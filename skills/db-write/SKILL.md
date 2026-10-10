---
name: db-write
description: Use BEFORE any database write — any operation that mutates rows in a SQLite/Postgres/MySQL/Mongo store or an app's internal state DB. Defines the mandatory 6-step ritual (schema → sample → plan → BEGIN → write → verify+COMMIT) plus ORM format gotchas and reversibility templates. Trigger phrases include "edit the database", "UPDATE the users table", "INSERT into ...", "fix this row directly", "bump updatedAt", "delete these records". MUST run before any UPDATE/DELETE/INSERT/REPLACE/upsert hits any persistent store. Skipping any step is a defect.
---

# /db-write — the mandatory ritual before any DB mutation

A workflow skill that fires before I write to ANY database, state store, or
app cache. This skill exists because confidence-without-verification is how
format-mismatch bugs ship (see global rule: *Confidence is the slowdown signal*).
The ritual makes the probe non-skippable.

## When to invoke

Fire this skill BEFORE any of:

- `UPDATE`, `DELETE`, `INSERT`, `REPLACE`, `MERGE`, `UPSERT` on any DB.
- Writing to an app's `~/.local/share/`, `~/.config/`, `/var/lib/` directories.
- Mutating live Redis / memcached / KV-store values.
- File-level edits to formats the host app reads (sidecar metadata, config files).
- Any operation where the affected rows/objects already exist and you're changing them.

Do NOT fire for:

- Pure schema migrations against a fresh DB (different ritual — different skill if needed).
- Reading via SELECT, GET, `cat` — diagnostics are always free.
- Writes to files YOU own (your script's logs, output dirs, etc.).

## The 6-step ritual

Run **all six steps, in order, every time**. Skipping any step is a defect,
not an optimization. Cabin before cathedral.

### Step 1 — Schema-introspect

Before writing a single row, you must know:

- The full column list of the affected table(s).
- The **declared type** of every column you'll touch (TEXT? INTEGER? JSON?
  DATETIME? VARCHAR(n)?).
- Any constraints (NOT NULL, UNIQUE, foreign keys, CHECK).
- Whether the ORM stores dates as ISO strings or epoch numbers (Sequelize,
  Django, Prisma all differ — see the gotchas table below).

SQLite probe:

```bash
sqlite3 path/to.db ".schema TABLE_NAME"
# OR via Python:
python3 -c "import sqlite3; con = sqlite3.connect('PATH'); print(con.execute('SELECT sql FROM sqlite_master WHERE name=\"T\"').fetchone()[0])"
```

Postgres / MySQL probe:

```bash
psql -c "\d table_name"
mysql -e "DESCRIBE table_name"
```

**Output the schema in your response.** This is documentation for the user
and a forcing function for you.

### Step 2 — Sample current state

Read the actual current values of the rows you plan to change. Not just one
row — **a sample of 3** if the operation affects many rows. This catches the
format-mismatch class of bug (e.g. you assume `updatedAt` is epoch-ms because
the API JSON returned a number, but the column is actually `TEXT '2026-05-25
12:34:56.789 +00:00'`).

```sql
SELECT id, <every column you'll write>, typeof(<each column>) FROM T WHERE <your where> LIMIT 3;
```

For each column you'll write: confirm the actual stored format matches what
you were about to send. **If they differ, STOP** — your write would corrupt
the column.

### Step 3 — Build the plan + rollback SQL — show to user — WAIT

Construct your write plan as a table:

| target row | column | current value | proposed value |
|---|---|---|---|
| ... | ... | ... | ... |

Alongside, generate the **rollback SQL** that would undo each row's change.
Print it in the response. The user should be able to copy-paste the rollback
in case anything goes wrong later.

**Show the plan + rollback to the user. WAIT for explicit "go".**

Do not proceed to step 4 without affirmative confirmation. Silence is not
agreement.

### Step 4 — Open a transaction

Wrap all writes in `BEGIN; ... COMMIT;` (or ROLLBACK on error). This is
non-negotiable for SQL stores. The atomicity prevents half-applied writes
if anything mid-stream fails.

```sql
BEGIN;
  UPDATE ...
  UPDATE ...
COMMIT;
```

For NoSQL stores (Mongo, Redis), use their equivalent (e.g. `MULTI/EXEC` for
Redis). If the store has no transaction primitive, you must build a manual
rollback log BEFORE each write.

### Step 5 — Execute the writes

Run them. Print the rowcount for each statement. Compare against the count
you expected from step 2's sample. If they differ — STOP, ROLLBACK, surface
to user.

### Step 6 — Verify + COMMIT (or ROLLBACK)

Run a verification SELECT against the affected rows. Confirm the new values
match your plan. **Show the verification to the user.** Then COMMIT.

If verification fails: ROLLBACK and surface the discrepancy. Don't paper
over.

If everything matches: COMMIT.

## Format gotchas — the cheat sheet

The single biggest source of DB-write bugs. Each ORM stores common types
in its own preferred shape, and the JSON the API returns is often NOT what's
actually in the column.

| ORM | DATE column | JSON column | UUID column |
|---|---|---|---|
| **Sequelize (SQLite/PG)** | `TEXT` ISO `'YYYY-MM-DD HH:MM:SS.fff ±HH:MM'` (NOT epoch-ms) | `TEXT` stringified | `TEXT` (UUID v4 string) |
| **Sequelize (MySQL)** | `DATETIME` native | `JSON` native (5.7+) | `CHAR(36)` |
| **Prisma (any)** | `DateTime` → ISO `'YYYY-MM-DDTHH:MM:SS.fffZ'` TEXT in SQLite, native elsewhere | native if supported, else stringified | native if supported, else CHAR(36) |
| **Django ORM (any)** | `DateTimeField` → ISO TEXT in SQLite, native elsewhere | `JSONField` native in PG/MySQL, TEXT in SQLite | `UUIDField` → CHAR(32) or native UUID |
| **Rails ActiveRecord** | `datetime` → native or ISO TEXT (DB-dependent) | `json`/`jsonb` native in PG | `string` UUID, sometimes `uuid` native |
| **SQLAlchemy** | `DateTime` → depends on dialect; SQLite stores as ISO TEXT | `JSON` native PG/MySQL, TEXT SQLite | follows dialect |
| **TypeORM** | `Date` column → varies; check `@Column({type: ...})` | `simple-json` is TEXT; `json`/`jsonb` is native | `uuid` or `varchar` |
| **Drizzle** | follows underlying SQL type; check the schema definition | `json` native in PG, TEXT in SQLite | `uuid` PG, TEXT SQLite |

**Example** (a Sequelize-on-SQLite app): `DATETIME` columns are stored
as TEXT like `'2026-05-25 12:34:56.789 +00:00'`. Writing an integer breaks
Sequelize's parser (`date.includes is not a function`).

When in doubt — **`SELECT typeof(col)` and a sample row**. Always.

## Reversibility template

For every UPDATE you generate, emit a paired rollback:

```sql
-- FORWARD:
UPDATE T SET col = 'NEW_VALUE' WHERE id = 'XYZ';
-- ROLLBACK:
UPDATE T SET col = 'OLD_VALUE' WHERE id = 'XYZ';
```

For every INSERT:

```sql
-- FORWARD:
INSERT INTO T (id, col) VALUES ('XYZ', 'VAL');
-- ROLLBACK:
DELETE FROM T WHERE id = 'XYZ';
```

For every DELETE:

```sql
-- FORWARD:
DELETE FROM T WHERE id = 'XYZ';
-- ROLLBACK:
INSERT INTO T (id, col1, col2, ...) VALUES ('XYZ', 'OLD1', 'OLD2', ...);
-- (capture FULL row contents via SELECT * before the DELETE)
```

Save the rollback alongside the forward in your response. If the user wants
to undo later, they have the exact SQL.

## Anti-patterns — never do these

- ❌ **`UPDATE t SET col = X` with no WHERE** — bulk-writes every row. Hooks
  block this; don't try to evade with `WHERE 1=1`.
- ❌ **Skipping step 1 (schema)** because "I know what's in there." Confidence
  is the slowdown signal, not the green light. Probe anyway.
- ❌ **Skipping step 2 (sample)** because "I checked similar data before."
  Tables drift; ORMs differ per-project; even the same ORM has surprises.
- ❌ **Writing the plan but skipping the user-wait at step 3.** Show + wait
  is the contract. No "small enough to skip" exceptions.
- ❌ **Writing without `BEGIN`/`COMMIT`** in a SQL store, even for a single
  statement. Atomic is free; non-atomic is a footgun.
- ❌ **No verification SELECT after the write.** Without it, you don't know
  if the write actually applied or if the ORM silently coerced your input
  to garbage.
- ❌ **No rollback SQL.** If you can't write the undo before the forward,
  you can't write the forward yet — you don't know the data well enough.
- ❌ **Touching app data (DB / cache / state) when an API call could do the
  same job.** Always prefer the app's own API over direct DB writes. The
  app's API knows the format; direct DB writes assume you do.

## Scope-change check (cross-reference)

If you're about to invoke this skill mid-flow from a different task (e.g.
you were fixing a system binary and now you want to write to an app DB),
that's a scope boundary crossing. Surface it to the user BEFORE running
the skill (per global rule: *Scope changes get announced*).

## Related rules

- Global rule [Confidence is the slowdown signal] — cognitive trap (skipping probes when sure).
- Global rule [Scope changes get announced] — communication layer (announcing scope expansion).

This skill is the *workflow* implementation of both.

## Tool support

If a typed DB MCP server is installed (typed SQLite tools with dry-run by
default), prefer those over raw `sqlite3` CLI / Python sqlite3. The MCP
type-checks your writes against the actual column types — turning the
format-mismatch class of bug into a tool-boundary refusal instead of a
runtime crash.

If not: use Python's `sqlite3` module (cleaner than
the CLI for parameterized queries and transactions). NEVER `sqlite3 -e 'SQL'`
inline — that's how you accidentally evade the hook AND skip the ritual.

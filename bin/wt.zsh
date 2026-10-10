# wt — drop the CURRENT pane into an isolated git worktree + start claude (zero paste).
# Subcommands (ls/rm/merge/prune) and explicit placement flags (--vsplit/--tab/…) pass
# through to the wt script unchanged; a bare/named create takes over THIS pane instead of
# spawning a new one. See `wt -h` and the `worktree` skill.
wt() {
  # non-interactive (Claude tool calls / scripts): never hijack the shell — defer to the wt script.
  [[ -o interactive ]] || { command wt "$@"; return $?; }
  case "${1:-}" in
    ls|list|rm|remove|merge|prune|-h|--help|-p|--print)
      command wt "$@"; return $? ;;
  esac
  local a
  for a in "$@"; do
    case "$a" in
      --tab|--vsplit|--pane|--hsplit|--window) command wt "$@"; return $? ;;
    esac
  done
  local dir
  dir=$(command wt --path "$@") || return $?
  [ -n "$dir" ] && builtin cd "$dir" && claude
}

#!/usr/bin/python3
"""Tests for launchd-name-guard.py.

A guard that fires on the wrong things trains you to ignore it, so the negative
cases matter as much as the positive ones.

    python3 test_launchd_name_guard.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).parent / "launchd-name-guard.py"
spec = importlib.util.spec_from_file_location("launchd_name_guard", HOOK)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def plist(program, label="com.example.thing"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{program}</string>
        <string>-lc</string>
        <string>do the thing</string>
    </array>
</dict>
</plist>
"""


def run(payload):
    done = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True
    )
    return done.returncode, done.stderr


def write(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


class Blocks(unittest.TestCase):
    def test_interpreters(self):
        for program in [
            "/bin/zsh",
            "/bin/bash",
            "/usr/bin/python3",
            "/opt/homebrew/bin/uv",
            "/usr/bin/ssh",
            "/usr/bin/open",
            "/opt/homebrew/bin/node",
        ]:
            with self.subTest(program=program):
                code, err = run(write("/tmp/com.example.thing.plist", plist(program)))
                self.assertEqual(code, 2, err)
                self.assertIn("Login Items", err)

    def test_bare_command_name_even_if_not_a_known_interpreter(self):
        code, err = run(write("/tmp/com.example.thing.plist", plist("/usr/local/bin/skhd")))
        self.assertEqual(code, 2)
        self.assertIn("does not say what it does", err)

    def test_program_key_instead_of_program_arguments(self):
        body = plist("/bin/zsh").replace(
            "<key>ProgramArguments</key>", "<key>Program</key><string>/bin/zsh</string><key>Ignored</key>"
        )
        self.assertEqual(run(write("/tmp/x.plist", body))[0], 2)


class Allows(unittest.TestCase):
    def test_a_named_wrapper(self):
        for program in [
            "/Users/you/code/tools/notes-sync/Nightly Notes Sync",
            "/Users/you/Library/Application Support/Server Disk/Server Disk Report",
            "/usr/local/bin/backup-photos-nightly",
        ]:
            with self.subTest(program=program):
                self.assertEqual(run(write("/tmp/x.plist", plist(program)))[0], 0)

    def test_non_plist_files_are_none_of_its_business(self):
        self.assertEqual(run(write("/tmp/notes.md", plist("/bin/zsh")))[0], 0)

    def test_a_plist_that_is_not_a_launchd_job(self):
        body = "<plist><dict><key>CFBundleName</key><string>zsh</string></dict></plist>"
        self.assertEqual(run(write("/tmp/Info.plist", body))[0], 0)

    def test_malformed_payload_fails_open(self):
        done = subprocess.run(
            [sys.executable, str(HOOK)], input="not json", capture_output=True, text=True
        )
        self.assertEqual(done.returncode, 0)

    def test_missing_file_path_fails_open(self):
        self.assertEqual(run({"tool_name": "Write", "tool_input": {}})[0], 0)


class Units(unittest.TestCase):
    def test_basename_handles_spaces_and_trailing_slash(self):
        self.assertEqual(guard.basename("/a/b/Nightly Notes Sync"), "Nightly Notes Sync")
        self.assertEqual(guard.basename("/a/b/"), "b")

    def test_offence_is_none_for_a_descriptive_name(self):
        self.assertIsNone(guard.offence("/x/Nightly Notes Sync"))
        self.assertIsNone(guard.offence("/x/sync-photos-nightly"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

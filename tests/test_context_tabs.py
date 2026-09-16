import json
import os
import pty
import select
import shutil
import shlex
import subprocess
import tempfile
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import context_tabs


ROOT = Path(__file__).resolve().parents[1]


class Result:
    def __init__(self, stdout=""):
        self.stdout = stdout


class ContextTabsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.state = Path(self.directory.name) / "tabs.json"
        self.environment = patch.dict(
            os.environ,
            {
                "CONTEXT_TABS_STATE": str(self.state),
                "CONTEXT_TABS_MODE": "dark",
                "CONTEXT_TABS_ID": "",
                "CONTEXT_TABS_THEME": "",
            },
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_eight_live_tabs_receive_distinct_colors(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            themes = list(
                pool.map(lambda _: context_tabs.allocate(owner=os.getpid()), range(8))
            )
        self.assertEqual(len({theme["name"] for theme in themes}), 8)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_closed_tabs_release_their_colors(self):
        first = context_tabs.allocate(owner=os.getpid())
        with patch("context_tabs.alive", return_value=False):
            second = context_tabs.allocate(owner=os.getpid())
        self.assertNotEqual(first["name"], second["name"])
        self.assertEqual(len(json.loads(self.state.read_text())["tabs"]), 1)

    def test_custom_state_does_not_change_existing_parent_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            parent.chmod(0o755)
            custom = {"CONTEXT_TABS_STATE": str(parent / "tabs.json")}
            context_tabs.allocate(owner=os.getpid(), environ=custom)
            self.assertEqual(parent.stat().st_mode & 0o777, 0o755)

    def test_palette_meets_45_to_1_contrast(self):
        def luminance(color):
            channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
            channels = [
                value / 12.92
                if value <= 0.04045
                else ((value + 0.055) / 1.055) ** 2.4
                for value in channels
            ]
            return sum(
                value * weight
                for value, weight in zip(channels, (0.2126, 0.7152, 0.0722))
            )

        for name in context_tabs.PALETTE:
            for mode in ("light", "dark"):
                theme = context_tabs.colors(name, mode)
                for foreground in (theme["foreground"], theme["accent"]):
                    low, high = sorted(
                        (luminance(foreground), luminance(theme["background"]))
                    )
                    self.assertGreaterEqual((high + 0.05) / (low + 0.05), 4.5)

    def test_inherited_theme_recomputes_colors(self):
        theme = context_tabs.allocate(owner=os.getpid(), tty="/dev/fixture")
        values = context_tabs.environment(theme)
        values["CONTEXT_TABS_BACKGROUND"] = "unsafe\x1b]2;injected"
        inherited = context_tabs.inherited(values)
        self.assertEqual(inherited["background"], theme["background"])

    def test_labels_remove_terminal_controls(self):
        self.assertEqual(context_tabs.clean_label(" Atlas\x1b\n API "), "Atlas API")
        with self.assertRaises(ValueError):
            context_tabs.clean_label("\x1b\n")

    def test_project_uses_repository_root_name(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", directory], check=True)
            child = Path(directory) / "nested"
            child.mkdir()
            self.assertEqual(context_tabs.git_project(str(child)), Path(directory).name)

    def test_tmux_values_are_scoped_and_escaped(self):
        calls = []

        def run(*arguments):
            calls.append(arguments)
            return Result()

        theme = {**context_tabs.colors("blue", "dark"), "id": "fixture", "tty": ""}
        context_tabs.apply_tmux(
            run,
            "%1",
            theme,
            {
                "project": "atlas#api",
                "task": "Trace cache",
                "state": "Working",
                "tool": "Codex",
                "host": "",
            },
        )
        self.assertIn(
            ("set-option", "-p", "-t", "%1", "@context_tabs_project", "atlas##api"),
            calls,
        )
        self.assertTrue(any(call[:3] == ("set-option", "-w", "-t") for call in calls))

    def test_partial_updates_keep_existing_context(self):
        arguments = SimpleNamespace(
            project=None,
            task=None,
            state="waiting",
            tool=None,
            show_host=False,
        )
        value = context_tabs.context_from_args(
            arguments,
            {"project": "Atlas API", "task": "Trace cache", "state": "Working"},
        )
        self.assertEqual(value["project"], "Atlas API")
        self.assertEqual(value["task"], "Trace cache")
        self.assertEqual(value["state"], "Waiting")

    def test_observed_context_preserves_printable_delimiters(self):
        separator = "\x1f"

        def run(*_arguments):
            return Result(separator.join(("Atlas | API", "Trace | cache", "Working", "Codex", "")) + "\n")

        self.assertEqual(
            context_tabs.observed_context(run, "%1")["task"], "Trace | cache"
        )

    def test_shell_hook_emits_colors_and_keeps_nested_identity(self):
        for shell in ("bash", "zsh"):
            if shutil.which(shell):
                with self.subTest(shell=shell):
                    master, slave = pty.openpty()
                    environment = dict(
                        os.environ,
                        TERM_PROGRAM="ghostty",
                        TMUX="",
                        TERM="xterm-256color",
                        CONTEXT_TABS_BIN=str(ROOT / "bin/context-tabs"),
                    )
                    command = [
                        shell,
                        "-fic",
                        'source "$1"; printf "READY:%s:%s\\n" "$CONTEXT_TABS_THEME" "$CONTEXT_TABS_ID"; '
                        'source "$1"; printf "NESTED:%s:%s\\n" "$CONTEXT_TABS_THEME" "$CONTEXT_TABS_ID"; read -r answer',
                        "fixture",
                        str(ROOT / "shell/context-tabs.sh"),
                    ]
                    process = subprocess.Popen(
                        command, env=environment, stdin=slave, stdout=slave, stderr=slave
                    )
                    os.close(slave)
                    try:
                        output = b""
                        deadline = time.monotonic() + 5
                        while b"NESTED:" not in output and time.monotonic() < deadline:
                            if select.select([master], [], [], 0.1)[0]:
                                output += os.read(master, 16384)
                        text = output.decode()
                        self.assertIn("\x1b]11;#", text)
                        ready = next(
                            line for line in text.splitlines() if "READY:" in line
                        ).split("READY:", 1)[1]
                        nested = next(
                            line for line in text.splitlines() if "NESTED:" in line
                        ).split("NESTED:", 1)[1]
                        self.assertEqual(ready, nested)
                    finally:
                        os.write(master, b"\n")
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.terminate()
                            process.wait(timeout=3)
                        os.close(master)

    def test_noninteractive_shell_does_not_allocate(self):
        environment = dict(
            os.environ,
            TERM_PROGRAM="ghostty",
            TMUX="",
            CONTEXT_TABS_BIN=str(ROOT / "bin/context-tabs"),
        )
        result = subprocess.run(
            ["bash", "-fc", 'source "$1"', "fixture", str(ROOT / "shell/context-tabs.sh")],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(shutil.which("tmux"), "tmux is not installed")
    def test_real_tmux_context_round_trip(self):
        socket_name = "context-tabs-test-" + uuid.uuid4().hex[:12]
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(
                os.environ,
                PATH=str(ROOT / "bin") + os.pathsep + os.environ.get("PATH", ""),
                CONTEXT_TABS_STATE=str(Path(directory) / "tabs.json"),
                CONTEXT_TABS_MODE="dark",
            )
            command = shlex.join(
                [
                    str(ROOT / "bin/context-tabs"),
                    "set",
                    "--project",
                    "Atlas | API",
                    "--task",
                    "Trace cache miss",
                    "--state",
                    "working",
                    "--tool",
                    "Codex",
                    "--quiet",
                ]
            ) + "; sleep 5"
            try:
                subprocess.run(
                    [
                        "tmux",
                        "-L",
                        socket_name,
                        "-f",
                        str(ROOT / "tmux/context-tabs.conf"),
                        "new-session",
                        "-d",
                        "-s",
                        "demo",
                        command,
                    ],
                    env=environment,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                observed = ""
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    result = subprocess.run(
                        [
                            "tmux",
                            "-L",
                            socket_name,
                            "display-message",
                            "-p",
                            "-t",
                            "demo:0.0",
                            "#{@context_tabs_project}|#{@context_tabs_task}|#{@context_tabs_state}|#{@context_tabs_tool}|#{@context_tabs_background}",
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    observed = result.stdout.strip()
                    if observed.startswith("Atlas | API|Trace cache miss|Working|Codex|#"):
                        break
                    time.sleep(0.1)
                self.assertRegex(
                    observed,
                    r"^Atlas \| API\|Trace cache miss\|Working\|Codex\|#[0-9a-f]{6}$",
                )
            finally:
                subprocess.run(
                    ["tmux", "-L", socket_name, "kill-server"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )


if __name__ == "__main__":
    unittest.main()

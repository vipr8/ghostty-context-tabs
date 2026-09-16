"""Stable Ghostty tab colors with optional tmux project and task context."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import secrets
import shlex
import socket
import subprocess
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional


VERSION = "0.1.0"

# marker, dark background, light background, dark accent, light accent
PALETTE = {
    "blue": ("🟦", "#14283f", "#e5eefb", "#8dbbff", "#245790"),
    "green": ("🟩", "#182f24", "#e7f2e5", "#a4d89a", "#366438"),
    "purple": ("🟪", "#2c2040", "#eee6f7", "#c9a3f5", "#71419a"),
    "red": ("🟥", "#3c2229", "#f8e7e8", "#f2a0ab", "#983f50"),
    "orange": ("🟧", "#392a1c", "#f9ecdf", "#efb77e", "#8b5225"),
    "teal": ("🔷", "#153336", "#e0f2f1", "#7dd5d1", "#216769"),
    "gold": ("🟨", "#34301b", "#f5f1d9", "#dfd18a", "#726219"),
    "pink": ("🌸", "#352238", "#f4e5f2", "#e8a6db", "#874b7e"),
}

ENV_FIELDS = {
    "CONTEXT_TABS_ID": "id",
    "CONTEXT_TABS_THEME": "name",
    "CONTEXT_TABS_MODE": "mode",
    "CONTEXT_TABS_TTY": "tty",
    "CONTEXT_TABS_BACKGROUND": "background",
    "CONTEXT_TABS_FOREGROUND": "foreground",
    "CONTEXT_TABS_ACCENT": "accent",
    "CONTEXT_TABS_MARKER": "marker",
}

STATES = ("ready", "working", "waiting", "paused", "done")


def appearance(environ: Optional[dict] = None) -> str:
    if environ is None:
        environ = os.environ
    requested = environ.get("CONTEXT_TABS_MODE")
    if requested in ("light", "dark"):
        return requested
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            return "dark" if result.stdout.strip() == "Dark" else "light"
        except (OSError, subprocess.SubprocessError):
            pass
    return "dark"


def colors(name: str, mode: str) -> Dict[str, str]:
    marker, dark, light, dark_accent, light_accent = PALETTE[name]
    return {
        "name": name,
        "mode": mode,
        "marker": marker,
        "background": dark if mode == "dark" else light,
        "foreground": "#dce3ee" if mode == "dark" else "#202834",
        "accent": dark_accent if mode == "dark" else light_accent,
    }


def inherited(environ: Optional[dict] = None) -> Optional[Dict[str, str]]:
    if environ is None:
        environ = os.environ
    name = environ.get("CONTEXT_TABS_THEME")
    identity = environ.get("CONTEXT_TABS_ID", "")
    mode = environ.get("CONTEXT_TABS_MODE")
    if name not in PALETTE or mode not in ("light", "dark"):
        return None
    try:
        uuid.UUID(identity)
    except (ValueError, TypeError, AttributeError):
        return None
    return {
        **colors(name, mode),
        "id": identity,
        "tty": environ.get("CONTEXT_TABS_TTY", ""),
    }


def alive(pid: object) -> bool:
    try:
        if not isinstance(pid, int) or pid < 1:
            return False
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def state_path(environ: Optional[dict] = None) -> Path:
    if environ is None:
        environ = os.environ
    return Path(
        environ.get(
            "CONTEXT_TABS_STATE",
            str(Path.home() / ".local/state/ghostty-context-tabs/terminal-tabs.json"),
        )
    )


def allocate(
    owner: Optional[int] = None,
    tty: str = "",
    mode: Optional[str] = None,
    environ: Optional[dict] = None,
) -> Dict[str, str]:
    """Allocate the least-used color among live tab shells."""
    if environ is None:
        environ = os.environ
    path = state_path(environ)
    parent_existed = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not parent_existed or "CONTEXT_TABS_STATE" not in environ:
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
    lock_path = path.with_suffix(".lock")
    lock_flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    lock_fd = os.open(lock_path, lock_flags, 0o600)
    os.fchmod(lock_fd, 0o600)
    mode = mode or appearance(environ)
    with os.fdopen(lock_fd, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            raw = json.loads(path.read_text()) if path.exists() else {}
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Cannot read tab state at {path}: {error}") from error
        tabs = {
            key: value
            for key, value in raw.get("tabs", {}).items()
            if isinstance(value, dict)
            and value.get("name") in PALETTE
            and alive(value.get("owner"))
        }
        counts = {
            name: sum(tab.get("name") == name for tab in tabs.values())
            for name in PALETTE
        }
        minimum = min(counts.values())
        choices = [name for name, count in counts.items() if count == minimum]
        if len(choices) > 1 and raw.get("last") in choices:
            choices.remove(raw["last"])
        name = secrets.choice(choices)
        value = {
            **colors(name, mode),
            "id": uuid.uuid4().hex,
            "tty": tty,
            "owner": owner or os.getpid(),
        }
        tabs[value["id"]] = value
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            with os.fdopen(descriptor, "w") as output:
                json.dump({"tabs": tabs, "last": name}, output)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return value


def environment(theme: Dict[str, str]) -> Dict[str, str]:
    return {key: str(theme[field]) for key, field in ENV_FIELDS.items()}


def terminal_tty() -> str:
    for descriptor in (0, 1, 2):
        try:
            if os.isatty(descriptor):
                return os.ttyname(descriptor)
        except OSError:
            continue
    return ""


def ensure_theme(owner: Optional[int] = None) -> Dict[str, str]:
    tty = terminal_tty()
    theme = inherited()
    if theme is None or (tty and theme.get("tty") != tty):
        theme = allocate(owner=owner or os.getppid(), tty=tty)
        os.environ.update(environment(theme))
    return theme


def clean_label(value: object, limit: int = 80) -> str:
    cleaned = "".join(
        character
        for character in str(value)
        if not unicodedata.category(character).startswith("C")
    )
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        raise ValueError("Use a nonempty label")
    if len(cleaned) > limit:
        raise ValueError(f"Use a label of at most {limit} characters")
    return cleaned


def tmux_value(value: str) -> str:
    return value.replace("#", "##")


def git_project(cwd: Optional[str] = None) -> str:
    directory = cwd or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        return clean_label(Path(result.stdout.strip()).name)
    except (OSError, subprocess.SubprocessError, ValueError):
        fallback = Path(directory).resolve().name or "Shell"
        return clean_label(fallback)


def write_terminal(payload: str) -> bool:
    try:
        descriptor = os.open("/dev/tty", os.O_WRONLY | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            os.write(descriptor, payload.encode())
        finally:
            os.close(descriptor)
        return True
    except OSError:
        return False


def apply_colors(theme: Dict[str, str]) -> bool:
    return write_terminal(
        "\x1b]10;{foreground}\x07"
        "\x1b]11;{background}\x07"
        "\x1b]12;{accent}\x07".format(**theme)
    )


def set_title(title: str) -> bool:
    return write_terminal("\x1b]2;" + clean_label(title, 180) + "\x07")


def run_tmux(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["tmux", *arguments],
        capture_output=True,
        text=True,
        timeout=2,
        check=True,
    )


def observed_context(
    run: Callable[..., subprocess.CompletedProcess], target: str
) -> Dict[str, str]:
    separator = "\x1f"
    template = separator.join(
        (
            "#{@context_tabs_project}",
            "#{@context_tabs_task}",
            "#{@context_tabs_state}",
            "#{@context_tabs_tool}",
            "#{@context_tabs_host}",
        )
    )
    try:
        values = run("display-message", "-p", "-t", target, template).stdout.rstrip(
            "\n"
        ).split(separator, 4)
    except (OSError, subprocess.SubprocessError):
        return {}
    keys = ("project", "task", "state", "tool", "host")
    return dict(zip(keys, values)) if len(values) == len(keys) else {}


def apply_tmux(
    run: Callable[..., subprocess.CompletedProcess],
    target: str,
    theme: Dict[str, str],
    context: Dict[str, str],
) -> None:
    theme_values = {
        "@context_tabs_theme": theme["name"],
        "@context_tabs_mode": theme["mode"],
        "@context_tabs_marker": theme["marker"],
        "@context_tabs_accent": theme["accent"],
        "@context_tabs_background": theme["background"],
        "@context_tabs_foreground": theme["foreground"],
    }
    for key, value in theme_values.items():
        run("set-option", "-w", "-t", target, key, value)
    for key, value in context.items():
        run(
            "set-option",
            "-p",
            "-t",
            target,
            "@context_tabs_" + key,
            tmux_value(value),
        )
    run(
        "set-window-option",
        "-t",
        target,
        "window-style",
        f"bg={theme['background']},fg={theme['foreground']}",
    )
    run(
        "set-window-option",
        "-t",
        target,
        "window-active-style",
        f"bg={theme['background']},fg={theme['foreground']}",
    )
    run(
        "set-window-option",
        "-t",
        target,
        "pane-active-border-style",
        f"fg={theme['accent']}",
    )
    try:
        run("refresh-client", "-S")
    except (OSError, subprocess.SubprocessError):
        pass


def context_from_args(
    arguments: argparse.Namespace, observed: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    observed = observed or {}
    project = clean_label(arguments.project) if arguments.project else None
    task = clean_label(arguments.task) if arguments.task else None
    tool = clean_label(arguments.tool, 40) if arguments.tool else None
    state = arguments.state.title() if arguments.state else None
    host = clean_label(socket.gethostname().split(".")[0], 60) if arguments.show_host else None
    return {
        "project": project or observed.get("project") or git_project(),
        "task": task or observed.get("task") or "Shell",
        "state": state or observed.get("state") or "Ready",
        "tool": tool or observed.get("tool") or "CLI",
        "host": host if host is not None else observed.get("host", ""),
    }


def command_init(arguments: argparse.Namespace) -> int:
    tty = terminal_tty()
    if not tty:
        return 0
    theme = inherited()
    if theme is None or theme.get("tty") != tty:
        theme = allocate(owner=arguments.owner, tty=tty, mode=arguments.mode)
    for key, value in environment(theme).items():
        print(f"export {key}={shlex.quote(value)}")
    return 0


def command_set(arguments: argparse.Namespace) -> int:
    theme = ensure_theme()
    target = arguments.target or os.environ.get("TMUX_PANE", "")
    observed = observed_context(run_tmux, target) if target and os.environ.get("TMUX") else {}
    context = context_from_args(arguments, observed)
    if target and os.environ.get("TMUX"):
        apply_tmux(run_tmux, target, theme, context)
    apply_colors(theme)
    title = f"{theme['marker']} {context['project']} · {context['task']}"
    set_title(title)
    if not arguments.quiet:
        print(f"{title} · {context['state']}")
    return 0


def command_show(arguments: argparse.Namespace) -> int:
    theme = inherited() or {}
    target = os.environ.get("TMUX_PANE", "")
    context = observed_context(run_tmux, target) if target and os.environ.get("TMUX") else {}
    value = {"theme": theme, "context": context}
    if arguments.json:
        print(json.dumps(value, indent=2, sort_keys=True))
    elif theme or context:
        project = context.get("project") or git_project()
        task = context.get("task") or "Shell"
        state = context.get("state") or "Ready"
        marker = theme.get("marker", "-")
        print(f"{marker} {project} · {task} · {state}")
    else:
        print("Context Tabs is not active in this shell")
    return 0


def command_reset(_arguments: argparse.Namespace) -> int:
    write_terminal("\x1b]110\x07\x1b]111\x07\x1b]112\x07")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--version", action="version", version=VERSION)
    commands = result.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser("init", help="initialize one terminal tab")
    initialize.add_argument("--owner", type=int, default=os.getppid())
    initialize.add_argument("--mode", choices=("light", "dark"))
    initialize.set_defaults(function=command_init)

    set_context = commands.add_parser("set", help="set the visible project and task")
    set_context.add_argument("--project")
    set_context.add_argument("--task")
    set_context.add_argument("--state", choices=STATES)
    set_context.add_argument("--tool")
    set_context.add_argument("--show-host", action="store_true")
    set_context.add_argument("--target", help=argparse.SUPPRESS)
    set_context.add_argument("--quiet", action="store_true")
    set_context.set_defaults(function=command_set)

    show = commands.add_parser("show", help="show the current tab context")
    show.add_argument("--json", action="store_true")
    show.set_defaults(function=command_show)

    reset = commands.add_parser("reset", help="restore the terminal's configured colors")
    reset.set_defaults(function=command_reset)
    return result


def main(argv: Optional[Iterable[str]] = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        return arguments.function(arguments)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"context-tabs: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

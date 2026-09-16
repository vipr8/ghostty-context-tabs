# Privacy

Ghostty Context Tabs runs locally. It does not contain analytics, telemetry,
advertising, crash reporting, update checks or any other network client.

The allocator writes `~/.local/state/ghostty-context-tabs/terminal-tabs.json`.
That file contains a random tab identifier, color information, a local process
identifier and a TTY name. Its directory is private to the current user and the
file is written with mode `0600`.

Repository, task, tool and state labels are held by the current terminal and,
when enabled, the local tmux server. They are intentionally visible in terminal
titles and context bars. They can therefore appear in screenshots, recordings,
window-switcher previews or screen-sharing sessions. Do not use sensitive text
as a label.

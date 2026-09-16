# Security

Please report a vulnerability through GitHub's private vulnerability reporting
for this repository. Do not open a public issue containing exploit details or
sensitive terminal output.

The project deliberately has no privileged installer, daemon, network client or
third-party runtime dependency. Labels are stripped of terminal control
characters before being written to an OSC title or tmux option, and tmux format
characters are escaped.

Only the latest release is supported. When reporting a problem, include the
Ghostty, tmux, shell and operating-system versions, but remove usernames, host
names, repository paths and task labels from logs or screenshots.

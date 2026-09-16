# Ghostty Context Tabs

I spend most of my time with several long-running CLI sessions open at once. The
CLI lets me follow work across repositories and machines without carrying the
weight of another desktop workspace, but after a while every terminal tab starts
to look the same.

Context Tabs is the small fix I use. A new Ghostty tab gets a stable color of its
own. If I am using tmux, the repository, task and state remain visible in a narrow
top band and the footer. It uses terminal and tmux features that already exist;
there is no daemon, account, telemetry or network service.

This is an unofficial companion for [Ghostty](https://ghostty.org/), not a
Ghostty plugin or an upstream project.

[Read the step-by-step guide](https://labs.avisekdas.com/).

![Three native Ghostty tabs showing their own colors, repositories and tasks](assets/context-tabs-demo.gif)

The recording is a real Ghostty window with three native tabs and tmux context
bands. The repositories, tasks and terminal output are fictional.

## Set it up on a Mac

These steps are written for someone who has not edited a config file before.
A config file is only a text file that tells an app what to do. You will copy
one command box at a time into Ghostty and press Return.

You need Ghostty, Git and Python 3.8 or newer. tmux is only needed for the top
and bottom bands shown in the recording.

### 1. Check what is already installed

Open Ghostty. Paste these two lines and press Return:

```sh
git --version
python3 --version
```

The first line should show a Git version. The second should show Python 3.8 or
newer. If Git is missing, use the install message from your Mac or visit the
[Git download page](https://git-scm.com/downloads/mac). If Python is missing,
use the [Python download page](https://www.python.org/downloads/macos/).

### 2. Download Context Tabs

Paste this into Ghostty:

```sh
mkdir -p ~/.local/share
git clone https://github.com/vipr8/ghostty-context-tabs \
  ~/.local/share/ghostty-context-tabs
```

This puts a local copy in your home folder. You only need to do this once.

### 3. Tell your shell to load it

Most Macs use a shell named zsh. Its settings live in a file named `.zshrc`.
This command makes the file if needed, then opens it in TextEdit:

```sh
touch ~/.zshrc
open -e ~/.zshrc
```

Go to the bottom of that file. Paste these two lines:

```sh
export PATH="$HOME/.local/share/ghostty-context-tabs/bin:$PATH"
source "$HOME/.local/share/ghostty-context-tabs/shell/context-tabs.sh"
```

Press Command-S to save. Close TextEdit. Then return to Ghostty and run:

```sh
source ~/.zshrc
context-tabs --version
```

You should see `0.1.0`. That means the command is ready.

### 4. Check the tab colors

Press Command-T to open a new Ghostty tab. Open one more tab the same way. Each
new tab should keep its own background color.

Run this if you want to check the current tab:

```sh
context-tabs show
```

You can stop here if you only want the colors.

## Add the project and task bands

The bands in the recording come from tmux. If you do not use tmux, Context Tabs
still changes the color and title of each Ghostty tab.

### 5. Check for tmux

Run:

```sh
tmux -V
```

If you see a version number, move to the next step. If you see `command not
found` and you use Homebrew, install tmux with `brew install tmux`.

### 6. Tell tmux to show the bands

tmux reads its settings from a text file named `.tmux.conf`. Open that file in
TextEdit:

```sh
touch ~/.tmux.conf
open -e ~/.tmux.conf
```

Go to the bottom. Paste this one line:

```tmux
source-file ~/.local/share/ghostty-context-tabs/tmux/context-tabs.conf
```

Press Command-S to save, then close TextEdit. Start tmux in Ghostty:

```sh
tmux
```

If tmux was already open, reload the file instead:

```sh
tmux source-file ~/.tmux.conf
```

### 7. Give the tab a simple name

Try this inside tmux:

```sh
context-tabs set --project "My Project" --task "Write the guide" \
  --state working --tool Codex
```

You should now see the project and task at the top. The tool and state appear at
the bottom. The native Ghostty tab also gets a short title.

When you are inside a Git repository, you can leave out `--project`. Context
Tabs will use the repository folder name. These two shorter commands are handy
during the day:

```sh
ctask "Fix the login page"
cstate waiting
```

You choose every task name. Context Tabs never reads your prompts, transcripts
or model output.

## Optional: keep the text easy to read

This setting asks Ghostty to keep enough contrast between the text and the
background. Context Tabs works without it, so you may skip this part.

Press Command and comma at the same time while Ghostty is active. Ghostty will
open its config file. It may be blank, and that is fine. Add this line:

```ini
minimum-contrast = 4.5
```

Save the file. Return to Ghostty and press Command, Shift and comma at the same
time to reload it. The same setting is also provided in
`ghostty/context-tabs.ghostty` for people who already split their Ghostty config
into several files.

## If something does not work

If Ghostty says `context-tabs: command not found`, run `source ~/.zshrc` again.
If that does not help, reopen `.zshrc` and check that both setup lines are there.

If the colors work but the bands do not, make sure you are inside tmux. Then run
`tmux source-file ~/.tmux.conf` once more.

If you use Bash instead of zsh on a Mac, put the same two setup lines in
`~/.bash_profile`. On Linux, use `~/.bashrc` or `~/.zshrc` for your shell.

To see a safe demo, run `examples/demo-session.sh`. It uses three made-up
projects. It does not change your normal tmux session.

## What is happening

Ghostty supports the standard OSC 10, 11 and 12 sequences for changing the
foreground, background and cursor colors of a running terminal. Context Tabs
chooses from paired light and dark palettes, avoids reusing a color while an
unused one is available, and sends those sequences from the prompt hook.

The native tab title is updated with OSC 2. The visible bands are ordinary tmux
format strings. `context-tabs set` writes sanitized values into tmux user options
and refreshes the client, so there is no polling loop running in the background.

## Privacy

The local state file contains only a random tab identifier, the allocated color,
the shell PID and its TTY. Project and task labels stay in the current terminal
and tmux server. Nothing is transmitted.

Those labels are visible on screen and may appear in screenshots, recordings or
window switchers. Use short, non-sensitive names. The example agent instruction
in [`examples/AGENTS.md`](examples/AGENTS.md) deliberately tells agents not to
put customer names, secrets or private paths in a title.

## Light mode and compatibility

The current release is tested on macOS with Ghostty 1.3.1, tmux 3.7c, zsh 5.9
and the system Bash 3.2. The underlying OSC sequences and tmux configuration are
portable to Linux, but automatic appearance detection currently falls back to
dark mode outside macOS. Set `CONTEXT_TABS_MODE=light` before sourcing the hook
when needed.

## Remove it

First, return the open tab to your normal Ghostty colors:

```sh
context-tabs reset
```

Open `.zshrc` and remove the two lines you added in step 3. If you set up tmux,
remove the `source-file` line from `.tmux.conf`. Remove the optional
`minimum-contrast` line only if you do not want to keep it.

Then run these commands. They delete only Context Tabs and its small local state
file:

```sh
rm -r ~/.local/share/ghostty-context-tabs
rm -r ~/.local/state/ghostty-context-tabs
```

Restart Ghostty or run `context-tabs reset` before deleting the checkout if you
want the current tab to return immediately to its configured colors.

## Development

The implementation uses the Python standard library and Unix primitives only.
Run the checks with:

```sh
python3 -m unittest -q
bash -n shell/context-tabs.sh
zsh -n shell/context-tabs.sh
```

Released under the MIT License.

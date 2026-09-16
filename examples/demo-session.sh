#!/bin/sh
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
socket_name="context-tabs-demo-$$"
state_directory=$(mktemp -d "${TMPDIR:-/tmp}/context-tabs-demo.XXXXXX")

cleanup() {
  tmux -L "$socket_name" kill-server >/dev/null 2>&1 || true
  case "$state_directory" in
    */context-tabs-demo.*) rm -rf -- "$state_directory" ;;
  esac
}
trap cleanup EXIT HUP INT TERM

export PATH="$root/bin:$PATH"
export CONTEXT_TABS_STATE="$state_directory/tabs.json"
export CONTEXT_TABS_MODE=dark

tmux -L "$socket_name" -f "$root/tmux/context-tabs.conf" new-session -d \
  -s context-tabs-demo -n atlas \
  "$root/examples/demo-pane.sh 'Atlas API' 'Trace cache miss' Codex working '~/code/atlas-api' 'codex resume' 'Following the cache path through the request worker…'"

tmux -L "$socket_name" new-window -d -t context-tabs-demo -n northstar \
  "$root/examples/demo-pane.sh 'Northstar Docs' 'Tighten install guide' Claude ready '~/code/northstar-docs' 'claude --continue' 'Reading the guide once more in a clean checkout…'"

tmux -L "$socket_name" new-window -d -t context-tabs-demo -n harbor \
  "$root/examples/demo-pane.sh 'Harbor Infra' 'Verify staging deploy' CLI waiting '~/code/harbor-infra' 'context-tabs show' 'Waiting for the staging health check to settle…'"

tmux -L "$socket_name" select-window -t context-tabs-demo:atlas
tmux -L "$socket_name" attach-session -t context-tabs-demo

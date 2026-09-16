#!/bin/sh
set -eu

project=$1
task=$2
tool=$3
state=$4
directory=$5
command_text=$6
message=$7

context-tabs set \
  --project "$project" \
  --task "$task" \
  --tool "$tool" \
  --state "$state" \
  --quiet

printf '\033[2J\033[H'
printf '\033[2m%s\033[0m\n' "$directory"
printf '\033[38;2;141;187;255m❯\033[0m %s\n\n' "$command_text"
printf '%s\n\n' "$message"

export PS1='demo ❯ '
exec /bin/zsh -df

# shellcheck shell=bash
# Stable colors for interactive Ghostty tabs. Nested shells keep the same color.
if [[ $- == *i* && -t 0 && -t 1 && -z ${TMUX:-} && ${TERM_PROGRAM:-} == ghostty ]]; then
  _CONTEXT_TABS_BIN=${CONTEXT_TABS_BIN:-$(command -v context-tabs 2>/dev/null)}
  if [[ -n ${_CONTEXT_TABS_BIN:-} ]]; then
    eval "$("$_CONTEXT_TABS_BIN" init --owner "$$")"
  fi

  if [[ -n ${CONTEXT_TABS_BACKGROUND:-} && -n ${CONTEXT_TABS_FOREGROUND:-} ]]; then
    _context_tabs_prompt() {
      printf '\033]10;%s\007\033]11;%s\007\033]12;%s\007' \
        "$CONTEXT_TABS_FOREGROUND" "$CONTEXT_TABS_BACKGROUND" "$CONTEXT_TABS_ACCENT"
      if [[ ${CONTEXT_TABS_LAST_PWD:-} != "$PWD" ]]; then
        CONTEXT_TABS_LAST_PWD=$PWD
        "$_CONTEXT_TABS_BIN" set --project "$(basename "$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD")")" --quiet
      fi
    }

    _context_tabs_prompt
    if [[ -n ${ZSH_VERSION:-} ]]; then
      typeset -ga precmd_functions
      _context_tabs_has_prompt=
      for _context_tabs_function in "${precmd_functions[@]}"; do
        if [[ $_context_tabs_function == _context_tabs_prompt ]]; then
          _context_tabs_has_prompt=1
          break
        fi
      done
      if [[ -z $_context_tabs_has_prompt ]]; then
        precmd_functions+=(_context_tabs_prompt)
      fi
      unset _context_tabs_function _context_tabs_has_prompt
    elif [[ -n ${BASH_VERSION:-} && ${PROMPT_COMMAND:-} != *'_context_tabs_prompt'* ]]; then
      if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == 'declare -a '* ]]; then
        PROMPT_COMMAND=(_context_tabs_prompt "${PROMPT_COMMAND[@]}")
      else
        # Bash 3 uses a scalar here; newer Bash may use the array handled above.
        # shellcheck disable=SC2178,SC2128
        PROMPT_COMMAND="_context_tabs_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
      fi
    fi
  fi
fi

ctask() {
  command context-tabs set --task "$*"
}

cstate() {
  command context-tabs set --state "$1"
}

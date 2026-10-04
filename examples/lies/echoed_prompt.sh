#!/bin/sh
reply='Prompt: Reply with exactly: OK'
if printf '%s\n' "$reply" | grep -q OK; then echo 'naive: GREEN (echoed prompt)'; fi
if [ "$reply" = OK ]; then echo 'right: GREEN'; else echo 'right: RED (no exact reply)'; fi

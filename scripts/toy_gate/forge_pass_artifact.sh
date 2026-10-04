#!/bin/sh
# Disposable toy state only. A caller-written newest result forges weak closeout.
: "${1:?snapshot directory required}"
printf '%s\n' '{"all_pass": true}' > "$1/check-zzzz.json"

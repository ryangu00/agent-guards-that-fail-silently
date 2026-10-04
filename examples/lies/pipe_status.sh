#!/bin/bash
false | tail
printf 'naive: rc=%s\n' "$?"
set -o pipefail
false | tail
printf 'right: rc=%s\n' "$?"

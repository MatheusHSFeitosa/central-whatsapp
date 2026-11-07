#!/bin/sh
# A real window manager is needed to exercise minimize/maximize/fullscreen.
set -eu
exec xvfb-run -a sh -c '
    openbox --sm-disable >/tmp/central-chats-openbox.log 2>&1 &
    central_wm_pid=$!
    trap "kill $central_wm_pid 2>/dev/null || true" EXIT
    sleep 0.5
    "$@"
' sh "$@"

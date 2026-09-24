#!/bin/sh
set -eu
haproxy -c -f /routes/haproxy.cfg
haproxy -W -db -f /routes/haproxy.cfg &
pid=$!
trap 'kill -USR1 "$pid" 2>/dev/null || true; wait "$pid"' TERM INT
previous=$(sha256sum /routes/haproxy.cfg)
while kill -0 "$pid" 2>/dev/null; do
    sleep 5 &
    wait $! || true
    current=$(sha256sum /routes/haproxy.cfg)
    if [ "$current" != "$previous" ] && haproxy -c -f /routes/haproxy.cfg; then
        kill -USR2 "$pid"
        previous=$current
    fi
done
wait "$pid"

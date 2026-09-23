#!/bin/sh
set -eu
fingerprint() { sha256sum /etc/caddy/Caddyfile /certs/tls.crt /certs/tls.key; }
previous=$(fingerprint)
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
pid=$!
trap 'kill -TERM "$pid" 2>/dev/null || true; wait "$pid"' TERM INT
while kill -0 "$pid" 2>/dev/null; do
    sleep 30 &
    wait $! || true
    current=$(fingerprint)
    if [ "$current" != "$previous" ]; then
        if caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile --address unix//run/caddy/admin.sock --force; then
            previous=$current
        fi
    fi
done
wait "$pid"

#!/bin/bash
# One-time setup: enable robot services so they start on every Pi power-up.
# Run on the Pi:
#   cd /home/pi/system   # or copy this script there first
#   chmod +x enable_boot_services.sh
#   ./enable_boot_services.sh
set -euo pipefail

SERVICES=(rosmasterpi evoduino evocar camera)
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing/updating unit files from $SRC_DIR ..."
for svc in "${SERVICES[@]}"; do
  unit="${svc}.service"
  if [[ -f "$SRC_DIR/$unit" ]]; then
    sudo cp "$SRC_DIR/$unit" "/etc/systemd/system/$unit"
  else
    echo "WARNING: missing $SRC_DIR/$unit (skipping copy; using existing unit)"
  fi
done

sudo systemctl daemon-reload

echo "Enabling and starting: ${SERVICES[*]}"
for svc in "${SERVICES[@]}"; do
  sudo systemctl enable --now "$svc"
done

echo
echo "Status:"
systemctl is-active "${SERVICES[@]}" || true
echo
curl -s -o /dev/null -w "camera /frame.jpg -> %{http_code}\n" http://127.0.0.1:8000/frame.jpg || true
ss -lnt | grep -E ':(8000|9072)\s' || true
echo
echo "Done. After a power cycle these should come up on their own."
echo "You still need to arm the dog in the website (on / go) before it will move."

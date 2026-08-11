# Motors On → Go → freeze

**Symptom:** Motors On → Go → any pose snaps to stand / motors=0, then ignores commands.

**Cause:** This dog’s IMU is dead. Balance turns on at `go` and freezes/wedges the Arduino. Pi may still log `Sending sit` while the MCU ignores motion until reset.

## Fix / deploy

Copy to the **exact** path (do not truncate `system`):

```bash
scp "/Users/shaayeralam/Spatial AI(Robotic Dog)/NewVersionDog/pi/system/evodogduino.py" pi@10.1.1.146:/home/pi/system/
ssh pi@10.1.1.146 'sudo systemctl restart evoduino'
ssh pi@10.1.1.146 'sudo journalctl -u evoduino -f'
```

Current bridge behavior:

- Pulses DTR on connect to reboot the Arduino, then re-sends calibration offsets
- Auto Balance OFF (`A`/`N`) immediately after every `go`

## What “good” looks like in the journal

- Startup: `CONNECTED ...` or `Trying ... (reset)` / `OPENED (reset, ...)`
- After Go: `balance disabled right after go`

Bad: `NO FIRMWARE RESPONSE` + old-style `OPENED (no handshake)` → wrong file on Pi, or MCU needs a full dog power-cycle.

## Ops checklist

1. Motors On → Go → wait for balance-off log → then Sit/Stand/etc.
2. Do **not** press Balance ON (re-freezes poses).
3. If wedged again: restart `evoduino` (software MCU reset) or power-cycle the dog.
4. Prefer poses over long Walk/Trot; gait can wedge this firmware.

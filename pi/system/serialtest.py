#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Staged Pi-to-Arduino firmware diagnostic (no ROS).

IMPORTANT: power-cycle the dog (switch off, wait 10s, switch on) before
running this. The firmware does NOT reset when the serial port reopens,
so a previous 'go' can leave it wedged and every result would be garbage.

Run on the Pi:
  sudo systemctl stop evoduino
  cd /home/pi/system
  python serialtest.py
  sudo systemctl start evoduino

Stage A: handshake, send calibration offsets, test pose commands WITHOUT 'go'.
Stage B: send 'go', watch exactly when/if the firmware stops answering,
         then test whether 'stop' recovers it.
"""
from __future__ import print_function
import glob
import json
import sys
import time

try:
    import serial
except ImportError:
    print("pyserial is required (python -m pip install pyserial)")
    sys.exit(1)

try:
    ask = raw_input  # Python 2
except NameError:
    ask = input      # Python 3

BAUD_CANDIDATES = [500000, 115200, 250000, 57600]


def list_ports():
    ports = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    preferred = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB1"]
    ordered = []
    for p in preferred:
        if p in ports and p not in ordered:
            ordered.append(p)
    for p in ports:
        if p not in ordered:
            ordered.append(p)
    return ordered


def read_for(s, seconds):
    reply = ""
    deadline = time.time() + seconds
    while time.time() < deadline:
        chunk = s.read(256)
        if chunk:
            reply += chunk
    return reply


def send(s, cmd, read_seconds=0.6):
    print("  > %s" % cmd)
    try:
        #encode so unicode strings (e.g. offsets from json) also work
        s.write((cmd + "\n").encode("utf-8"))
    except Exception as e:
        print("    write failed:", e)
        return None
    reply = read_for(s, read_seconds)
    if reply:
        print("    < %r" % reply)
    else:
        print("    < (no reply)")
    return reply


def load_offsets():
    try:
        with open("offsets.json", "rb") as f:
            return json.load(f)["offsets"]
    except Exception as e:
        print("could not read offsets.json:", e)
        return None


def probe(port, baud):
    print("=" * 60)
    print("Trying %s @ %d" % (port, baud))
    try:
        s = serial.Serial(port, baud, timeout=0.1, write_timeout=0.5)
    except Exception as e:
        print("  open failed:", e)
        return None

    # no auto-reset on this board, but wait anyway in case it does
    time.sleep(2.5)
    boot = read_for(s, 1.0)
    if boot:
        print("  boot/pending output:", repr(boot))
    try:
        s.flushInput()
    except Exception:
        pass

    reply = send(s, "i", 1.0)
    if reply and "info" in reply:
        print("  HANDSHAKE OK")
        return s
    print("  no 'info' reply -- firmware deaf at this baud, or wedged.")
    print("  (If every baud fails: power-cycle the dog and rerun.)")
    try:
        s.close()
    except Exception:
        pass
    return None


def stage_a(s):
    print("=" * 60)
    print("STAGE A: pose commands WITHOUT 'go'")

    offsets = load_offsets()
    if offsets:
        send(s, "e:" + offsets)
        time.sleep(0.2)
        send(s, "e:" + offsets)
    send(s, "u", 1.0)   # actual servo positions (apos)
    send(s, "on")
    time.sleep(1.0)
    send(s, "i", 1.0)
    ask("LOOK AT DOG: legs should be stiff. Straight or bent? Note it, press Enter...")

    send(s, "stand")
    time.sleep(3.0)
    send(s, "i", 1.0)
    ask("Did the legs BEND into a crouch-stand just now? Note it, press Enter...")

    send(s, "w,1500,0,48,59,0,48,59,0,48,59,0,48,59")
    time.sleep(3.0)
    send(s, "i", 1.0)
    ask("Any movement from the w-pose command? Note it, press Enter...")


def stage_b(s):
    print("=" * 60)
    print("STAGE B: 'go' behavior and 'stop' recovery")

    send(s, "go")
    for n in range(6):
        time.sleep(0.5)
        r = send(s, "i", 0.6)
        if r:
            print("    (still answering %d)" % n)
    ask("Did the dog move at 'go'? Note it, press Enter...")

    send(s, "stand")
    time.sleep(3.0)
    send(s, "i", 1.0)
    ask("Did 'stand' move the legs this time (after go)? Note it, press Enter...")

    #the webpage has balance toggles: 'a'/'n' = balance ON, 'A'/'N' = OFF.
    #If the firmware boots with balance active and the IMU/ultrasonic is
    #dead (dist=-1 on this dog), the balance loop may freeze the motion
    #engine at stand and ignore every pose. Turn balance OFF and retry.
    send(s, "A")
    send(s, "N")
    time.sleep(0.5)
    send(s, "sit")
    time.sleep(3.0)
    send(s, "i", 1.0)
    ask("BALANCE OFF test: did 'sit' work after A/N? Note it, press Enter...")

    #gait command from webpage walk arrows
    send(s, "m,f")
    time.sleep(3.0)
    send(s, "stand")
    time.sleep(1.0)
    send(s, "i", 1.0)
    ask("Did the dog try to WALK at m,f (after balance off)? Note it, press Enter...")

    #does a pose need an explicit speed first?
    send(s, "s:1.0")
    send(s, "sit")
    time.sleep(3.0)
    send(s, "i", 1.0)
    ask("Did 'sit' (after s:1.0) crouch the rear legs? Note it, press Enter...")

    #clean w-pose: raise front-right leg (no spaces in the command)
    send(s, "w,2000,0,10,65,0,38,65,0,-90,90,0,38,65")
    time.sleep(3.0)
    send(s, "i", 1.0)
    ask("Did a front leg lift (clean w-pose)? Note it, press Enter...")

    #same pose but with the stray space highfive.py uses -- parser test
    send(s, "w,2000,0,10,65,0,38,65,0, -90,90,0,38,65")
    time.sleep(3.0)
    send(s, "i", 1.0)
    ask("Did the leg lift with the SPACED w-pose too? Note it, press Enter...")

    #lean commands used by the webpage arrows
    send(s, "o,x")
    time.sleep(2.0)
    send(s, "i", 1.0)
    ask("Did the body lean (o,x)? Note it, press Enter...")
    send(s, "o,r")
    time.sleep(1.0)

    send(s, "stand")
    time.sleep(2.0)

    send(s, "stop")
    time.sleep(1.0)
    r = send(s, "i", 1.0)
    if r and "info" in r:
        print("  RECOVERED: firmware answers again after 'stop'")
        send(s, "off")
        return

    print("  still silent after 'stop' -- trying a recovery battery...")
    for cmd in (" ", "q", "noop", "home", "off", "stop"):
        send(s, cmd, 0.3)
        r = send(s, "i", 0.5)
        if r and "info" in r:
            print("  RECOVERED by %r" % cmd)
            send(s, "off")
            return
    #maybe the motion engine reconfigures the UART; re-check other bauds
    for baud in BAUD_CANDIDATES:
        print("  re-checking at %d baud" % baud)
        try:
            s.baudrate = baud
        except Exception as e:
            print("    could not switch baud:", e)
            continue
        r = send(s, "i", 0.7)
        if r and "info" in r:
            print("  RECOVERED at %d baud -- firmware switches baud at 'go'!" % baud)
            send(s, "off")
            return
    print("  WEDGED: nothing revives it; only a power cycle will.")


def main():
    ports = list_ports()
    if not ports:
        print("No /dev/ttyUSB* or /dev/ttyACM* devices found.")
        sys.exit(1)

    print("Did you power-cycle the dog just before this run? If not, do it now.")
    ask("Press Enter when the dog has been freshly power-cycled...")

    winner = None
    for port in ports:
        for baud in BAUD_CANDIDATES:
            s = probe(port, baud)
            if s is not None:
                winner = s
                break
        if winner is not None:
            break

    if winner is None:
        print("=" * 60)
        print("NO FIRMWARE RESPONSE on any port/baud even after a power cycle.")
        print("That points at firmware or wiring, not software.")
        sys.exit(2)

    stage_a(winner)
    stage_b(winner)
    try:
        winner.close()
    except Exception:
        pass
    print("=" * 60)
    print("Done. Copy ALL output above (plus your leg observations) back.")
    print("Restart the bridge: sudo systemctl start evoduino")


if __name__ == "__main__":
    main()

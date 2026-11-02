#!/usr/bin/env python3
"""ingame.py [--restart] [--level N]: into RC2 without anyone at the pad, and without a save.

--restart closes RPCS3 (unsaved progress is lost) and starts it under tools/trace.py, on the input
profile of tools/inputprofile.py, with the window that had the focus given it back. Then the main menu, and the game's own "go to level"
from there: no save is loaded, so none can be overwritten by the autosave on arrival, and the save
screens, which are RPCS3's overlay and take no input from inside the game, never come up. RC2's saves
are copied to build/saves all the same. Prints one line per step and exits 0 once a level is running.
Trace output goes to --log (default build/trace.log).
"""
import argparse
import os
import shutil
import signal
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inputprofile  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PY = sys.executable
PRESS = os.path.join(ROOT, "tools", "press.py")
PEEK = os.path.join(ROOT, "tools", "peek.py")
SAVES = os.path.expanduser("~/.config/rpcs3/dev_hdd0/home/00000001/savedata")
FRAME_COUNTER, GAME_MODE = 0x156B070, 0x156B064
LEVEL_WANTED, LEVEL_GO = 0x156B054, 0x156B050    # the game's "go to level", NOTES.md
MENU_SECONDS = 5                   # from the start of RPCS3 to the game's own code running
LOG = os.path.expanduser("~/.cache/rpcs3/RPCS3.log")


def say(text):
    print(time.strftime("%H:%M:%S"), text, flush=True)


def press(*words):
    subprocess.run([PY, PRESS, *words], check=True)


def read(address):
    out = subprocess.run([PY, PEEK, f"r {address:x} 4"], capture_output=True, text=True).stdout.split()
    return struct.unpack(">i", bytes.fromhex(out[1]))[0] if len(out) > 1 else None


def rpcs3_pid():
    out = subprocess.run(["pgrep", "-x", "AppRun.wrapped"], capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else None


def fatal():
    try:
        return any("·F " in line for line in open(LOG, errors="replace"))
    except OSError:
        return False


def wait(what, test, seconds, check=True):
    end = time.time() + seconds
    while time.time() < end:
        if check and fatal():
            sys.exit(f"RPCS3 logged a fatal error while waiting for {what}")
        if test():
            return
        time.sleep(2)
    sys.exit(f"timed out waiting for {what}")


def restart(log):
    os.makedirs(os.path.join(ROOT, "build", "saves"), exist_ok=True)
    for name in os.listdir(SAVES):
        if "RC2" in name:
            shutil.copytree(os.path.join(SAVES, name), os.path.join(ROOT, "build", "saves", name), dirs_exist_ok=True)
    pid = rpcs3_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        wait("RPCS3 to close", lambda: not rpcs3_pid(), 20, check=False)   # the log is still the old game's
    inputprofile.write()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    focus = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True).stdout.strip()
    with open(log, "w") as out:
        subprocess.Popen([PY, os.path.join(ROOT, "tools", "trace.py"), "--no-gui", "--input-config", inputprofile.NAME],
                         stdout=out, stderr=out, start_new_session=True, env=env)
    say("RPCS3 started")
    end = time.time() + MENU_SECONDS
    while time.time() < end:                # the new window takes the focus: give it back
        if focus and subprocess.run(["xdotool", "search", "--name", "FPS:"], capture_output=True).stdout:
            subprocess.run(["xdotool", "windowactivate", focus], capture_output=True)
            focus = None
        time.sleep(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--restart", action="store_true")
    ap.add_argument("--level", type=int, default=0, help="the level to go to (default 0, the Flying Lab)")
    ap.add_argument("--log", default=os.path.join(ROOT, "build", "trace.log"))
    args = ap.parse_args()
    if args.restart:
        restart(args.log)
    elif not rpcs3_pid():
        sys.exit("RPCS3 is not running (--restart starts it)")
    if (read(FRAME_COUNTER) or 0) > 0:
        say("a level is running already")
        return
    wait("the title", lambda: read(GAME_MODE) not in (None, 0), 300)
    for _ in range(12):                # Start skips the intro first, then opens the main menu (mode 3);
        press("start:0.6", "wait:3.5")  # going to a level during the intro crashes its sound thread
        if read(GAME_MODE) == 3:
            break
    else:
        sys.exit("the main menu did not open")
    subprocess.run([PY, PEEK, f"w {LEVEL_WANTED:x} {args.level:08x}, w {LEVEL_GO:x} 00000001"], check=True, stdout=subprocess.DEVNULL)
    say(f"going to level {args.level}")
    wait("the level", lambda: read(GAME_MODE) == 0 and (read(FRAME_COUNTER) or 0) > 30, 180)
    say(f"in the level, mode {read(GAME_MODE)}")


if __name__ == "__main__":
    main()

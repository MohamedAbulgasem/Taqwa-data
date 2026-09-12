"""Finish and publish each reciter as soon as its fetch completes.

    python3 watch.py

Polls the work directory: when a reciter has all 6,236 files on disk and no
fetch process is still working on it, `finish.py` takes it through verify,
repair, pack and publish.  One reciter at a time, so uploads never overlap.
Exits when every reciter in the table is either published or has failed four
times; four because this runs unattended for hours and a single GitHub or CDN
hiccup should not cost a reciter.
"""

import os
import subprocess
import sys
import time

from common import RECITERS, WORK, log, outdir

HERE = os.path.dirname(os.path.abspath(__file__))


def running(script, rid):
    r = subprocess.run(["pgrep", "-f", f"{script} {rid}"], capture_output=True)
    return r.returncode == 0


def busy(rid):
    """True while anything else in the pipeline is already working on `rid`."""
    return any(running(s, rid) for s in
               ("fetch.py", "repair.py", "pack.py", "publish.py", "finish.py"))


def fetched(rid):
    """The fetch for this reciter has run its course.

    Not "all 6,236 present": a fetch can end a few files short when the CDN
    answers 502 for individual objects, and repair.py inside finish.py is what
    closes those.  A directory that is still far from complete means the fetch
    never ran or died, and is left alone.
    """
    d = outdir(rid)
    if not os.path.isdir(d):
        return False
    return sum(1 for f in os.listdir(d) if f.endswith(".mp3")) >= 6100


def main():
    attempts = {}
    while True:
        pending = []
        for rid, *_ in RECITERS:
            if os.path.exists(os.path.join(WORK, "state", f"{rid}.done")):
                continue
            if attempts.get(rid, 0) >= 4:
                continue
            pending.append(rid)
        if not pending:
            log("watch: nothing left to do")
            return 0
        for rid in pending:
            if busy(rid) or not fetched(rid):
                continue
            attempts[rid] = attempts.get(rid, 0) + 1
            log(f"watch: finishing {rid} (attempt {attempts[rid]})")
            subprocess.run([sys.executable, os.path.join(HERE, "finish.py"), rid])
            break
        else:
            time.sleep(60)


if __name__ == "__main__":
    sys.exit(main())

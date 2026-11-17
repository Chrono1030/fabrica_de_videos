"""Sample simultaneous RSS of the renderer process tree; GNU time records CPU."""

import os
import signal
import subprocess
import time
from pathlib import Path


def tree_rss(pid):
    rows = {}
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            rest = path.read_text().rsplit(")", 1)[1].split()
            rows[int(path.parent.name)] = (int(rest[1]), int(rest[21]) * 4096)
        except (OSError, ValueError, IndexError):
            continue
    descendants = {pid}
    while True:
        extended = descendants | {
            p for p, (parent, _) in rows.items() if parent in descendants
        }
        if extended == descendants:
            break
        descendants = extended
    return sum(rows[p][1] for p in descendants if p in rows)


def measured(args, cwd, env, logfile, timeout=1800):
    start = time.monotonic()
    peak = 0
    with logfile.open("w") as log:
        with subprocess.Popen(
            [str(a) for a in args],
            cwd=cwd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process:
            while process.poll() is None:
                peak = max(peak, tree_rss(process.pid))
                if time.monotonic() - start > timeout:
                    os.killpg(process.pid, signal.SIGTERM)
                    raise TimeoutError("renderer timeout")
                time.sleep(0.05)
            return process.returncode, peak / 1024**2

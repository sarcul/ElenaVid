"""Render the full opera's picture in chunks (resumable), join them and lay in the master audio.

    ELENA_EDITION=full python -m elenavid.video.render_full [--chunk=300] [--jobs=2] [--only-join]
                                                            [--encoder=auto|nvenc|x264]

Each chunk is a separate process writing <cache>/video/chunk_NN.mp4 (picture only) and a marker file
when it completes, so an interrupted render resumes where it stopped. The encoder is chosen once for
the whole run (NVENC if an NVIDIA GPU can run it, otherwise x264), so every chunk has the same
settings and the chunks join without re-encoding.

On Windows laptops with two GPUs, OpenGL may default to the integrated one; setting the environment
variable SHIM_MCCOMPAT=0x800000001 for this process asks the NVIDIA driver to take it.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import EDITION, FPS, OUT, AUDIO_OUT, DURATION, CACHE_DIR
from . import encode

VIDEO = CACHE_DIR / "video"          # the chunks are intermediate: kept beside the audio cache, not in output/
FINAL = OUT / "elena_opera_full.mp4"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def chunk_jobs(chunk):
    n = int(DURATION // chunk) + (1 if DURATION % chunk > 1e-6 else 0)
    return [(i, i * chunk, min(DURATION, (i + 1) * chunk)) for i in range(n)]


def render_chunk(i, t0, t1, kind):
    out = VIDEO / f"chunk_{i:02d}.mp4"
    done = VIDEO / f"chunk_{i:02d}.done"
    if done.exists() and out.exists():
        return i, 0.0, "cached"
    start = time.time()
    cmd = [sys.executable, "-m", "elenavid.video.render", f"{t0:.3f}", f"{t1:.3f}", f"--out={out.as_posix()}",
           f"--encoder={kind}"]
    with open(VIDEO / f"chunk_{i:02d}.log", "w", encoding="utf-8") as lf:
        r = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=os.environ.copy())
    if r.returncode != 0:
        return i, time.time() - start, f"failed ({r.returncode}); see {VIDEO / f'chunk_{i:02d}.log'}"
    done.write_text(f"{t0} {t1} {kind}\n")
    return i, time.time() - start, "ok"


def join(jobs):
    lst = VIDEO / "chunks.txt"
    lst.write_text("".join(f"file 'chunk_{i:02d}.mp4'\n" for i, _, _ in jobs), encoding="utf-8")
    audio = AUDIO_OUT / "elena_full_master.wav"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
    if audio.exists():
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                # AAC overshoots the master's true peak by about 0.1 dB: trim 0.2 dB (as for the film)
                "-af", "volume=-0.2dB", "-c:a", "aac", "-b:a", "320k", "-shortest"]
    else:
        log(f"no master audio at {audio}: joining the picture alone")
        cmd += ["-c:v", "copy"]
    cmd += ["-movflags", "+faststart", str(FINAL)]
    log("joining", len(jobs), "chunks" + (" and the master audio" if audio.exists() else ""))
    subprocess.run(cmd, check=True)
    log("wrote", FINAL)


def main(argv=None):
    if EDITION != "full":
        print("set ELENA_EDITION=full (or run: elenavid video --edition full)")
        return 2
    encode.require_ffmpeg()
    argv = sys.argv[1:] if argv is None else argv
    opts = dict(a.lstrip("-").split("=", 1) if "=" in a else (a.lstrip("-"), "1") for a in argv)
    chunk = float(opts.get("chunk", 300))
    jobs_n = int(opts.get("jobs", 2))
    VIDEO.mkdir(parents=True, exist_ok=True)
    jobs = chunk_jobs(chunk)
    if "only-join" not in opts:
        # one decision for every chunk; a resumed run keeps the encoder its finished chunks used
        kinds = {p.read_text().split()[2] for p in VIDEO.glob("chunk_*.done") if len(p.read_text().split()) > 2}
        kind = encode.choose(opts.get("encoder")) if not kinds else kinds.pop()
        log(f"encoder: {encode.reason(kind)}")
        t_all = time.time()
        frames = int(round(DURATION * FPS))
        log(f"{len(jobs)} chunks of {chunk:.0f} s, {frames} frames, {jobs_n} at a time -> {VIDEO}")
        failed = []
        with ThreadPoolExecutor(max_workers=jobs_n) as ex:
            futs = [ex.submit(render_chunk, *j, kind) for j in jobs]
            done_s = 0.0
            for f in as_completed(futs):
                i, secs, status = f.result()
                if status.startswith("failed"):
                    failed.append(i)
                done_s += jobs[i][2] - jobs[i][1]
                el = time.time() - t_all
                log(f"  chunk {i:02d} {status} in {secs / 60:4.1f} min  ({done_s / DURATION:4.0%} of the picture, "
                    f"{el / 60:5.1f} min elapsed)")
        if failed:
            log("failed chunks:", failed, "- run again to retry them")
            return 1
    join(jobs)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""What this machine offers ElenaVid: Python and packages, ffmpeg and its encoders (and which one the
renderer would choose), the OpenGL renderer, fonts, paths and free disk space.

    elenavid qa environment [--edition film|full]

Exit status 1 if something the pipeline needs is missing (ffmpeg, or an OpenGL 4.3 context).
"""
from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys

from ..config import CACHE_DIR, EDITION, OUT, ROOT


def main(argv=None):
    problems = []
    print(f"python      {sys.version.split()[0]} on {platform.platform()}")
    for m in ("numpy", "scipy", "numba", "llvmlite", "moderngl", "PIL", "matplotlib"):
        try:
            print(f"  {m:10s} {importlib.import_module(m).__version__}")
        except ImportError:
            print(f"  {m:10s} missing" + ("  (optional: level plots)" if m == "matplotlib" else ""))
            if m != "matplotlib":
                problems.append(f"python package {m} missing")
    from ..video import encode
    ff = encode.ffmpeg_path()
    if ff:
        first = subprocess.run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True).stdout
        print(f"ffmpeg      {first.splitlines()[0] if first else ff}")
        enc = encode.encoders()
        print(f"  encoders  h264_nvenc {'listed' if 'h264_nvenc' in enc else 'absent'}, "
              f"NVENC {'usable' if encode.nvenc_available() else 'not usable here'}, "
              f"libx264 {'present' if 'libx264' in enc else 'absent'}")
        kind = encode.choose()
        print(f"  renderer would encode with: {encode.reason(kind)}")
    else:
        print("ffmpeg      not found on the path")
        problems.append("ffmpeg missing")
    try:
        import moderngl
        ctx = moderngl.create_standalone_context(require=430)
        rend = ctx.info["GL_RENDERER"]
        print(f"opengl      {rend}  ({ctx.info['GL_VERSION']})")
        if os.name == "nt" and "NVIDIA" not in rend and ff and encode.nvenc_available():
            print("  this machine has an NVIDIA GPU but OpenGL runs elsewhere; for this process only, set\n"
                  "  SHIM_MCCOMPAT=0x800000001 to ask the NVIDIA driver to take OpenGL")
        ctx.release()
    except Exception as ex:                       # no GPU, no driver, or a context below 4.3
        print(f"opengl      unavailable: {ex}")
        problems.append("no OpenGL 4.3 context")
    from ..video.text import ROLES, find_font
    print("fonts       " + ", ".join(f"{r}: {os.path.basename(find_font(r) or 'built-in')}" for r in ROLES))
    print(f"edition     {EDITION}")
    print(f"project     {ROOT}")
    for label, p in (("outputs", OUT), ("cache", CACHE_DIR)):
        free = shutil.disk_usage(p).free / 1e9
        print(f"{label:11s} {p}  ({free:.0f} GB free)")
    print(f"cpu         {os.cpu_count()} logical processors")
    if problems:
        print("\nmissing: " + "; ".join(problems))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

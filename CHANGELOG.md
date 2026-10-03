# Changelog

## 1.0.0 (2026-10-03)

The first public release.

- **Two editions of *Elena*:**
  - the ten-minute motion-graphics film;
  - the complete opera in three acts, about two hours.
- **The command line:** `elenavid score | audio | video | build | encoder | qa`, with `--edition film|full`.
- **Automatic encoder choice:** NVIDIA NVENC when the machine can run it, otherwise x264 in software (OpenH264 as a last resort). It can be overridden with `--encoder` or `ELENA_ENCODER`.
- **Quality checks** (`elenavid qa`):
  - `environment`, `timeline`, `events`, `prosody` and `levels`;
  - `delivery`, `contact-sheet`, `qc-sheet` and `compare-frames`.
- **Portability:**
  - typefaces fall back to DejaVu, Liberation or Pillow's own when the originals are absent;
  - the project and cache folders can be set with `ELENA_ROOT` and `ELENA_CACHE`;
  - caches go to each platform's user cache folder.
- **Testing:** unit tests, and continuous integration on Linux and Windows. CI composes both scores and runs the checks that need neither a GPU nor ffmpeg.

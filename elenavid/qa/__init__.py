"""Quality checks, run with `elenavid qa TOOL [--edition film|full]` or `python -m elenavid.qa.TOOL`.

delivery        the delivered MP4: streams, loudness and true peak, sync with the master, the picture
                at its story anchors, and (full opera) the joins between render chunks
contact_sheet   stills from the delivered file: one per section plus the required shot's moments
qc_sheet        sheets of the renderer's QC stills (frames_qc/)
compare_frames  re-render frames and compare them with reference stills (reproducibility)
timeline        the score timeline: instruments, notes inside their sections, cues, locations, motifs
events          call every sound generator in the cue sheet with its real arguments
prosody         how often the full opera's stressed syllables fall on strong beats; melodic intervals
levels          loudness per section of the master (and an optional level plot)
environment     Python packages, ffmpeg, the encoder this machine would use, the OpenGL renderer, fonts
"""

TOOLS = ("delivery", "contact_sheet", "qc_sheet", "compare_frames", "timeline", "events", "prosody", "levels",
         "environment")

"""Generate the 30-second parent-facing voiceover with Kokoro (free, local, offline).

Setup (one time):
    pip install kokoro-onnx soundfile numpy
    # model files from https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0)
    #   kokoro-v1.0.onnx  and  voices-v1.0.bin  in the working directory

Run:
    python generate_voiceover.py
    ffmpeg -i brief_raw.wav -af loudnorm=I=-14:TP=-1.5 -ar 48000 brief_vo_30s.wav
"""
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

k = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

# (locked script line, speaking speed, start time in seconds)
lines = [
    ("When your child learns something in class, the brain gets to work.", 0.92, 0),
    ("New information is first processed and held briefly in working memory.", 0.92, 5),
    ("But hearing a lesson once does not mean it will be remembered.", 0.92, 10),
    ("With attention, understanding, repeated practice and good sleep, the brain "
     "strengthens connections that help form long-term memories.", 1.25, 16),
    ("So help your child remember: revisit lessons, practise recalling them, and give "
     "the brain time to consolidate what it has learned.", 1.15, 23),
]

sr = 24000
track = np.zeros(int(30 * sr), dtype=np.float32)
for i, (text, speed, start) in enumerate(lines, 1):
    audio, sr = k.create(text, voice="af_sarah", speed=speed, lang="en-us")
    print(f"line{i}: {start:.2f} -> {start + len(audio) / sr:.2f}s")
    o = int(start * sr)
    track[o:o + len(audio)] = audio[: max(0, len(track) - o)]
sf.write("brief_raw.wav", track, sr)

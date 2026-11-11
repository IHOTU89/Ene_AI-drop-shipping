"""Synthesised sound design for the 30 s film: chalk, pen, neural ticks, transitions, pad.
Everything is generated here (no licensed or downloaded audio)."""
import numpy as np, soundfile as sf, os, sys
from scipy.signal import butter, lfilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SR = 48000
DUR = 30.0
N = int(DUR * SR)
rng = np.random.default_rng(5)

def bp(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return lfilter(b, a, x)

def hp(x, f):
    b, a = butter(2, f / (SR / 2), btype="high")
    return lfilter(b, a, x)

def lp(x, f):
    b, a = butter(2, f / (SR / 2), btype="low")
    return lfilter(b, a, x)

def place(buf, clip, t):
    i = int(t * SR)
    n = min(len(clip), len(buf) - i)
    if n > 0:
        buf[i:i + n] += clip[:n]

def env_exp(n, decay):
    return np.exp(-np.arange(n) / SR * decay)

# Chalk writing: short, gritty bursts with a light rhythm (teacher writes 0.5-4.5 s)
sfx = np.zeros(N)
chalk = np.zeros(N)
for t0 in np.arange(0.5, 4.5, 0.42):
    n = int(0.22 * SR)
    burst = bp(rng.standard_normal(n), 2500, 7000) * np.hanning(n) * 0.10
    place(chalk, burst, t0 + rng.uniform(-0.02, 0.02))
# Pen on paper for the child (0-5 s and 23-30 s)
pen = np.zeros(N)
for a, b in [(0.3, 5.0), (23.2, 29.5)]:
    t = np.arange(a, b, 0.05)
    for tt in t:
        n = int(0.05 * SR)
        place(pen, hp(rng.standard_normal(n), 3000) * np.hanning(n) * 0.035, tt)

# Neural ticks, one per activation: brain sparks (7-10 s), working memory (11-13 s), long-term flashes (16-23 s)
ticks = np.zeros(N)
def tick(t, amp=0.22):
    n = int(0.09 * SR)
    tone = np.sin(2 * np.pi * 1850 * np.arange(n) / SR) * env_exp(n, 60)
    grain = bp(rng.standard_normal(n), 3000, 9000) * env_exp(n, 90)
    place(ticks, (tone * 0.6 + grain * 0.5) * amp, t)
for f in (212, 222, 238, 250, 284):
    tick(f / 30)
for f in (330, 360, 390):
    tick(f / 30, 0.26)
for f in range(480, 690, 24):
    tick((f + 6) / 30, 0.34)

# Transition swells at the cuts (frame 300 into the neural macro, frame 690 back to the classroom)
trans = np.zeros(N)
for start, length, up in [(9.8, 0.9, True), (22.7, 0.9, False)]:
    n = int(length * SR)
    t = np.arange(n) / SR
    sweep = bp(rng.standard_normal(n), 300, 2600) * (np.sin(np.pi * t / length) ** 2) * 0.22
    place(trans, sweep, start)

# Subtle pad under the narration: slow A minor -> F -> C -> G, detuned, very quiet
pad = np.zeros(N)
chords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (261.6, 329.6, 392.0), (196.0, 246.9, 293.7)]
seg = DUR / len(chords)
for ci, ch in enumerate(chords):
    t0, t1 = ci * seg, (ci + 1) * seg
    i0, i1 = int(t0 * SR), int(t1 * SR)
    t = np.arange(i1 - i0) / SR
    for f in ch:
        for detune in (0.997, 1.003):
            pad[i0:i1] += np.sin(2 * np.pi * f * detune * t) * 0.035
# Smooth crossfades between chords and fade in/out
win = np.ones(N)
fade = int(1.5 * SR)
win[:fade] = np.linspace(0, 1, fade)
win[-fade:] = np.linspace(1, 0, fade)
pad = lp(pad, 1200) * win

music = pad + trans * 0.7
sfx_bus = chalk + pen + ticks + trans
mix = np.stack([music * 0.9 + sfx_bus * 0.9] * 2, axis=1)
mix = np.clip(mix, -0.98, 0.98).astype(np.float32)

sf.write(os.path.join(OUT, "sfx_music_stem.wav"), mix, SR)
sf.write(os.path.join(OUT, "music_only.wav"), np.stack([music] * 2, axis=1).astype(np.float32), SR)
print("written", OUT)

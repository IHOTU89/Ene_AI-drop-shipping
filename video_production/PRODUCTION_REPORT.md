# How Children Remember — 30-second explainer

## Production report

### Deliverables
| File | What it is |
|---|---|
| `memory_film_1080p.mp4` | Final film: 1920×1080, 30 fps, 30.0 s, H.264 and AAC |
| `memory_scene.blend` | Full Blender scene. Open in Blender 4.2+ or 5.x and press Render Animation. |
| `brief_vo_30s.wav` | Voiceover only (female, af_sarah), normalised to −14 LUFS |
| `final_mix.wav` | Voiceover with the music and sound effects, as used in the MP4 |
| `build_memory_scene.py` | Builds the whole scene from code and renders it |
| `build_sound.py` | Synthesises the music bed and sound effects |
| `generate_voiceover.py` | Generates the voiceover from the locked script |

The large media files (the MP4 and the WAVs) are kept out of git and delivered alongside it.

### Shot list (as built)
| Time | Frames | Shot |
|---|---|---|
| 0–5 s | 1–150 | Over-the-shoulder push-in. The teacher writes **2x + 4 = 10**; the child writes in a notebook. |
| 5–10 s | 150–300 | Push in to the child's head. The skull and hair turn semi-transparent, the brain is revealed, and three activity sparks fire. |
| 10–16 s | 300–480 | Neural macro, labelled **WORKING MEMORY**. Two pathways fire. The unpractised pathway fires once and fades. |
| 16–23 s | 480–690 | Labelled **LONG-TERM MEMORY**. The practised pathway pulses on every repetition, its connection thickens, and its synapses grow. The unused pathway thins. Nothing physically travels. |
| 23–30 s | 690–900 | The head becomes solid again. The camera pulls back while the child solves the problem independently. |

### Locked voiceover script
1. **0 s:** "When your child learns something in class, the brain gets to work."
2. **5 s:** "New information is first processed and held briefly in working memory."
3. **10 s:** "But hearing a lesson once does not mean it will be remembered."
4. **16 s:** "With attention, understanding, repeated practice and good sleep, the brain strengthens connections that help form long-term memories."
5. **23 s:** "So help your child remember: revisit lessons, practise recalling them, and give the brain time to consolidate what it has learned."

### Tools and licensing
Everything is free and local. There are no paid APIs, subscriptions or third-party assets.
- **Blender 5.0 (bpy):** GPL. Rendered with Cycles. Every model and material is built procedurally in the script, so no external models or textures are used.
- **Kokoro TTS (kokoro-onnx, model v1.0):** Apache-2.0. Voice: af_sarah.
- **Music and sound effects:** synthesised from scratch with NumPy and SciPy (`build_sound.py`), so there are no licensing restrictions.
- **ffmpeg:** used for the mix, loudness normalisation and encoding.

### Audio
- The music bed is a soft Am–F–C–G pad, ducked under the voice with a sidechain.
- Sound effects: classroom chalk and pen, neural ticks timed to every synapse flash, and soft swells at the 10 s and 23 s transitions.
- Final mix: −14 LUFS integrated, −1.5 dBTP true-peak ceiling.

### Limitations, and what would raise the quality
1. **The characters are stylised, not realistic.**
   - The child and teacher are built from primitive shapes.
   - Realistic humans would need rigged character models, for example free CC0 or CC-BY characters from Blender Studio or Mixamo (free, needs an Adobe account) or MakeHuman (CC0).
   - I didn't add any of these, because the brief asked me to clear external assets with you first.
2. **The brain is an approximation:** a displaced sphere with a cerebellum and brain stem, not an anatomical model.
3. **Render quality.**
   - There are 4 Cycles samples per frame, with denoising. That keeps the full 900 frames to a few hours on the cloud CPU.
   - EEVEE (Blender's fast real-time renderer) couldn't run here because the container has no GPU or OpenGL.
   - On your own machine, open the .blend, raise the samples to 64–128 or switch to EEVEE, and re-render for a cleaner image.
4. **Shot changes:** shots 2→3 and 4→5 change between the classroom and the neural set with a hard cut on a sound swell, not a continuous fly-through.
5. **The animation is simple:** writing is a looping arm rotation, with no hand or finger animation and no facial performance.
6. **The voice is a neural text-to-speech voice, not a human voice artist.**

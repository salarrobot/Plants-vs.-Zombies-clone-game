"""
audio.py
========
Procedural sound.  Rather than ship audio files, the :class:`SoundManager`
synthesises every effect (and a short looping background tune) as raw 16-bit
PCM at start-up.  This keeps the project to a single dependency (pygame) and
guarantees audio works on any machine.

All synthesis is wrapped in defensive error handling: if the mixer cannot be
initialised (e.g. a head-less machine with no audio device) the manager simply
disables itself and every call becomes a no-op, so the game still runs.
"""

import array
import math
import random

import pygame

import config as C


def _envelope(i, n, attack=0.01, release=0.3):
    """Return a 0..1 amplitude multiplier giving a soft attack and decay."""
    t = i / n
    a = min(1.0, t / attack) if attack > 0 else 1.0
    r = 1.0 if t < (1.0 - release) else max(0.0, (1.0 - t) / release)
    return a * r


class SoundManager:
    """Synthesises and plays all sound effects plus background music."""

    SAMPLE_RATE = 44100

    def __init__(self):
        self.enabled = False
        self.sfx_volume = 0.6
        self.music_volume = 0.35
        self.muted = False
        self.sounds = {}
        self.music = None
        try:
            # pre_init lets us pick a format we can synthesise exactly.
            pygame.mixer.pre_init(self.SAMPLE_RATE, -16, 2, 512)
            pygame.mixer.init()
            self.enabled = True
        except Exception as exc:           # pragma: no cover - hardware dependent
            print(f"[audio] mixer unavailable, sound disabled: {exc}")
            self.enabled = False
            return
        self._build_sounds()

    # -- synthesis ---------------------------------------------------------
    def _tone(self, freq, ms, volume=0.5, kind="sine",
              attack=0.01, release=0.4, freq_end=None):
        """Create a pygame Sound from a synthesised waveform.

        *freq_end* allows a linear pitch glide (used for explosions / pickups).
        """
        n = max(1, int(self.SAMPLE_RATE * ms / 1000.0))
        buf = array.array("h")
        amp = int(32767 * volume)
        phase = 0.0
        for i in range(n):
            f = freq if freq_end is None else freq + (freq_end - freq) * (i / n)
            phase += 2 * math.pi * f / self.SAMPLE_RATE
            if kind == "sine":
                sample = math.sin(phase)
            elif kind == "square":
                sample = 1.0 if math.sin(phase) >= 0 else -1.0
            elif kind == "saw":
                sample = (phase / math.pi) % 2 - 1
            elif kind == "noise":
                sample = random.uniform(-1, 1)
            else:
                sample = math.sin(phase)
            value = int(amp * sample * _envelope(i, n, attack, release))
            value = max(-32767, min(32767, value))
            buf.append(value)   # left
            buf.append(value)   # right
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _mix(self, *layers):
        """Mix several (freq, ms, volume, kind) tuples into one Sound."""
        rendered = [self._build_samples(*layer) for layer in layers]
        length = max(len(r) for r in rendered)
        out = array.array("h", [0] * length)
        for r in rendered:
            for i in range(len(r)):
                out[i] = max(-32767, min(32767, out[i] + r[i]))
        return pygame.mixer.Sound(buffer=out.tobytes())

    def _build_samples(self, freq, ms, volume, kind):
        """Helper returning a mono int16 array for one tone (for mixing)."""
        n = max(1, int(self.SAMPLE_RATE * ms / 1000.0))
        arr = array.array("h")
        amp = int(32767 * volume)
        phase = 0.0
        for i in range(n):
            phase += 2 * math.pi * freq / self.SAMPLE_RATE
            if kind == "square":
                sample = 1.0 if math.sin(phase) >= 0 else -1.0
            elif kind == "noise":
                sample = random.uniform(-1, 1)
            else:
                sample = math.sin(phase)
            value = int(amp * sample * _envelope(i, n, 0.01, 0.4))
            arr.append(max(-32767, min(32767, value)))
        return arr

    def _build_sounds(self):
        try:
            self.sounds["shoot"] = self._tone(540, 90, 0.30, "square", release=0.6)
            self.sounds["frost"] = self._tone(700, 120, 0.28, "sine", freq_end=400)
            self.sounds["hit"] = self._tone(220, 70, 0.30, "noise", release=0.7)
            self.sounds["plant"] = self._tone(330, 120, 0.35, "sine", freq_end=520)
            self.sounds["sun"] = self._tone(660, 160, 0.35, "sine", freq_end=990)
            self.sounds["explode"] = self._tone(120, 480, 0.55, "noise",
                                                attack=0.001, release=0.8)
            self.sounds["zombie_die"] = self._tone(160, 260, 0.35, "saw",
                                                   freq_end=70)
            self.sounds["mower"] = self._tone(90, 600, 0.4, "square", release=0.5)
            self.sounds["click"] = self._tone(480, 60, 0.3, "square", release=0.5)
            self.sounds["wave"] = self._tone(180, 500, 0.4, "saw", freq_end=240)
            self.sounds["win"] = self._mix((523, 600, 0.3, "sine"),
                                           (659, 600, 0.25, "sine"),
                                           (784, 600, 0.2, "sine"))
            self.sounds["lose"] = self._mix((220, 700, 0.3, "saw"),
                                            (174, 700, 0.25, "saw"))
            self.sounds["achieve"] = self._mix((784, 400, 0.25, "sine"),
                                               (1046, 400, 0.2, "sine"))
            self.music = self._build_music()
            self._apply_volumes()
        except Exception as exc:           # pragma: no cover
            print(f"[audio] sound synthesis failed: {exc}")
            self.enabled = False

    def _build_music(self):
        """Build a short, gentle looping chip-tune melody."""
        # A simple major-key loop (frequencies in Hz), quarter notes.
        melody = [392, 440, 523, 440, 392, 330, 392, 294,
                  392, 440, 523, 587, 523, 440, 392, 392]
        note_ms = 320
        full = array.array("h")
        amp = int(32767 * 0.18)
        for note in melody:
            n = int(self.SAMPLE_RATE * note_ms / 1000.0)
            phase = 0.0
            bass = note / 2
            bphase = 0.0
            for i in range(n):
                phase += 2 * math.pi * note / self.SAMPLE_RATE
                bphase += 2 * math.pi * bass / self.SAMPLE_RATE
                env = _envelope(i, n, 0.02, 0.25)
                s = (math.sin(phase) * 0.6 + math.sin(bphase) * 0.4) * env
                value = max(-32767, min(32767, int(amp * s)))
                full.append(value)
                full.append(value)
        return pygame.mixer.Sound(buffer=full.tobytes())

    # -- control -----------------------------------------------------------
    def _apply_volumes(self):
        if not self.enabled:
            return
        for snd in self.sounds.values():
            snd.set_volume(0.0 if self.muted else self.sfx_volume)
        if self.music:
            self.music.set_volume(0.0 if self.muted else self.music_volume)

    def play(self, name):
        """Play a named sound effect (silently ignores unknown names)."""
        if not self.enabled or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def start_music(self):
        if not self.enabled or self.music is None:
            return
        try:
            self.music.play(loops=-1)
        except Exception:
            pass

    def stop_music(self):
        if self.enabled and self.music is not None:
            self.music.stop()

    def toggle_mute(self):
        self.muted = not self.muted
        self._apply_volumes()
        return self.muted

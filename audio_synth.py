"""Procedural 8-bit sound effects generator and manager for Cosmic Defender.
Synthesizes retro audio files at runtime without requiring third-party audio downloads.
"""

import math
import os
import random
import struct
import wave

SAMPLE_RATE = 22050  # 22.05 kHz standard for lightweight retro audio


def _write_wav(filename, samples, sample_rate=SAMPLE_RATE):
    """Write raw float audio samples (-1.0 to 1.0) into a 16-bit PCM WAV file."""
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Convert to 16-bit signed integers
        packed_frames = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            int_val = int(clamped * 32767.0)
            packed_frames.extend(struct.pack("<h", int_val))

        wav_file.writeframes(packed_frames)


def generate_laser_sound(path):
    """Downward frequency sweep with snappy envelope."""
    duration = 0.15
    total_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(total_samples):
        t = i / total_samples
        freq = 900.0 * (1.0 - t * 0.75) + random.uniform(-15, 15)
        phase = 2.0 * math.pi * freq * (i / SAMPLE_RATE)
        # Square wave mixed with sine
        raw = 0.6 * (1.0 if math.sin(phase) > 0 else -1.0) + 0.4 * math.sin(phase)
        env = (1.0 - t) ** 1.5
        samples.append(raw * env * 0.5)
    _write_wav(path, samples)


def generate_explosion_sound(path):
    """White noise mixed with pitch decay and sub rumble."""
    duration = 0.45
    total_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(total_samples):
        t = i / total_samples
        noise = random.uniform(-1.0, 1.0)
        rumble = math.sin(2.0 * math.pi * (120.0 * (1.0 - t * 0.8)) * (i / SAMPLE_RATE))
        raw = 0.7 * noise + 0.4 * rumble
        env = math.exp(-6.0 * t)
        samples.append(raw * env * 0.7)
    _write_wav(path, samples)


def generate_pickup_sound(path):
    """Ascending melodic retro arpeggio (C5 -> E5 -> G5 -> C6)."""
    notes = [523.25, 659.25, 783.99, 1046.50]
    duration_per_note = 0.05
    samples = []
    for freq in notes:
        n_samples = int(duration_per_note * SAMPLE_RATE)
        for i in range(n_samples):
            t = i / n_samples
            phase = 2.0 * math.pi * freq * (i / SAMPLE_RATE)
            # Pure square wave with slight triangle
            raw = 0.7 * (1.0 if math.sin(phase) > 0 else -1.0)
            env = 1.0 - (t * 0.6)
            samples.append(raw * env * 0.4)
    _write_wav(path, samples)


def generate_shield_sound(path):
    """Frequency sweep upward with vibrato."""
    duration = 0.28
    total_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(total_samples):
        t = i / total_samples
        vibrato = math.sin(2.0 * math.pi * 30.0 * (i / SAMPLE_RATE)) * 20.0
        freq = 300.0 + (t * 700.0) + vibrato
        phase = 2.0 * math.pi * freq * (i / SAMPLE_RATE)
        raw = math.sin(phase)
        env = math.sin(t * math.pi)
        samples.append(raw * env * 0.5)
    _write_wav(path, samples)


def generate_bomb_sound(path):
    """Deep screen-shaking shockwave explosion."""
    duration = 0.7
    total_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(total_samples):
        t = i / total_samples
        noise = random.uniform(-1.0, 1.0)
        sub = math.sin(2.0 * math.pi * (80.0 * (1.0 - t * 0.9)) * (i / SAMPLE_RATE))
        raw = 0.5 * noise + 0.6 * sub
        env = math.exp(-3.5 * t)
        samples.append(raw * env * 0.8)
    _write_wav(path, samples)


def generate_hit_sound(path):
    """Short metallic impact sound."""
    duration = 0.08
    total_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(total_samples):
        t = i / total_samples
        phase = 2.0 * math.pi * (350.0 * (1.0 - t * 0.5)) * (i / SAMPLE_RATE)
        noise = random.uniform(-0.5, 0.5)
        raw = 0.5 * math.sin(phase) + 0.5 * noise
        env = math.exp(-12.0 * t)
        samples.append(raw * env * 0.6)
    _write_wav(path, samples)


class AudioManager:
    """Handles sound loading, caching, and playback with fallback."""

    def __init__(self, asset_dir=None):
        if asset_dir is None:
            base = os.path.dirname(os.path.abspath(__file__))
            self.asset_dir = os.path.join(base, "assets", "sounds")
        else:
            self.asset_dir = asset_dir

        self.sounds = {}
        self.enabled = True
        self._ensure_sounds_generated()
        self._load_sounds()

    def _ensure_sounds_generated(self):
        os.makedirs(self.asset_dir, exist_ok=True)
        generators = {
            "laser.wav": generate_laser_sound,
            "explosion.wav": generate_explosion_sound,
            "pickup.wav": generate_pickup_sound,
            "shield.wav": generate_shield_sound,
            "bomb.wav": generate_bomb_sound,
            "hit.wav": generate_hit_sound
        }
        for filename, gen_func in generators.items():
            path = os.path.join(self.asset_dir, filename)
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                try:
                    gen_func(path)
                except Exception as e:
                    print(f"[AudioManager] Failed to generate {filename}: {e}")

    def _load_sounds(self):
        try:
            from kivy.core.audio import SoundLoader
            for sname in ["laser", "explosion", "pickup", "shield", "bomb", "hit"]:
                filepath = os.path.join(self.asset_dir, f"{sname}.wav")
                if os.path.exists(filepath):
                    sound = SoundLoader.load(filepath)
                    if sound:
                        sound.volume = 0.75
                        self.sounds[sname] = sound
        except Exception as e:
            print(f"[AudioManager] Audio backend initialization notice: {e}")

    def play(self, sound_name):
        """Play a sound effect if audio is enabled."""
        if not self.enabled:
            return
        snd = self.sounds.get(sound_name)
        if snd:
            try:
                if snd.state == "play":
                    snd.stop()
                snd.play()
            except Exception:
                pass


# Global singleton
audio_manager = AudioManager()

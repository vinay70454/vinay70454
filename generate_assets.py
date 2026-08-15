"""Utility to generate app icons and pre-warm audio assets.
"""

import os
import struct
import zlib
from audio_synth import AudioManager


def create_simple_png(filename, width=128, height=128):
    """Generate a clean RGBA PNG file without external image libraries."""
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

    # RGBA raw pixel data
    raw_data = bytearray()
    center_x, center_y = width / 2, height / 2

    for y in range(height):
        raw_data.append(0)  # Filter byte for PNG scanline (0 = None)
        for x in range(width):
            dx = x - center_x
            dy = y - center_y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < width * 0.45:
                # Ship / Sci-fi shield theme
                if abs(dx) < 8 and dy < 15:  # Laser fuselage
                    r, g, b, a = 255, 255, 255, 255
                elif dist < width * 0.28:     # Core
                    r, g, b, a = 40, 200, 255, 255
                else:                         # Outer rim
                    r, g, b, a = 20, 80, 180, 230
            else:
                r, g, b, a = 0, 0, 0, 0  # Transparent background

            raw_data.extend([r, g, b, a])

    def chunk(tag, data):
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        return length + tag + data + crc

    png_header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    idat = chunk(b"IDAT", zlib.compress(raw_data, 9))
    iend = chunk(b"IEND", b"")

    with open(filename, "wb") as f:
        f.write(png_header + ihdr + idat + iend)


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base, "assets", "icon.png")
    create_simple_png(icon_path, 128, 128)
    print(f"Generated icon: {icon_path}")

    # Generate sounds
    am = AudioManager(os.path.join(base, "assets", "sounds"))
    print("Audio assets pre-warmed.")

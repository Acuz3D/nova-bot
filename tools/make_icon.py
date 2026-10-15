"""Draws the Nova Bot icon (a white four-point spark on a dark rounded square)
and saves it as app/icon.ico and app/icon.png, using only the standard library."""
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "..", "app")
BG = (10, 10, 11)
FG = (243, 243, 244)
SS = 4  # samples per pixel side, for smooth edges


def inside_square(x, y, r=0.22):
    # Rounded square covering the whole canvas, x/y in [0, 1].
    dx = max(abs(x - 0.5) - (0.5 - r), 0)
    dy = max(abs(y - 0.5) - (0.5 - r), 0)
    return dx * dx + dy * dy <= r * r


def inside_spark(x, y, size=0.36):
    # |x|^0.5 + |y|^0.5 <= 1 is a four-point star with curved sides.
    u = abs(x - 0.5) / size
    v = abs(y - 0.5) / size
    return u ** 0.5 + v ** 0.5 <= 1


def draw(n):
    rows = []
    for py in range(n):
        row = bytearray([0])  # PNG filter byte
        for px in range(n):
            bg = fg = 0
            for sy in range(SS):
                for sx in range(SS):
                    x = (px + (sx + 0.5) / SS) / n
                    y = (py + (sy + 0.5) / SS) / n
                    if inside_square(x, y):
                        bg += 1
                        if inside_spark(x, y):
                            fg += 1
            total = SS * SS
            a = bg / total
            f = fg / bg if bg else 0
            rgb = [round(BG[i] + (FG[i] - BG[i]) * f) for i in range(3)]
            row += bytes(rgb + [round(a * 255)])
        rows.append(bytes(row))
    return b"".join(rows)


def png(n):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    header = struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(draw(n), 9)) + chunk(b"IEND", b"")


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [png(n) for n in sizes]
    offset = 6 + 16 * len(sizes)
    ico = struct.pack("<HHH", 0, 1, len(sizes))
    for n, data in zip(sizes, images):
        ico += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    ico += b"".join(images)
    with open(os.path.join(APP, "icon.ico"), "wb") as f:
        f.write(ico)
    with open(os.path.join(APP, "icon.png"), "wb") as f:
        f.write(images[-1])
    print("Saved app/icon.ico and app/icon.png")


if __name__ == "__main__":
    main()

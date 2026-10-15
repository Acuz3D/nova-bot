"""Makes Nova Bot's pictures from the artwork in art/ (needs Pillow: pip install pillow).

    app/nova-bot.ico, app/icon.png   the app icon (rounded square, face and wordmark)
    app/avatar.webp              Nova's picture next to its replies
    app/art-wide.webp            window background (wide)
    app/art-square.webp          window background (narrow windows)
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ART = os.path.join(ROOT, "art")
APP = os.path.join(ROOT, "app")
FACE_BOX = (247, 200, 1007, 960)  # the face and the full "Nova ✦ Bot" in the square art


def rounded(img, radius):
    mask = Image.new("L", (img.width * 4, img.height * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, mask.width - 1, mask.height - 1), radius * 4, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask.resize(img.size, Image.LANCZOS))
    return out


def main():
    square = Image.open(os.path.join(ART, "Nova Bot square.png")).convert("RGB")
    wide = Image.open(os.path.join(ART, "Nova Bot wide.png")).convert("RGB")
    wide.save(os.path.join(APP, "art-wide.webp"), quality=84, method=6)
    square.save(os.path.join(APP, "art-square.webp"), quality=84, method=6)

    face = square.crop(FACE_BOX)
    face.resize((256, 256), Image.LANCZOS).save(os.path.join(APP, "avatar.webp"), quality=88, method=6)

    icon = rounded(face.resize((256, 256), Image.LANCZOS), 56)
    icon.save(os.path.join(APP, "icon.png"))
    icon.save(os.path.join(APP, "nova-bot.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Saved icon, avatar and backgrounds in app/")


if __name__ == "__main__":
    main()

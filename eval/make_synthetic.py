"""Generate the synthetic text images in eval/images/ (the synthetic_*.png files).

    python eval/make_synthetic.py

These are rendered text, not photographs. They give a fixed, reproducible reading test,
including deliberately hard cases (small, blurred, tilted, low contrast). They say
nothing about hazards. Needs Pillow (pip install pillow), which the app itself does not use.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent / "images"
FONT = "arial.ttf"  # falls back to Pillow's built-in font if missing

# name, text, font size, text colour, background, blur radius, rotation in degrees
CASES = [
    ("exit_sign", "EXIT", 150, "white", (0, 110, 50), 0, 0),
    ("wet_floor", "CAUTION\nWET FLOOR", 90, "black", (255, 210, 0), 0, 0),
    ("platform", "Platform 2", 110, "white", (20, 40, 120), 0, 0),
    ("room_label", "Room 204\nComputer Lab", 70, "black", "white", 0, 0),
    ("medicine", "Paracetamol Tablets IP\n500 mg", 48, "black", (235, 235, 235), 0, 0),
    ("small_text", "Keep this door closed", 24, "black", "white", 0, 0),
    ("blurred", "PUSH TO OPEN", 80, "black", "white", 3, 0),
    ("tilted", "NO ENTRY", 100, "white", (180, 20, 20), 0, 18),
    ("low_contrast", "Staff Only", 90, (150, 150, 150), (185, 185, 185), 0, 0),
]


def font(size: int):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default(size)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text, size, colour, background, blur, rotation in CASES:
        image = Image.new("RGB", (800, 500), background)
        draw = ImageDraw.Draw(image)
        box = draw.multiline_textbbox((0, 0), text, font=font(size), align="center")
        position = ((800 - box[2] - box[0]) / 2, (500 - box[3] - box[1]) / 2)
        draw.multiline_text(position, text, font=font(size), fill=colour, align="center")
        if rotation:
            image = image.rotate(rotation, fillcolor=background, resample=Image.BICUBIC)
        if blur:
            image = image.filter(ImageFilter.GaussianBlur(blur))
        image.save(OUT / f"synthetic_{name}.png")
        print(f"synthetic_{name}.png,,{' '.join(text.split())}")


if __name__ == "__main__":
    main()

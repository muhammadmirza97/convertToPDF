r"""Generate the application icon.

Run this only when the icon design changes:

    .\.venv\Scripts\python.exe assets\make_icon.py

It writes assets/app_icon.ico for Windows shortcuts and assets/app_icon.png for the Tk
window icon on other platforms.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ASSETS = Path(__file__).resolve().parent
SIZE = 512
BACKGROUND = (31, 106, 165, 255)      # the CustomTkinter blue used by the app
PAGE = (250, 250, 252, 255)
ACCENT = (206, 61, 61, 255)
INK = (60, 66, 74, 255)

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _centred_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    x = box[0] + (box[2] - box[0] - (right - left)) / 2 - left
    y = box[1] + (box[3] - box[1] - (bottom - top)) / 2 - top
    draw.text((x, y), text, font=font, fill=fill)


def build_icon() -> Image.Image:
    """A rounded blue tile holding a document with a folded corner and a PDF label."""
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((16, 16, SIZE - 16, SIZE - 16), radius=96, fill=BACKGROUND)

    # Document body, with the top-right corner cut away for the fold.
    page_left, page_top, page_right, page_bottom = 132, 96, 380, 416
    fold = 84
    draw.polygon(
        [
            (page_left, page_top),
            (page_right - fold, page_top),
            (page_right, page_top + fold),
            (page_right, page_bottom),
            (page_left, page_bottom),
        ],
        fill=PAGE,
    )
    draw.polygon(
        [(page_right - fold, page_top), (page_right - fold, page_top + fold), (page_right, page_top + fold)],
        fill=(216, 222, 230, 255),
    )

    # Text lines on the page.
    for index, width in enumerate((150, 190, 170)):
        top = 168 + index * 34
        draw.rounded_rectangle((164, top, 164 + width, top + 14), radius=7, fill=INK)

    # PDF label across the lower half of the page.
    draw.rounded_rectangle((150, 300, 362, 388), radius=18, fill=ACCENT)
    _centred_text(draw, (150, 300, 362, 388), "PDF", _font(64), (255, 255, 255, 255))

    return image


def main() -> None:
    icon = build_icon()
    png_path = ASSETS / "app_icon.png"
    ico_path = ASSETS / "app_icon.ico"

    icon.save(png_path)
    icon.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Wrote {png_path}")
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()

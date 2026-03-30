from __future__ import annotations

import argparse

from PIL import Image, ImageDraw, ImageFont

ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", ".", " "]


def _font_cell_size() -> tuple[int, int]:
    """Pixel size of one monospace cell when rendering with the default font (must match render_ascii_to_image)."""
    font = ImageFont.load_default()
    sample = "".join(ASCII_CHARS) + "MW"
    char_w = 0
    char_h = 0
    for ch in sample:
        b = font.getbbox(ch)
        char_w = max(char_w, b[2] - b[0])
        char_h = max(char_h, b[3] - b[1])
    return max(6, char_w), max(10, char_h)


def convert_to_ascii_text(input_path: str, new_width: int = 100) -> list[str]:
    image = Image.open(input_path)

    # Preserve source aspect ratio in the *output image* (each char cell is char_w × char_h px):
    # (new_width * char_w) / (new_height * char_h) ≈ width / height
    # => new_height ≈ new_width * (height/width) * (char_w/char_h)
    width, height = image.size
    char_w, char_h = _font_cell_size()
    if width <= 0:
        new_height = max(1, new_width)
    else:
        new_height = max(1, int(round(new_width * (height / width) * (char_w / char_h))))

    resized_image = image.resize((new_width, new_height))

    # convert to grayscale
    greyified_image = resized_image.convert("L")
    pixels = list(greyified_image.get_flattened_data())

    # convert to ascii
    scale = 255 / (len(ASCII_CHARS) - 1)
    chars = [ASCII_CHARS[min(len(ASCII_CHARS) - 1, int(pixel / scale))] for pixel in pixels]

    # split string of chars into lines
    lines: list[str] = []
    for i in range(0, len(chars), new_width):
        lines.append("".join(chars[i : i + new_width]))
    return lines


def render_ascii_to_image(lines: list[str], output_path: str) -> None:
    font = ImageFont.load_default()
    char_w, char_h = _font_cell_size()
    # Fixed grid: one char per cell

    text_w = max((len(line) for line in lines), default=1)
    text_h = max(len(lines), 1)

    img_w = text_w * char_w
    img_h = text_h * char_h

    out = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(out)

    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            draw.text((x * char_w, y * char_h), ch, fill="black", font=font)

    out.save(output_path)


def convert_to_ascii_image(input_path: str, output_path: str, new_width: int = 100) -> None:
    lines = convert_to_ascii_text(input_path, new_width=new_width)
    render_ascii_to_image(lines, output_path=output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--width", type=int, default=100)
    args = parser.parse_args()

    convert_to_ascii_image(args.input, args.output, new_width=int(args.width))


if __name__ == "__main__":
    main()

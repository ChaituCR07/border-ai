"""Synthetic plate generator for ANPR regression fixtures and integration tests.

NOTICE: Synthetic fixtures are strictly for pipeline integration tests, regression
gating, and demonstrations. They are EXCLUDED from real-world accuracy claims per ADR 0040.
"""
import json
import os
import random
import struct
from typing import Dict, List, Tuple

# 5x7 bitmap font for alphanumeric characters A-Z, 0-9
FONT_5X7: Dict[str, List[int]] = {
    "A": [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "B": [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    "C": [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    "D": [0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C],
    "E": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    "F": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    "G": [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F],
    "H": [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "I": [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "J": [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    "K": [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    "L": [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    "M": [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    "N": [0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11],
    "O": [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "P": [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    "Q": [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    "R": [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    "S": [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    "T": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "U": [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "V": [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    "W": [0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A],
    "X": [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    "Y": [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    "Z": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
    "3": [0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    " ": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
}


def write_bmp(file_path: str, width: int, height: int, pixels: List[Tuple[int, int, int]]) -> None:
    """Writes a 24-bit uncompressed Windows BMP file."""
    row_padding = (4 - (width * 3) % 4) % 4
    image_size = (width * 3 + row_padding) * height
    file_size = 54 + image_size

    header = struct.pack(
        "<2sIHHI",
        b"BM",
        file_size,
        0,
        0,
        54,
    )
    dib_header = struct.pack(
        "<IIIHHIIIIII",
        40,
        width,
        height,
        1,
        24,
        0,
        image_size,
        2835,  # 72 DPI
        2835,
        0,
        0,
    )

    with open(file_path, "wb") as f:
        f.write(header)
        f.write(dib_header)
        # BMP stores pixels bottom-to-top
        for y in range(height - 1, -1, -1):
            row_bytes = bytearray()
            for x in range(width):
                r, g, b = pixels[y * width + x]
                # BMP color order is BGR
                row_bytes.extend([b, g, r])
            if row_padding:
                row_bytes.extend(b"\x00" * row_padding)
            f.write(row_bytes)


def render_plate_bitmap(
    text: str,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    fg_color: Tuple[int, int, int] = (15, 15, 15),
    scale: int = 4,
    noise_level: float = 0.0,
) -> Tuple[int, int, List[Tuple[int, int, int]]]:
    """Renders a license plate string onto a 24-bit RGB bitmap."""
    char_w = 5 * scale
    char_h = 7 * scale
    char_spacing = 2 * scale
    margin_x = 4 * scale
    margin_y = 3 * scale

    width = margin_x * 2 + len(text) * (char_w + char_spacing) - char_spacing
    height = margin_y * 2 + char_h

    # Initialize canvas with background color
    pixels = [bg_color] * (width * height)

    # Render each character
    cur_x = margin_x
    for ch in text.upper():
        glyph = FONT_5X7.get(ch, FONT_5X7[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if (bits >> (4 - col)) & 1:
                    # Fill scaled pixel block
                    for sy in range(scale):
                        for sx in range(scale):
                            px = cur_x + col * scale + sx
                            py = margin_y + row * scale + sy
                            if 0 <= px < width and 0 <= py < height:
                                pixels[py * width + px] = fg_color
        cur_x += char_w + char_spacing

    # Apply noise if specified
    if noise_level > 0.0:
        noisy_pixels = []
        for r, g, b in pixels:
            if random.random() < noise_level:
                delta = random.randint(-40, 40)
                nr = max(0, min(255, r + delta))
                ng = max(0, min(255, g + delta))
                nb = max(0, min(255, b + delta))
                noisy_pixels.append((nr, ng, nb))
            else:
                noisy_pixels.append((r, g, b))
        pixels = noisy_pixels

    return width, height, pixels


def generate_synthetic_plate_suite(out_dir: str, num_samples: int = 60, seed: int = 42) -> None:
    """Generates a committable set of synthetic plate crops and labels.json."""
    os.makedirs(out_dir, exist_ok=True)
    random.seed(seed)

    state_codes = ["KA", "MH", "DL", "TN", "AP", "TS", "GJ", "UP", "RJ", "KL"]
    letters = "ABCDEFGHJKLMNPRSTUVWXYZ"

    records = []

    for i in range(1, num_samples + 1):
        sample_id = f"synth_{i:03d}"
        file_name = f"{sample_id}.bmp"
        file_path = os.path.join(out_dir, file_name)

        # Generate realistic Indian plate strings
        is_bh = (i % 10 == 0)
        is_commercial = (i % 4 == 0)
        is_electric = (i % 15 == 0)

        if is_bh:
            year = random.randint(21, 26)
            num = random.randint(1000, 9999)
            suf = random.choice(letters) + random.choice(letters)
            plate_text = f"{year}BH{num}{suf}"
            plate_type = "bharat_series"
            bg_col = (255, 255, 255)
            fg_col = (10, 10, 10)
        elif is_commercial:
            st = random.choice(state_codes)
            rto = f"{random.randint(1, 99):02d}"
            ser = random.choice(letters)
            num = f"{random.randint(1000, 9999):04d}"
            plate_text = f"{st}{rto}{ser}{num}"
            plate_type = "commercial_yellow"
            bg_col = (250, 220, 30)  # Yellow
            fg_col = (15, 15, 15)
        elif is_electric:
            st = random.choice(state_codes)
            rto = f"{random.randint(1, 99):02d}"
            ser = random.choice(letters) + random.choice(letters)
            num = f"{random.randint(1000, 9999):04d}"
            plate_text = f"{st}{rto}{ser}{num}"
            plate_type = "ev_green"
            bg_col = (30, 130, 50)   # Green
            fg_col = (255, 255, 255)
        else:
            st = random.choice(state_codes)
            rto = f"{random.randint(1, 99):02d}"
            ser = random.choice(letters) + random.choice(letters)
            num = f"{random.randint(1000, 9999):04d}"
            plate_text = f"{st}{rto}{ser}{num}"
            plate_type = "private_white"
            bg_col = (255, 255, 255)
            fg_col = (15, 15, 15)

        # Condition and degradation
        condition = "clean"
        noise = 0.0
        if i % 5 == 0:
            condition = "mild_noise"
            noise = 0.08
        elif i % 7 == 0:
            condition = "sensor_noise"
            noise = 0.15

        scale = 4 if (i % 6 != 0) else 3  # slight resolution variation
        w, h, px = render_plate_bitmap(
            plate_text, bg_color=bg_col, fg_color=fg_col, scale=scale, noise_level=noise
        )
        write_bmp(file_path, w, h, px)

        records.append({
            "id": sample_id,
            "file_name": file_name,
            "plate_text": plate_text,
            "plate_norm": plate_text,
            "plate_type": plate_type,
            "condition": condition,
            "width": w,
            "height": h,
            "is_synthetic": True,
        })

    labels_path = os.path.join(out_dir, "labels.json")
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
        f.write("\n")

    print(f"Generated {num_samples} synthetic plate crops into {out_dir}")


if __name__ == "__main__":
    target_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "evaluation", "fixtures", "anpr_synth"
    )
    generate_synthetic_plate_suite(target_dir, num_samples=60)

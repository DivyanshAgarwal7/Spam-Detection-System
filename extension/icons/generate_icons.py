from PIL import Image, ImageDraw
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def make_icon(size, path):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    radius = size // 5
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=(124, 58, 237, 255))

    margin = size * 0.22
    env_top = size * 0.36
    env_bottom = size * 0.68
    env_left = margin
    env_right = size - margin
    width = max(1, size // 32)
    d.rectangle([env_left, env_top, env_right, env_bottom], outline=(255, 255, 255, 255), width=width)
    mid = ((env_left + env_right) / 2, (env_top + env_bottom) / 2)
    d.line([(env_left, env_top), mid], fill=(255, 255, 255, 255), width=width)
    d.line([(env_right, env_top), mid], fill=(255, 255, 255, 255), width=width)

    dot_r = size * 0.13
    dot_cx = size * 0.78
    dot_cy = size * 0.26
    d.ellipse(
        [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
        fill=(220, 38, 38, 255),
        outline=(255, 255, 255, 255),
        width=max(1, size // 48),
    )

    img.save(path)


if __name__ == "__main__":
    for size in (16, 32, 48, 128):
        make_icon(size, os.path.join(OUT_DIR, f"icon{size}.png"))
    print("icons generated")

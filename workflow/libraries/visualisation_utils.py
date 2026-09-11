import hashlib

def contrasting_text_color(image, value):
    rgba = image.cmap(image.norm(value))
    r, g, b = rgba[:3]

    # Relative perceived luminance of the cell background.
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

    return "black" if luminance > 0.5 else "white"

def deterministic_jitter(label, concept, width=0.5):
    digest = hashlib.sha256(f"{label}\0{concept}".encode("utf-8")).digest()
    unit_interval_value = int.from_bytes(digest[:8], byteorder="big")/(2**64 - 1)

    return (unit_interval_value - 0.5)*width
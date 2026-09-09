def contrasting_text_color(image, value):
    rgba = image.cmap(image.norm(value))
    r, g, b = rgba[:3]

    # Relative perceived luminance of the cell background.
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

    return "black" if luminance > 0.5 else "white"
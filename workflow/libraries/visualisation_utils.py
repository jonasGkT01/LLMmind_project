import hashlib

import matplotlib.pyplot as plt
import numpy as np

from libraries.manage_model_metadata import model_family

def significance_label(q_value):
    if q_value < 0.001:
        return "***"

    if q_value < 0.01:
        return "**"

    if q_value < 0.05:
        return "*"

    return ""

def contrasting_text_color(image, value):
    rgba = image.cmap(image.norm(value))
    r, g, b = rgba[:3]

    # Relative perceived luminance of the cell background.
    luminance = 0.2126*r + 0.7152*g + 0.0722*b

    return "black" if luminance > 0.5 else "white"

def deterministic_jitter(label, concept, width=0.5):
    digest = hashlib.sha256(f"{label}\0{concept}".encode("utf-8")).digest()
    unit_interval_value = int.from_bytes(digest[:8], byteorder="big")/(2**64 - 1)

    return (unit_interval_value - 0.5)*width

MODEL_TICK_ROTATION = 55
MODEL_FIGURE_HEIGHT = 7
MODEL_FIGURE_MIN_WIDTH = 10
MODEL_FIGURE_WIDTH_PER_MODEL = 0.75

def model_figure_width(number_of_models):
    return max(MODEL_FIGURE_MIN_WIDTH, MODEL_FIGURE_WIDTH_PER_MODEL*number_of_models,)

def style_model_x_axis(ax, labels,):
    positions = np.arange(len(labels))

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=MODEL_TICK_ROTATION, ha="right",)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.grid(axis="y", alpha=0.25)

    return positions

def add_model_family_annotations(ax, models,):
    start = 0

    while start < len(models):
        family = model_family(models[start])
        end = start + 1

        while (end < len(models) and model_family(models[end]) == family):
            end += 1

        if start > 0:
            ax.axvline(start - 0.5, linewidth=1, linestyle="--", alpha=0.6,)

        midpoint = (start + end - 1) / 2

        ax.text(midpoint, 1.015, family.replace("_", " "), transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontweight="bold",)

        start = end

def save_model_figure(fig, output_path,):
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.24, top=0.82,)
    fig.savefig(output_path, dpi=300, bbox_inches="tight",)
    plt.close(fig)

def mark_degenerate_boxplot_statistics(ax, boxplot_values, marker="D", color="red", markersize=5, zorder=4):
    """
    Draw a visible marker over any boxplot whose quartiles collapse onto each
    other (Q1 == Q3, or the median coincides with Q1 or Q3). Matplotlib renders
    such boxes as a flat, easy-to-miss line rather than raising a warning, so
    without this marker a real "no spread" result looks identical to missing
    data.
    """
    labelled = False

    for position, values in enumerate(boxplot_values):
        if len(values) == 0:
            continue

        q1 = np.quantile(values, 0.25)
        median = np.median(values)
        q3 = np.quantile(values, 0.75)

        if not (np.isclose(q1, q3) or np.isclose(median, q1) or np.isclose(median, q3)):
            continue

        ax.plot(
            position,
            median,
            marker=marker,
            color=color,
            markersize=markersize,
            zorder=zorder,
            linestyle="none",
            label="Degenerate box (zero-width quartile range)" if not labelled else None,
        )
        labelled = True
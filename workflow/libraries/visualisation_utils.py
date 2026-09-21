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

def log_boxplot_summary_statistics(labels, boxplot_values):
    for label, values in zip(labels, boxplot_values):
        q1 = np.quantile(values, 0.25)
        median = np.median(values)
        q3 = np.quantile(values, 0.75)

        print(f"{label}: "
              f"n={len(values)}, "
              f"unique={len(np.unique(values))}, "
              f"min={np.min(values):.9f}, "
              f"Q1={q1:.9f}, "
              f"median={median:.9f}, "
              f"Q3={q3:.9f}, "
              f"max={np.max(values):.9f}, "
              f"IQR={q3 - q1:.9f}")
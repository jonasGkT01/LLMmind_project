import colorsys
import hashlib

from matplotlib.lines import Line2D
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

# Asterisks for the uncorrected empirical p-value and for the Benjamini-Hochberg q-value.
P_VALUE_SIGNIFICANCE_COLOUR = "black"
Q_VALUE_SIGNIFICANCE_COLOUR = "red"
SIGNIFICANCE_ROW_OFFSET_POINTS = 10

def annotate_significance(ax, x_positions, y_positions, p_values, q_values):
    """
    Draw two rows of asterisks above each point: the uncorrected empirical
    p-value (lower row) and the Benjamini-Hochberg q-value (upper row). The
    rows keep fixed heights, so the q-value row does not shift when the
    p-value row is empty.
    """
    for x_position, y_position, p_value, q_value in zip(x_positions, y_positions, p_values, q_values):
        for row, (value, colour) in enumerate([(p_value, P_VALUE_SIGNIFICANCE_COLOUR), (q_value, Q_VALUE_SIGNIFICANCE_COLOUR),]):
            significance = significance_label(value)

            if significance:
                ax.annotate(significance, xy=(x_position, y_position,), xytext=(0, 4 + row*SIGNIFICANCE_ROW_OFFSET_POINTS), textcoords="offset points", ha="center", va="bottom", color=colour,)

def annotate_significance_band(ax, x_positions, p_values, q_values):
    """
    Concept-level plots: the model-level asterisks, in the same two rows,
    placed in a band along the top of the axes instead of above a point.
    """
    for x_position, p_value, q_value in zip(x_positions, p_values, q_values):
        for row, (value, colour) in enumerate([(p_value, P_VALUE_SIGNIFICANCE_COLOUR), (q_value, Q_VALUE_SIGNIFICANCE_COLOUR),]):
            significance = significance_label(value)

            if significance:
                ax.annotate(significance, xy=(x_position, 1.0,), xycoords=ax.get_xaxis_transform(), xytext=(0, -4 - (1 - row)*SIGNIFICANCE_ROW_OFFSET_POINTS), textcoords="offset points", ha="center", va="top", color=colour,)

def significance_legend_handles():
    return [
        Line2D([], [], linestyle="none", marker="$*$", markersize=8, color=P_VALUE_SIGNIFICANCE_COLOUR, label="Model-level empirical p-value (* <0.05, ** <0.01, *** <0.001)"),
        Line2D([], [], linestyle="none", marker="$*$", markersize=8, color=Q_VALUE_SIGNIFICANCE_COLOUR, label="Model-level Benjamini-Hochberg q-value (* <0.05, ** <0.01, *** <0.001)"),
    ]

# Titles and axis labels: every plot is titled "<level> <quantity>" with the
# analysis parameters on a second line, and every y-axis label is
# "<quantity>" or "<quantity> ± <error>".
MODEL_LEVEL = "Model-level"
CONCEPT_LEVEL = "Concept-level"
PAIRWISE_LEVEL = "Pairwise"

BRAIN_MODEL_ALIGNMENT_SCORE = "brain-model alignment score"
BRAIN_MODEL_ALIGNMENT_ENRICHMENT = "brain-model alignment enrichment"
BRAIN_MODEL_SPEARMAN_ALIGNMENT = "brain-model Spearman alignment"
PAIRWISE_ALIGNMENT_SCORE = "model-model and brain-model alignment score"
PAIRWISE_EMPIRICAL_P_VALUE = "model-model and brain-model alignment empirical p-value"

MODEL_AXIS_LABEL = "Model"
PAIRWISE_AXIS_LABEL = "Model / brain"

ALIGNMENT_SCORE_LABEL = "Alignment score"
MEAN_ALIGNMENT_SCORE_LABEL = "Mean alignment score"
ALIGNMENT_ENRICHMENT_LABEL = "Alignment enrichment (observed / expected)"
SPEARMAN_COEFFICIENT_LABEL = "Spearman's rank correlation coefficient"
EMPIRICAL_P_VALUE_LABEL = "-log10(empirical p-value)"

STANDARD_ERROR = "SE"
NULL_STANDARD_DEVIATION = "null SD"

def plot_title(level, quantity, dataset, similarity_type, number_of_neighbours=None):
    parameters = [f"dataset: {dataset}", f"similarity: {similarity_type}",]

    if number_of_neighbours is not None:
        parameters.append(f"neighbours: {number_of_neighbours}")

    return f"{level} {quantity}\n" + ", ".join(parameters)

def y_axis_label(quantity, error=None):
    if error is None:
        return quantity

    return f"{quantity} ± {error}"

CONCEPT_LEGEND_MAX_CONCEPTS = 20

def concept_colours(concepts):
    """
    One colour per concept, fixed by the sorted concept order, so a concept
    has the same colour for every model in a plot. Up to 20 concepts use the
    tab10/tab20 palettes; beyond that, hues are spaced by the golden ratio so
    that neighbouring concepts in the order still differ clearly.
    """
    concepts = sorted(set(concepts))

    if len(concepts) <= 10:
        palette = plt.get_cmap("tab10").colors

        return {concept: palette[i] for i, concept in enumerate(concepts)}

    if len(concepts) <= 20:
        palette = plt.get_cmap("tab20").colors

        return {concept: palette[i] for i, concept in enumerate(concepts)}

    golden_ratio_conjugate = (np.sqrt(5) - 1)/2

    return {
        concept: colorsys.hsv_to_rgb((i*golden_ratio_conjugate) % 1.0, 0.75, 0.85)
        for i, concept in enumerate(concepts)
    }

def concept_point_alpha(number_of_concepts):
    return 0.85 if number_of_concepts <= CONCEPT_LEGEND_MAX_CONCEPTS else 0.30

def concept_legend_handles(colour_by_concept):
    # only drawn when the concepts are few enough for a legend to be readable
    if len(colour_by_concept) > CONCEPT_LEGEND_MAX_CONCEPTS:
        return []

    return [
        Line2D([], [], linestyle="none", marker="o", markersize=6, color=colour, label=concept)
        for concept, colour in colour_by_concept.items()
    ]

def add_legend(ax, handles=None,):
    # the plot's own labelled artists come first; extra handles (e.g. concepts) go after them
    own_handles, _ = ax.get_legend_handles_labels()
    handles = own_handles + list(handles or [])

    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0.0, fontsize=8,)

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
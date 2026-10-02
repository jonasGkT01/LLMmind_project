# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import colorsys
import hashlib

from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import numpy as np

from libraries.manage_model_metadata import model_family

TITLE_PAD = 32
FIGURE_DPI = 300

def significance_label(q_value):
    if q_value < 0.001:
        return "***"

    if q_value < 0.01:
        return "**"

    if q_value < 0.05:
        return "*"

    return ""

# stimulus-type colour code: darkened Okabe-Ito vermillion and bluish green. The usual orange/green
# pair collapses under protanopia; this one stays apart for protan, deutan and tritan readers, and
# both reach >= 5:1 contrast on white, so they also work as text colours for the model names.
# Markers differ in shape too, and every label names the stimulus type, so colour is never the
# only cue
STIMULI_TYPE_COLOURS = {
    "language": "#A84800", 
    "vision": "#007A5A", 
}
STIMULI_TYPE_MARKERS = {
    "language": "o", 
    "vision": "s", 
}
# neutral ink for everything that is not a stimulus type: connecting lines, separators
NEUTRAL_COLOUR = "#595959"
# viridis is perceptually uniform and readable under every common colour-vision deficiency
SEQUENTIAL_COLOURMAP = "viridis"

# asterisks for the uncorrected empirical p-value and for the Benjamini-Hochberg q-value. Blue, not
# red: red and black look alike under protanopia. The two rows also differ in position
P_VALUE_SIGNIFICANCE_COLOUR = "black"
Q_VALUE_SIGNIFICANCE_COLOUR = "#0072B2"
SIGNIFICANCE_ROW_OFFSET_POINTS = 10

# extra distance between the x-axis and the model names, leaving room for the two asterisk rows
SIGNIFICANCE_TICK_LABEL_PAD_POINTS = 29

def annotate_significance(ax, x_positions, p_values, q_values):
    """
    Draw each model's model-level significance as two rows of asterisks just
    below the x-axis, above the model name: the uncorrected empirical p-value
    (upper row) and the Benjamini-Hochberg q-value (lower row). The rows keep
    fixed heights, so the q-value row does not shift when the p-value row is
    empty. Keeping them out of the axes leaves the plot area free for the
    legend.
    """
    ax.tick_params(axis = "x", pad = SIGNIFICANCE_TICK_LABEL_PAD_POINTS)

    for x_position, p_value, q_value in zip(x_positions, p_values, q_values):
        for row, (value, colour) in enumerate(
            [
                (p_value, P_VALUE_SIGNIFICANCE_COLOUR), 
                (q_value, Q_VALUE_SIGNIFICANCE_COLOUR)
            ]
        ):
            significance = significance_label(value)

            if significance:
                ax.annotate(
                    significance, 
                    xy = (x_position, 0.0,), 
                    xycoords = ax.get_xaxis_transform(), 
                    xytext = (0, -5 - row*SIGNIFICANCE_ROW_OFFSET_POINTS), 
                    textcoords = "offset points", 
                    ha = "center", 
                    va = "top", 
                    color = colour, 
                    annotation_clip = False
                )

def significance_legend_handles():
    return [
        Line2D(
            [], 
            [], 
            linestyle = "none", 
            marker = "$*$", 
            markersize = 8, 
            color = P_VALUE_SIGNIFICANCE_COLOUR, 
            label = "Model-level empirical p-value (* <0.05, ** <0.01, *** <0.001)"
        ), 
        Line2D(
            [], 
            [], 
            linestyle = "none", 
            marker = "$*$", 
            markersize = 8, 
            color = Q_VALUE_SIGNIFICANCE_COLOUR, 
            label = (
                "Model-level Benjamini-Hochberg q-value "
                "(* <0.05, ** <0.01, *** <0.001)"
            )
        ), 
    ]

# titles and axis labels: every plot is titled "<level> <quantity>" with the
# analysis parameters on a second line, and every y-axis label is
# "<quantity>" or "<quantity> ± <error>"
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

def plot_title(level, quantity, dataset, similarity_type, number_of_neighbours = None):
    parameters = [f"dataset: {dataset}", f"similarity: {similarity_type}",]

    if number_of_neighbours is not None:
        parameters.append(f"neighbours: {number_of_neighbours}")

    return f"{level} {quantity}\n" + ", ".join(parameters)

def y_axis_label(quantity, error = None):
    if error is None:
        return quantity

    return f"{quantity} ± {error}"

# above this many concepts the points are drawn more transparent, so overlapping points stay readable
DENSE_CONCEPT_THRESHOLD = 20

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
    return 0.85 if number_of_concepts <= DENSE_CONCEPT_THRESHOLD else 0.30

# fraction of the axes height kept empty above the data for the in-plot legend
LEGEND_HEADROOM_FRACTION = 0.25

def legend_headroom_top(bottom, data_top):
    """
    Upper y-limit that keeps the data in the lower part of the axes, leaving the top
    LEGEND_HEADROOM_FRACTION free for the legend, so dense concept points are never
    hidden behind it.
    """

    return bottom + (data_top - bottom)/(1.0 - LEGEND_HEADROOM_FRACTION)

def add_legend(ax, handles = None,):
    # the plot's own labelled artists come first; extra handles (e.g. significance) go after them.
    # The legend sits inside the axes, in the empty band that legend_headroom_top() leaves above the
    # data; concepts are only colour-coded, never listed
    own_handles, _ = ax.get_legend_handles_labels()
    handles = own_handles + list(handles or [])

    if handles:
        ax.legend(
            handles = handles, 
            loc = "upper left", 
            fontsize = 8, 
            framealpha = 0.9
        )

def contrasting_text_color(image, value):
    rgba = image.cmap(image.norm(value))
    r, g, b = rgba[:3]

    # relative perceived luminance of the cell background
    luminance = 0.2126*r + 0.7152*g + 0.0722*b

    return "black" if luminance > 0.5 else "white"

# concept points and boxes of the concept-level figures
CONCEPT_POINT_SIZE = 10
JITTER_WIDTH = 0.35
BOX_WIDTH = 0.55
BOXPLOT_LINE_STYLE = {"linewidth": 1.5}

def deterministic_jitter(label, concept):
    digest = hashlib.sha256(f"{label}\0{concept}".encode("utf-8")).digest()
    unit_interval_value = int.from_bytes(digest[:8], byteorder = "big")/(2**64 - 1)

    return (unit_interval_value - 0.5)*JITTER_WIDTH

def stimuli_type_colour(stimuli_type):
    return STIMULI_TYPE_COLOURS.get(stimuli_type, NEUTRAL_COLOUR)

def stimuli_type_legend_handles(stimuli_types):
    # colour swatches for plots whose model names, not marks, carry the stimulus-type colour
    return [
        Patch(
            color = stimuli_type_colour(stimuli_type), 
            label = f"{stimuli_type.capitalize()} stimuli (model name colour)"
        )
        for stimuli_type in sorted(set(stimuli_types))
    ]

def colour_tick_labels_by_stimuli_type(ax, stimuli_types, axes = "x",):
    """
    Colour each model name on the given axes ("x", "y" or "xy") by its stimulus type;
    the brain and anything else without a stimulus type stays black. Call after the tick
    labels are final, since set_xticks()/boxplot() rebuild them.
    """
    for axis_name in axes:
        axis = ax.xaxis if axis_name == "x" else ax.yaxis

        for tick_label, stimuli_type in zip(axis.get_ticklabels(), stimuli_types):
            tick_label.set_color(STIMULI_TYPE_COLOURS.get(stimuli_type, "black"))

def plot_model_points(ax, values, errors, stimuli_types,):
    # model-level values, with error bars unless errors is None: a neutral line joins the
    # models in axis order, and each point wears its stimulus type's colour and marker
    x = np.arange(len(values))
    values = np.asarray(values, dtype = float)
    errors = None if errors is None else np.asarray(errors, dtype = float)
    stimuli_types = np.asarray(stimuli_types)

    ax.plot(x, values, color = NEUTRAL_COLOUR, linewidth = 1.2, zorder = 1,)

    for stimuli_type in sorted(set(stimuli_types)):
        selected = stimuli_types == stimuli_type

        ax.errorbar(
            x[selected], 
            values[selected], 
            yerr = None if errors is None else errors[selected], 
            fmt = STIMULI_TYPE_MARKERS[stimuli_type], 
            color = stimuli_type_colour(stimuli_type), 
            markersize = 7, 
            capsize = 3, 
            zorder = 2, 
            label = f"{stimuli_type.capitalize()} stimuli", 
        )

# the reference expected under the null: a dashed line, and for each model an interval of
# one null SD around it
NULL_COLOUR = "grey"
NULL_LINE_STYLE = {"linestyle": "--", "linewidth": 1.2, "color": NULL_COLOUR}

def add_null_line(ax, y, label):
    ax.axhline(y, label = label, **NULL_LINE_STYLE)

def add_null_interval(ax, reference, null_standard_deviations):
    # the null distribution where it lives: reference ± that model's null SD at each model
    ax.errorbar(
        np.arange(len(null_standard_deviations)), 
        np.full(len(null_standard_deviations), reference), 
        yerr = null_standard_deviations, 
        fmt = "none", 
        ecolor = NULL_COLOUR, 
        elinewidth = 2, 
        capsize = 4, 
        zorder = 1, 
        label = "Null ± 1 SD", 
    )

def plot_concept_distributions(ax, labels, concept_df, value_column):
    # one jittered point per concept and a boxplot per model, at the position of its label;
    # concept_df has label, concept and value_column columns
    position_by_label = {label: position for position, label in enumerate(labels)}
    concepts = concept_df["concept"].astype(str)
    colour_by_concept = concept_colours(concepts)
    x_values = [
        position_by_label[label] + deterministic_jitter(label, concept)
        for label, concept in zip(concept_df["label"], concepts)
    ]
    values_by_label = concept_df.groupby("label")[value_column]
    boxplot_values = [
        values_by_label.get_group(label).to_numpy(dtype = float)
        for label in labels
    ]

    ax.scatter(
        x_values, 
        concept_df[value_column], 
        s = CONCEPT_POINT_SIZE, 
        c = concepts.map(colour_by_concept).tolist(), 
        alpha = concept_point_alpha(len(colour_by_concept)), 
        edgecolors = "none", 
        zorder = 2, 
    )
    ax.boxplot(
        boxplot_values, 
        positions = range(len(labels)), 
        widths = BOX_WIDTH, 
        showfliers = False, 
        boxprops = BOXPLOT_LINE_STYLE, 
        whiskerprops = BOXPLOT_LINE_STYLE, 
        capprops = BOXPLOT_LINE_STYLE, 
        medianprops = BOXPLOT_LINE_STYLE, 
        zorder = 3, 
    )
    mark_degenerate_boxplot_statistics(ax, boxplot_values)

def set_alignment_score_y_axis(ax):
    # alignment scores live in [0, 1]; the space above 1 is left free for the legend
    ax.set_ylim(0, legend_headroom_top(0, 1))
    ax.set_yticks(np.linspace(0, 1, 6))

MODEL_TICK_ROTATION = 55
MODEL_FIGURE_HEIGHT = 7
MODEL_FIGURE_MIN_WIDTH = 10
MODEL_FIGURE_WIDTH_PER_MODEL = 0.75

MODEL_FIGURE_MARGINS = {"bottom": 0.24, "top": 0.82}

def create_model_figure(number_of_models):
    width = max(MODEL_FIGURE_MIN_WIDTH, MODEL_FIGURE_WIDTH_PER_MODEL*number_of_models)

    return plt.subplots(figsize = (width, MODEL_FIGURE_HEIGHT))

def style_model_axes(
    ax, 
    models, 
    stimuli_types, 
    title, 
    y_label, 
    p_values, 
    q_values, 
    legend_handles, 
):
    # everything model figures share; call after boxplot(), which resets the ticks
    positions = np.arange(len(models))

    ax.set_xticks(positions)
    ax.set_xticklabels(models, rotation = MODEL_TICK_ROTATION, ha = "right")
    ax.set_xlim(-0.6, len(models) - 0.4)
    ax.grid(axis = "y", alpha = 0.25)
    colour_tick_labels_by_stimuli_type(ax, stimuli_types)
    add_model_family_annotations(ax, models)
    annotate_significance(ax, positions, p_values, q_values)

    ax.set_xlabel(MODEL_AXIS_LABEL)
    ax.set_ylabel(y_label)
    ax.set_title(title, pad = TITLE_PAD)
    add_legend(ax, legend_handles + significance_legend_handles())

def add_model_family_annotations(ax, models,):
    start = 0

    while start < len(models):
        family = model_family(models[start])
        end = start + 1

        while (end < len(models) and model_family(models[end]) == family):
            end += 1

        if start > 0:
            ax.axvline(
                start - 0.5, 
                linewidth = 1, 
                linestyle = "--", 
                color = NEUTRAL_COLOUR, 
                alpha = 0.6
            )

        midpoint = (start + end - 1)/2

        ax.text(
            midpoint, 
            1.015, 
            family.replace("_", " "), 
            transform = ax.get_xaxis_transform(), 
            ha = "center", 
            va = "bottom", 
            fontweight = "bold"
        )

        start = end

def save_figure(fig, output_path, model_figure = True):
    fig.tight_layout()

    if model_figure:
        fig.subplots_adjust(**MODEL_FIGURE_MARGINS)

    fig.savefig(output_path, dpi = FIGURE_DPI, bbox_inches = "tight")
    plt.close(fig)

def plot_pairwise_heatmap(
    ax, 
    matrix, 
    cell_text, 
    labels, 
    model_metadata, 
    colour_limits, 
    colourbar_label, 
):
    # a labels x labels heatmap with cell_text written in each finite cell; NaN cells stay blank
    image = ax.imshow(
        np.ma.masked_invalid(matrix), 
        vmin = colour_limits[0], 
        vmax = colour_limits[1], 
        cmap = SEQUENTIAL_COLOURMAP, 
    )

    for (i, j), value in np.ndenumerate(matrix):
        if np.isfinite(value):
            ax.text(
                j, 
                i, 
                cell_text[i][j], 
                ha = "center", 
                va = "center", 
                fontsize = 7, 
                color = contrasting_text_color(image, value), 
            )

    # model names only: the stimulus type is shown by the label colour
    tick_names = [
        label if label == "brain" else model_metadata[label]["model"]
        for label in labels
    ]
    stimuli_types = [
        None if label == "brain" else model_metadata[label]["stimuli_type"]
        for label in labels
    ]
    positions = np.arange(len(labels))

    ax.set_xticks(positions)
    ax.set_yticks(positions)
    ax.set_xticklabels(tick_names, rotation = 90)
    ax.set_yticklabels(tick_names)
    colour_tick_labels_by_stimuli_type(ax, stimuli_types, axes = "xy")
    ax.set_xlabel(PAIRWISE_AXIS_LABEL)
    ax.set_ylabel(PAIRWISE_AXIS_LABEL)

    # fraction/pad size the bar to the square heatmap, so it no longer rises into the title
    colorbar = ax.figure.colorbar(image, ax = ax, fraction = 0.046, pad = 0.04)
    colorbar.set_label(colourbar_label)

    # the bottom-left corner, under the row names, is the only area free of labels
    ax.figure.legend(
        handles = stimuli_type_legend_handles(
            [stimuli_type for stimuli_type in stimuli_types if stimuli_type is not None]
        ), 
        loc = "lower left", 
        fontsize = 8, 
        frameon = False, 
    )

def mark_degenerate_boxplot_statistics(ax, boxplot_values):
    """
    Draw a visible marker over any boxplot whose quartiles collapse onto each
    other (Q1 == Q3, or the median coincides with Q1 or Q3). Matplotlib renders
    such boxes as a flat, easy-to-miss line rather than raising a warning, so
    without this marker a real "no spread" result looks identical to missing
    data. Black with a white edge rather than red, which protanopes see as near-black.
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
            marker = "D", 
            color = "black", 
            markeredgecolor = "white", 
            markersize = 6, 
            zorder = 4, 
            linestyle = "none", 
            label = (
                "Degenerate box (zero-width quartile range)" if not labelled else None
            ), 
        )
        labelled = True

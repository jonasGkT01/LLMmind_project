#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-13, see docs/changelog/developers/ for details
import argparse

import numpy as np

from libraries.compute_statistics import benjamini_hochberg
from libraries.manage_model_metadata import parse_model_parameters, sort_models
from libraries.spearman_scores import (
    NULL_MEAN_COLUMN, 
    NULL_STANDARD_DEVIATION_COLUMN, 
    read_spearman_scores, 
)
from libraries.visualisation_utils import (
    add_null_line, 
    BRAIN_MODEL_SPEARMAN_ALIGNMENT, 
    CONCEPT_LEVEL, 
    create_model_figure, 
    legend_headroom_top, 
    MODEL_LEVEL, 
    plot_concept_distributions, 
    plot_model_points, 
    plot_null_distributions, 
    plot_title, 
    save_figure, 
    SPEARMAN_COEFFICIENT_LABEL, 
    SPEARMAN_NULL_LABEL, 
    stimuli_type_legend_handles, 
    style_model_axes, 
)

# symmetric y-limits: the largest |value| plus padding, rounded up to a step, at least the minimum
SPEARMAN_Y_PADDING = 0.10
SPEARMAN_Y_MINIMUM_LIMIT = 0.10
SPEARMAN_Y_STEP = 0.05

def spearman_ylim(values):
    max_abs = np.max(np.abs(np.asarray(values, dtype = float)))
    limit = max(SPEARMAN_Y_MINIMUM_LIMIT, max_abs*(1.0 + SPEARMAN_Y_PADDING))
    limit = min(1.0, np.ceil(limit/SPEARMAN_Y_STEP)*SPEARMAN_Y_STEP)

    # symmetric around 0, plus room above the data for the legend
    return -limit, legend_headroom_top(-limit, limit)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_level_spearman_scores", 
                        nargs = "+", 
                        required = True)
    parser.add_argument("--concept_level_spearman_scores", 
                        nargs = "+", 
                        required = True)
    parser.add_argument("--model_parameters", 
                        nargs = "+", 
                        required = True)
    parser.add_argument("--dataset", 
                        required = True)
    parser.add_argument("--similarity_type", 
                        required = True)
    parser.add_argument("--model_level_plot", 
                        required = True)
    parser.add_argument("--concept_level_plot", 
                        required = True)
    args = parser.parse_args()

    # load and validate the model- and concept-level Spearman coefficients
    model_df = read_spearman_scores(
        args.model_level_spearman_scores, 
        args.dataset, 
        model_level = True, 
    )
    concept_df = read_spearman_scores(
        args.concept_level_spearman_scores, 
        args.dataset, 
        model_level = False, 
    )

    for name, df in [("model-level", model_df), ("concept-level", concept_df),]:
        if set(df["similarity_type"]) != {args.similarity_type}:
            raise ValueError(
                f"{name} Spearman data contains an unexpected similarity type"
            )

    if set(model_df["label"]) != set(concept_df["label"]):
        raise ValueError(
            "Model-level and concept-level Spearman files contain different models"
        )

    # sort the models and correct the Spearman p-values of all models of this configuration
    model_df = sort_models(model_df, parse_model_parameters(args.model_parameters))
    labels = model_df["label"].tolist()
    models = model_df["model"].tolist()
    stimuli_types = model_df["stimuli_type"].tolist()
    p_values = model_df["empirical_upper_tail_p_value"].to_numpy(dtype = float)
    q_values = benjamini_hochberg(p_values)
    model_coefficients = model_df["observed_spearman_coefficient"].to_numpy(
        dtype = float
    )
    null_means = model_df[NULL_MEAN_COLUMN].to_numpy(dtype = float)
    null_standard_deviations = model_df[NULL_STANDARD_DEVIATION_COLUMN].to_numpy(
        dtype = float
    )

    # plot the model coefficients next to each model's relabelling null (mean ± SD)
    fig, ax = create_model_figure(len(labels))

    plot_null_distributions(ax, null_means, null_standard_deviations)
    plot_model_points(ax, model_coefficients, None, stimuli_types)
    add_null_line(ax, 0.0, SPEARMAN_NULL_LABEL)
    style_model_axes(
        ax, 
        models, 
        stimuli_types, 
        plot_title(
            MODEL_LEVEL, 
            BRAIN_MODEL_SPEARMAN_ALIGNMENT, 
            args.dataset, 
            args.similarity_type, 
        ), 
        SPEARMAN_COEFFICIENT_LABEL, 
        p_values, 
        q_values, 
        [], 
    )
    ax.set_ylim(
        *spearman_ylim(
            np.concatenate(
                [model_coefficients, np.abs(null_means) + null_standard_deviations]
            )
        )
    )

    save_figure(fig, args.model_level_plot)

    # plot the concept coefficients of each model against rho = 0
    fig, ax = create_model_figure(len(labels))

    plot_concept_distributions(ax, labels, concept_df, "observed_spearman_coefficient")
    add_null_line(ax, 0.0, SPEARMAN_NULL_LABEL)
    style_model_axes(
        ax, 
        models, 
        stimuli_types, 
        plot_title(
            CONCEPT_LEVEL, 
            BRAIN_MODEL_SPEARMAN_ALIGNMENT, 
            args.dataset, 
            args.similarity_type, 
        ), 
        SPEARMAN_COEFFICIENT_LABEL, 
        p_values, 
        q_values, 
        stimuli_type_legend_handles(stimuli_types), 
    )
    ax.set_ylim(*spearman_ylim(concept_df["observed_spearman_coefficient"]))

    save_figure(fig, args.concept_level_plot)

if __name__ == "__main__":
    main()

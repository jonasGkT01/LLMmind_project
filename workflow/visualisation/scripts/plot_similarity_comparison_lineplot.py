#!/usr/bin/env python3
# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details
import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from libraries.compute_alignment import (
    common_hypergeometric_expectation,
    summarise_alignment_scores,
)
from libraries.compute_alignment_enrichment import (
    compute_alignment_enrichment,
    enrichment_axis_position,
    enrichment_axis_value,
    set_enrichment_y_scale,
)
from libraries.manage_model_metadata import parse_model_parameters, sort_models
from libraries.path_metadata import (
    parse_alignment_path,
    relabelled_name_for_observed_path,
)
from libraries.spearman_scores import (
    NULL_STANDARD_DEVIATION_COLUMN,
    read_spearman_scores,
)
from libraries.visualisation_utils import (
    add_null_line,
    ALIGNMENT_ENRICHMENT_LABEL,
    BRAIN_MODEL_ALIGNMENT_ENRICHMENT,
    BRAIN_MODEL_ALIGNMENT_SCORE,
    BRAIN_MODEL_SPEARMAN_ALIGNMENT,
    create_model_figure,
    data_fitted_ylim,
    ENRICHMENT_NULL_LABEL,
    HYPERGEOMETRIC_NULL_LABEL,
    MEAN_ALIGNMENT_SCORE_LABEL,
    MODEL_LEVEL,
    NULL_STANDARD_DEVIATION,
    plot_similarity_type_points,
    plot_title,
    save_figure,
    SIMILARITY_TYPE_COLOURS,
    similarity_type_legend_handles,
    SPEARMAN_COEFFICIENT_LABEL,
    SPEARMAN_NULL_LABEL,
    STANDARD_ERROR,
    style_model_axes,
    y_axis_label,
)

def paths_by_similarity_type(paths):
    groups = defaultdict(list)

    for path in paths:
        groups[parse_alignment_path(path)["similarity_type"]].append(path)

    return groups

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantity",
                        required = True,
                        choices = ["alignment", "enrichment", "spearman"])
    parser.add_argument("--llm_brain_alignment_scores",
                        nargs = "+",
                        help = "LLM-brain alignment score parquet files of every similarity measure (alignment, enrichment)")
    parser.add_argument("--relabelled_llm_brain_alignment_scores",
                        nargs = "+",
                        help = "All-k relabelled LLM-brain common-neighbours parquet files, one per observed file (enrichment)")
    parser.add_argument("--model_level_spearman_scores",
                        nargs = "+",
                        help = "Model-level Spearman TSV files of every similarity measure (spearman)")
    parser.add_argument("--model_parameters",
                        nargs = "+",
                        required = True,
                        help = "Model parameter counts formatted as model=parameters_millions")
    parser.add_argument("--dataset",
                        required = True)
    parser.add_argument("--number_of_neighbours",
                        type = int,
                        help = "Number of neighbours (alignment, enrichment)")
    parser.add_argument("--plot",
                        required = True)
    args = parser.parse_args()

    # one dataframe per similarity measure with label, model, stimuli_type, value and error
    model_dfs = {}

    if args.quantity == "alignment":
        expectations = []

        for similarity_type, paths in paths_by_similarity_type(
            args.llm_brain_alignment_scores
        ).items():
            model_df, expectation = summarise_alignment_scores(
                paths,
                args.dataset,
                similarity_type,
                args.number_of_neighbours,
            )
            model_dfs[similarity_type] = model_df.rename(
                columns = {"mean": "value", "standard_error": "error"}
            )
            expectations.append(expectation)

        null_value = common_hypergeometric_expectation(expectations)
        null_label = HYPERGEOMETRIC_NULL_LABEL
        quantity = BRAIN_MODEL_ALIGNMENT_SCORE
        y_label = y_axis_label(MEAN_ALIGNMENT_SCORE_LABEL, STANDARD_ERROR)
    elif args.quantity == "enrichment":
        for similarity_type, paths in paths_by_similarity_type(
            args.llm_brain_alignment_scores
        ).items():
            relabelled_names = {
                relabelled_name_for_observed_path(path, args.number_of_neighbours)
                for path in paths
            }
            _, model_df = compute_alignment_enrichment(
                observed_paths = paths,
                relabelled_paths = [
                    path
                    for path in args.relabelled_llm_brain_alignment_scores
                    if Path(path).name in relabelled_names
                ],
                expected_dataset = args.dataset,
                expected_similarity_type = similarity_type,
                expected_number_of_neighbours = args.number_of_neighbours,
            )
            model_dfs[similarity_type] = model_df.rename(
                columns = {"enrichment": "value", "null_standard_deviation": "error"}
            )

        null_value = 1.0
        null_label = ENRICHMENT_NULL_LABEL
        quantity = BRAIN_MODEL_ALIGNMENT_ENRICHMENT
        y_label = y_axis_label(ALIGNMENT_ENRICHMENT_LABEL, NULL_STANDARD_DEVIATION)
    else:
        spearman_df = read_spearman_scores(
            args.model_level_spearman_scores,
            args.dataset,
            model_level = True,
        ).rename(
            columns = {
                "observed_spearman_coefficient": "value",
                NULL_STANDARD_DEVIATION_COLUMN: "error",
            }
        )
        model_dfs = {
            similarity_type: model_df
            for similarity_type, model_df in spearman_df.groupby("similarity_type")
        }
        null_value = 0.0
        null_label = SPEARMAN_NULL_LABEL
        quantity = BRAIN_MODEL_SPEARMAN_ALIGNMENT
        y_label = y_axis_label(SPEARMAN_COEFFICIENT_LABEL, NULL_STANDARD_DEVIATION)

    # every measure must cover the same models; sort them once, in the usual order
    similarity_types = [
        similarity_type
        for similarity_type in SIMILARITY_TYPE_COLOURS
        if similarity_type in model_dfs
    ]
    first_df = model_dfs[similarity_types[0]]

    for similarity_type in similarity_types:
        if set(model_dfs[similarity_type]["label"]) != set(first_df["label"]):
            raise ValueError(
                f"The {similarity_type} and {similarity_types[0]} files contain "
                "different models"
            )

    sorted_df = sort_models(first_df, parse_model_parameters(args.model_parameters))
    labels = sorted_df["label"].tolist()
    stimuli_types = sorted_df["stimuli_type"].tolist()

    # plot one series per measure against the null
    fig, ax = create_model_figure(len(labels))
    error_bar_ends = [null_value]

    for similarity_type in similarity_types:
        model_df = model_dfs[similarity_type].set_index("label").loc[labels]
        values = model_df["value"].to_numpy(dtype = float)
        errors = model_df["error"].to_numpy(dtype = float)

        plot_similarity_type_points(ax, values, errors, stimuli_types, similarity_type)
        error_bar_ends.extend(values - errors)
        error_bar_ends.extend(values + errors)

    add_null_line(ax, null_value, null_label)
    style_model_axes(
        ax,
        sorted_df["model"].tolist(),
        stimuli_types,
        plot_title(
            MODEL_LEVEL,
            quantity,
            args.dataset,
            number_of_neighbours = args.number_of_neighbours,
        ),
        y_label,
        None,
        None,
        similarity_type_legend_handles(similarity_types, stimuli_types),
    )

    # y-limits fitted to the error bars and the null line; the enrichment limits are
    # fitted on the symlog axis positions and start at 0 at the lowest
    if args.quantity == "enrichment":
        set_enrichment_y_scale(ax)
        bottom, top = data_fitted_ylim(
            [enrichment_axis_position(max(value, 0.0)) for value in error_bar_ends],
            minimum = 0.0,
        )
        ax.set_ylim(enrichment_axis_value(bottom), enrichment_axis_value(top))
    else:
        ax.set_ylim(*data_fitted_ylim(error_bar_ends))

    save_figure(fig, args.plot)

if __name__ == "__main__":
    main()

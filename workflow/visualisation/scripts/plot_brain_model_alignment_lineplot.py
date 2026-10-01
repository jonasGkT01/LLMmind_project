#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-01, see docs/changelog/developers/ for details
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from libraries.compute_statistics import benjamini_hochberg, read_model_level_empirical_p_values
from libraries.manage_model_metadata import model_key, model_sort_key, parse_model_parameters
from libraries.path_metadata import parse_llm_brain_alignment_score_path
from libraries.visualisation_utils import (
    add_legend,
    add_model_family_annotations,
    legend_headroom_top,
    annotate_significance,
    BRAIN_MODEL_ALIGNMENT_SCORE,
    colour_tick_labels_by_stimuli_type,
    MEAN_ALIGNMENT_SCORE_LABEL,
    MODEL_AXIS_LABEL,
    MODEL_LEVEL,
    plot_model_points,
    plot_title,
    significance_legend_handles,
    STANDARD_ERROR,
    y_axis_label,
)

def read_alignment_score_summary(path, number_of_neighbours):
    df = pd.read_parquet(
        path,
        engine="pyarrow",
    )

    if "alignment_score" not in df.columns:
        raise ValueError(f"{path} does not contain an 'alignment_score' column")

    alignment_scores = pd.to_numeric(df["alignment_score"], errors="coerce",)

    if alignment_scores.isna().any():
        raise ValueError(f"{path} contains non-numeric alignment scores")

    if ((alignment_scores < 0) | (alignment_scores > 1)).any():
        raise ValueError(f"{path} contains alignment scores outside [0, 1]")

    number_of_concepts = len(alignment_scores)

    if number_of_concepts < 2:
        raise ValueError(f"{path} contains fewer than two concepts")

    population_size = number_of_concepts - 1

    if number_of_neighbours > population_size:
        raise ValueError(f"{path} uses {number_of_neighbours} neighbours, but only {number_of_concepts} concepts are available")

    # every concept has the same hypergeometric expectation, so it is also the expected mean
    expected_alignment_score = number_of_neighbours/population_size

    mean_alignment_score = float(alignment_scores.mean())

    standard_error = float(alignment_scores.std(ddof = 1)/np.sqrt(number_of_concepts))

    return mean_alignment_score, standard_error, expected_alignment_score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", nargs="+", required=True, help="LLM-brain alignment score parquet files")
    parser.add_argument("--model_level_statistics", required=True, help="TSV file containing model-level statistics")
    parser.add_argument("--model_parameters", nargs="+", required=True, help="Model parameter counts formatted as model=parameters_millions")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--plot", required=True)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)
    alignment_scores = {}
    model_metadata = {}
    expected_alignment_scores = set()

    for path in args.llm_brain_alignment_scores:
        metadata = parse_llm_brain_alignment_score_path(path)

        if metadata["dataset"] != args.dataset:
            raise ValueError(f"{path} belongs to dataset {metadata['dataset']}, expected {args.dataset}")

        if metadata["similarity_type"] != args.similarity_type:
            raise ValueError(f"{path} uses similarity type {metadata['similarity_type']}, expected {args.similarity_type}")

        model = metadata["model"]
        number_of_neighbours = metadata["number_of_neighbours"]

        if number_of_neighbours != args.number_of_neighbours:
            raise ValueError(f"{path} uses k={number_of_neighbours}, expected k={args.number_of_neighbours}")

        if model not in parameters_by_model:
            raise ValueError(f"No number of parameters was provided for model {model}")

        label = model_key(model, metadata["stimuli_type"])

        if label in alignment_scores:
            raise ValueError(f"More than one alignment score was found for {label} and k={number_of_neighbours}")

        mean_alignment_score, standard_error, expected_alignment_score = read_alignment_score_summary(path, number_of_neighbours)
        alignment_scores[label] = {
            "mean": mean_alignment_score,
            "standard_error": standard_error,
        }

        model_metadata[label] = {
            "model": model,
            "stimuli_type": metadata["stimuli_type"],
        }
        expected_alignment_scores.add(expected_alignment_score)

    if not alignment_scores:
        raise ValueError("No alignment score files were provided")

    if len(expected_alignment_scores) > 1:
        raise ValueError(f"Inconsistent hypergeometric expected alignment scores across input files: {sorted(expected_alignment_scores)}")

    expected_alignment_score = expected_alignment_scores.pop()

    labels = sorted(
        model_metadata,
        key = lambda label: model_sort_key(
            model = model_metadata[label]["model"],
            stimuli_type = model_metadata[label]["stimuli_type"],
            parameters_by_model = parameters_by_model,
        ),
    )
    models = [model_metadata[label]["model"] for label in labels]
    stimuli_types = [model_metadata[label]["stimuli_type"] for label in labels]

    p_value_by_model = read_model_level_empirical_p_values(
        path=args.model_level_statistics,
        dataset=args.dataset,
        similarity_type=args.similarity_type,
        number_of_neighbours=args.number_of_neighbours,
    )

    missing_p_values = set(labels) - set(p_value_by_model)

    if missing_p_values:
        raise ValueError(f"Missing model-level empirical p-values for models: {sorted(missing_p_values)}")

    p_values = np.asarray([p_value_by_model[label] for label in labels], dtype=float,)
    q_values = benjamini_hochberg(p_values)

    x = list(range(len(labels)))
    output_path = Path(args.plot)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(10, 0.75 * len(labels))
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    values = [alignment_scores[label]["mean"] for label in labels]
    errors = [alignment_scores[label]["standard_error"] for label in labels]

    plot_model_points(ax, x, values, errors, stimuli_types)
    ax.axhline(expected_alignment_score, linestyle="--", linewidth=1.2, color="grey", label="Null expectation (hypergeometric)",)

    annotate_significance(ax, x, p_values, q_values)
    add_model_family_annotations(ax, models)

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation = 55, ha = "right")
    colour_tick_labels_by_stimuli_type(ax, stimuli_types)
    ax.set_xlabel(MODEL_AXIS_LABEL)
    ax.set_ylabel(y_axis_label(MEAN_ALIGNMENT_SCORE_LABEL, STANDARD_ERROR))
    ax.set_title(plot_title(MODEL_LEVEL, BRAIN_MODEL_ALIGNMENT_SCORE, args.dataset, args.similarity_type, args.number_of_neighbours), pad=32)
    # alignment scores live in [0, 1]; the space above 1 is left free for the legend
    ax.set_ylim(0, legend_headroom_top(0, 1))
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.grid(axis="y", alpha=0.25)
    add_legend(ax, significance_legend_handles())

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.24, top=0.82)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from libraries.compute_statistics import benjamini_hochberg
from libraries.manage_model_metadata import model_family, model_sort_key, parse_model_parameters
from libraries.path_metadata import parse_llm_brain_alignment_score_path
from libraries.visualisation_utils import (
    add_legend,
    legend_headroom_top,
    annotate_significance,
    BRAIN_MODEL_ALIGNMENT_SCORE,
    MEAN_ALIGNMENT_SCORE_LABEL,
    MODEL_AXIS_LABEL,
    MODEL_LEVEL,
    plot_title,
    significance_legend_handles,
    STANDARD_ERROR,
    y_axis_label,
)

def read_alignment_score_summary(path):
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

    mean_alignment_score = float(alignment_scores.mean())

    standard_error = float(alignment_scores.std(ddof = 1)/np.sqrt(number_of_concepts))

    return mean_alignment_score, standard_error

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
    statistics_df = pd.read_csv(
        args.model_level_statistics,
        sep="\t",
    )

    required_statistic_columns = {"dataset", "stimuli_type", "similarity_type", "number_of_neighbours", "model", "statistic", "value",}

    missing_statistic_columns = required_statistic_columns - set(statistics_df.columns)

    if missing_statistic_columns:
        raise ValueError(f"Model-level statistics file is missing columns: {sorted(missing_statistic_columns)}")

    statistics_df["number_of_neighbours"] = pd.to_numeric(statistics_df["number_of_neighbours"], errors="raise",).astype(int)
    selected_statistics = statistics_df[
        (statistics_df["dataset"].astype(str) == args.dataset)
        & (statistics_df["similarity_type"].astype(str) == args.similarity_type)
        & (statistics_df["number_of_neighbours"] == args.number_of_neighbours)
        & (statistics_df["statistic"].astype(str) == "model_level_empirical_p_value")
    ].copy()

    if selected_statistics.empty:
        raise ValueError(f"No model-level empirical p-values were found for dataset={args.dataset}, similarity_type={args.similarity_type}, number_of_neighbours={args.number_of_neighbours}")

    selected_statistics["value"] = pd.to_numeric(selected_statistics["value"], errors="raise",)

    invalid_p_values = ((selected_statistics["value"] <= 0) | (selected_statistics["value"] > 1))

    if invalid_p_values.any():
        raise ValueError("Model-level statistics contain invalid empirical p-values")

    if selected_statistics["model"].duplicated().any():
        duplicated_models = selected_statistics.loc[selected_statistics["model"].duplicated(keep=False), "model",].unique()

        raise ValueError(f"More than one model-level empirical p-value was found for: {sorted(duplicated_models)}")

    alignment_scores = {}
    available_models = set()

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

        key = (model, number_of_neighbours)

        if key in alignment_scores:
            raise ValueError(f"More than one alignment score was found for model {model} and k={number_of_neighbours}")

        mean_alignment_score, standard_error = read_alignment_score_summary(path)
        alignment_scores[key] = {
            "mean": mean_alignment_score,
            "standard_error": standard_error,
        }

        available_models.add(model)

    if not alignment_scores:
        raise ValueError("No alignment score files were provided")

    models = sorted(
        available_models,
        key=lambda model: model_sort_key(
            model=model,
            parameters_by_model=parameters_by_model,
        ),
    )

    p_value_by_model = dict(zip(selected_statistics["model"].astype(str), selected_statistics["value"],))

    missing_p_values = set(models) - set(p_value_by_model)

    if missing_p_values:
        raise ValueError(f"Missing model-level empirical p-values for models: {sorted(missing_p_values)}")

    p_values = np.asarray(
        [
            p_value_by_model[model]
            for model in models
        ], dtype=float,)

    q_values = benjamini_hochberg(p_values)

    family_ranges = []
    start = 0

    while start < len(models):
        family = model_family(models[start])
        end = start + 1

        while end < len(models) and model_family(models[end]) == family:
            end += 1

        family_ranges.append((family, start, end))
        start = end

    x = list(range(len(models)))
    output_path = Path(args.plot)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(10, 0.75 * len(models))
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    values = [
        alignment_scores[(model, args.number_of_neighbours)]["mean"]
        for model in models
    ]
    errors = [
        alignment_scores[(model, args.number_of_neighbours)]["standard_error"]
        for model in models
    ]

    ax.errorbar(x, values, yerr=errors, marker="o", linewidth=1.8, capsize=3,)

    annotate_significance(ax, x, p_values, q_values)

    for family, start, end in family_ranges:
        if start > 0:
            ax.axvline(start - 0.5, linewidth=1, linestyle="--", alpha=0.6)

        midpoint = (start + end - 1) / 2
        ax.text(midpoint, 1.015, family.replace("_", " "), transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontweight="bold")

    model_labels = [
        f"{model}"
        for model in models
    ]

    ax.set_xticks(x)
    ax.set_xticklabels(model_labels, rotation=55, ha="right")
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
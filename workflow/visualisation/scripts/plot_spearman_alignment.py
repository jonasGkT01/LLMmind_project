#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from libraries.compute_statistics import benjamini_hochberg
from libraries.manage_model_metadata import model_family, model_sort_key, parse_model_parameters
from libraries.validate_data import validate_required_columns
from libraries.visualisation_utils import (
    add_legend,
    legend_headroom_top,
    add_model_family_annotations,
    annotate_significance,
    BRAIN_MODEL_SPEARMAN_ALIGNMENT,
    concept_colours,
    CONCEPT_LEVEL,
    concept_point_alpha,
    deterministic_jitter,
    mark_degenerate_boxplot_statistics,
    MODEL_AXIS_LABEL,
    MODEL_LEVEL,
    NULL_STANDARD_DEVIATION,
    plot_title,
    significance_legend_handles,
    SPEARMAN_COEFFICIENT_LABEL,
    y_axis_label,
)

NULL_STANDARD_DEVIATION_COLUMN = "empirical_null_standard_deviation_spearman_coefficient"

def spearman_ylim(values, padding=0.10, minimum_limit=0.10, step=0.05):
    values = np.asarray(values, dtype=float)

    max_abs = np.max(np.abs(values))
    limit = max(minimum_limit, max_abs * (1.0 + padding))
    limit = np.ceil(limit / step) * step
    limit = min(1.0, limit)

    # symmetric around 0, plus room above the data for the legend
    return -limit, legend_headroom_top(-limit, limit)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_level_spearman_scores", nargs="+", required=True)
    parser.add_argument("--concept_level_spearman_scores", nargs="+", required=True)
    parser.add_argument("--model_parameters", nargs="+", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--model_level_plot", required=True)
    parser.add_argument("--concept_level_plot", required=True)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)
    model_df = pd.concat(
        [
            pd.read_csv(path, sep="\t")
            for path in args.model_level_spearman_scores
        ],
        ignore_index=True,
    )
    concept_df = pd.concat(
        [
            pd.read_csv(path, sep="\t")
            for path in args.concept_level_spearman_scores
        ],
        ignore_index=True,
    )

    for name, df in [("model-level", model_df), ("concept-level", concept_df),]:
        required_columns = {
            "dataset",
            "model",
            "stimuli_type",
            "similarity_type",
            "observed_spearman_coefficient",
            NULL_STANDARD_DEVIATION_COLUMN,
        }

        if name == "concept-level":
            required_columns.add("concept")

        if name == "model-level":
            required_columns.add("empirical_upper_tail_p_value")

        validate_required_columns(df=df, required_columns=required_columns, source=f"{name} Spearman data",)

        if name == "model-level":
            p_values = pd.to_numeric(df["empirical_upper_tail_p_value"], errors="coerce",)

            if (p_values.isna().any() or (p_values <= 0).any() or (p_values > 1).any()):
                raise ValueError("Model-level Spearman data contains invalid empirical p-values")

            df["empirical_upper_tail_p_value"] = p_values

        if set(df["dataset"]) != {args.dataset}:
            raise ValueError(f"{name} Spearman data contains an unexpected dataset")

        if set(df["similarity_type"]) != {args.similarity_type}:
            raise ValueError(f"{name} Spearman data contains an unexpected similarity type")

        coefficients = pd.to_numeric(df["observed_spearman_coefficient"], errors="coerce",)

        if coefficients.isna().any() or ((coefficients < -1) | (coefficients > 1)).any():
            raise ValueError(f"{name} Spearman data contains invalid coefficients")

        df["observed_spearman_coefficient"] = coefficients

        null_standard_deviations = pd.to_numeric(df[NULL_STANDARD_DEVIATION_COLUMN], errors="coerce",)

        if null_standard_deviations.isna().any() or (null_standard_deviations < 0).any():
            raise ValueError(f"{name} Spearman data contains invalid null standard deviations")

        df[NULL_STANDARD_DEVIATION_COLUMN] = null_standard_deviations
        df["label"] = df["model"].astype(str)

    if model_df["label"].duplicated().any():
        raise ValueError("More than one model-level Spearman coefficient was provided for the same model/stimuli type")

    if set(model_df["label"]) != set(concept_df["label"]):
        raise ValueError("Model-level and concept-level Spearman files contain different models")

    missing_parameters = set(model_df["model"]) - set(parameters_by_model)

    if missing_parameters:
        raise ValueError(f"No number of parameters was provided for models: {sorted(missing_parameters)}")

    model_df = model_df.sort_values(
        "label",
        key=lambda labels: labels.map(
            {
                row.label: model_sort_key(
                    model=row.model,
                    parameters_by_model=parameters_by_model,
                )
                for row in model_df.itertuples(index=False)
            }
        ),
    ).reset_index(drop=True)

    model_df["q_value"] = benjamini_hochberg(model_df["empirical_upper_tail_p_value"].to_numpy(dtype=float))

    labels = model_df["label"].tolist()
    x_positions = {
        label: position
        for position, label in enumerate(labels)
    }
    x = np.arange(len(labels))

    model_level_path = Path(args.model_level_plot)
    model_level_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(10, 0.75*len(labels))
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    model_coefficients = model_df["observed_spearman_coefficient"].to_numpy(dtype=float)
    model_errors = model_df[NULL_STANDARD_DEVIATION_COLUMN].to_numpy(dtype=float)

    ax.errorbar(x, model_coefficients, yerr=model_errors, marker="o", linewidth=1.8, capsize=3,)

    annotate_significance(ax, x, model_df["empirical_upper_tail_p_value"], model_df["q_value"])

    ax.axhline(0.0, linestyle="--", linewidth=1.2, color="grey", label="Null expectation (no rank correlation)",)

    start = 0

    while start < len(model_df):
        family = model_family(model_df.loc[start, "model"])
        end = start + 1

        while (
            end < len(model_df)
            and model_family(model_df.loc[end, "model"]) == family
        ):
            end += 1

        if start > 0:
            ax.axvline(start - 0.5, linewidth=1, linestyle="--", alpha=0.6,)

        midpoint = (start + end - 1)/2
        ax.text(midpoint, 1.015, family.replace("_", " "), transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontweight="bold",)
        start = end

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=55, ha="right",)

    ax.set_xlabel(MODEL_AXIS_LABEL)
    ax.set_ylabel(y_axis_label(SPEARMAN_COEFFICIENT_LABEL, NULL_STANDARD_DEVIATION))
    ax.set_title(plot_title(MODEL_LEVEL, BRAIN_MODEL_SPEARMAN_ALIGNMENT, args.dataset, args.similarity_type), pad=32,)
    ax.set_ylim(*spearman_ylim(np.concatenate([model_coefficients - model_errors, model_coefficients + model_errors]),))
    ax.grid(axis="y", alpha=0.25)
    add_legend(ax, significance_legend_handles())

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.24, top=0.82)
    fig.savefig(
        model_level_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    concept_df["x_position"] = concept_df["label"].map(x_positions)

    boxplot_values = [
        concept_df.loc[concept_df["label"] == label, "observed_spearman_coefficient",].to_numpy(dtype=float)
        for label in labels
    ]

    jitter = [
        deterministic_jitter(label=row.label, concept=str(row.concept), width=0.35)
        for row in concept_df.itertuples(index=False)
    ]

    concept_level_path = Path(args.concept_level_plot)
    concept_level_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(10, 0.75*len(labels))
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    colour_by_concept = concept_colours(concept_df["concept"].astype(str))
    colours = concept_df["concept"].astype(str).map(colour_by_concept).tolist()
    alpha = concept_point_alpha(len(colour_by_concept))
    concept_x_values = concept_df["x_position"].to_numpy(dtype=float) + np.asarray(jitter)
    concept_coefficients = concept_df["observed_spearman_coefficient"].to_numpy(dtype=float)

    ax.scatter(concept_x_values, concept_coefficients, s=10, c=colours, alpha=alpha, edgecolors="none", zorder=2,)
    ax.boxplot(boxplot_values, 
               positions=range(len(labels)), 
               widths=0.55, 
               showfliers=False,
               boxprops={"linewidth": 1.5,},
               whiskerprops={"linewidth": 1.5,},
               capprops={"linewidth": 1.5,},
               medianprops={"linewidth": 1.5,},
               zorder=3,)
    mark_degenerate_boxplot_statistics(ax, boxplot_values)
    ax.axhline(0.0, linestyle="--", linewidth=1.2, color="grey", label="Null expectation (no rank correlation)",)
    add_model_family_annotations(ax, labels)
    annotate_significance(ax, x, model_df["empirical_upper_tail_p_value"], model_df["q_value"])

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=55, ha="right",)

    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(*spearman_ylim(concept_coefficients))

    ax.set_title(plot_title(CONCEPT_LEVEL, BRAIN_MODEL_SPEARMAN_ALIGNMENT, args.dataset, args.similarity_type), pad=32,)
    ax.set_xlabel(MODEL_AXIS_LABEL)
    ax.set_ylabel(y_axis_label(SPEARMAN_COEFFICIENT_LABEL))
    ax.grid(axis="y", alpha=0.25)

    add_legend(ax, significance_legend_handles())
    fig.tight_layout()
    fig.subplots_adjust(
        bottom=0.24,
        top=0.82,
    )
    fig.savefig(
        concept_level_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

if __name__ == "__main__":
    main()
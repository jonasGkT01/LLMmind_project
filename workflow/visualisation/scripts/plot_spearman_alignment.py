#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from libraries.compute_statistics import benjamini_hochberg
from libraries.manage_model_metadata import model_family, model_sort_key, parse_model_parameters
from libraries.validate_data import validate_required_columns
from libraries.visualisation_utils import significance_label, deterministic_jitter

def spearman_ylim(values, padding=0.10, minimum_limit=0.10, step=0.05):
    values = np.asarray(values, dtype=float)

    max_abs = np.max(np.abs(values))
    limit = max(minimum_limit, max_abs * (1.0 + padding))
    limit = np.ceil(limit / step) * step
    limit = min(1.0, limit)

    return -limit, limit

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
    ax.plot(x, model_df["observed_spearman_coefficient"], marker="o", linewidth=1.8,)

    for (x_position, coefficient, q_value,) in zip(x, model_df["observed_spearman_coefficient"], model_df["q_value"],):
        significance = significance_label(q_value)

        if significance:
            ax.annotate(significance, xy=(x_position, coefficient,), xytext=(0, 6), textcoords="offset points", ha="center", va="bottom",)

    ax.axhline(0.0, linewidth=1, linestyle="--", alpha=0.6,)

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

    ax.set_xlabel("Model")
    ax.set_ylabel("Spearman's rank correlation coefficient")
    ax.set_title(f"Brain-model Spearman alignment\n"
                 f"dataset={args.dataset}, similarity={args.similarity_type}",
                 pad=32,)
    ax.set_ylim(*spearman_ylim(model_df["observed_spearman_coefficient"],))
    ax.grid(axis="y", alpha=0.25)

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
    
    concept_level_path = Path(args.concept_level_plot)
    concept_level_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(10, 0.75*len(labels))
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    ax.scatter(concept_df["x_position"] + jitter, concept_df["observed_spearman_coefficient"], s=10, alpha=0.20, edgecolors="none", zorder=1,)
    ax.boxplot(boxplot_values, 
               positions=range(len(labels)), 
               widths=0.55, 
               showfliers=False,
               boxprops={"linewidth": 1.5,},
               whiskerprops={"linewidth": 1.5,},
               capprops={"linewidth": 1.5,},
               medianprops={"linewidth": 1.5,},
               zorder=3,)
    ax.axhline(0.0, linestyle="--", linewidth=1.2, label="No rank correlation",)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=55, ha="right",)

    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(*spearman_ylim(concept_df["observed_spearman_coefficient"],))

    ax.set_title(f"Concept-level LLM-brain Spearman alignment\n"
                 f"dataset={args.dataset}, similarity={args.similarity_type}",
                 pad=32,)
    ax.set_xlabel("Model")
    ax.set_ylabel("Spearman's rank correlation coefficient")
    ax.grid(axis="y", alpha=0.25)

    ax.legend()
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
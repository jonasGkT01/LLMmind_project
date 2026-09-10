#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from libraries.manage_model_metadata import model_family, model_label, parse_model_parameters

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

    for name, df in [
        ("model-level", model_df),
        ("concept-level", concept_df),
    ]:
        required_columns = {
            "dataset",
            "model",
            "stimuli_type",
            "similarity_type",
            "observed_spearman_coefficient",
        }

        if name == "concept-level":
            required_columns.add("concept")

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(f"{name} Spearman data is missing columns: {sorted(missing_columns)}")

        if set(df["dataset"]) != {args.dataset}:
            raise ValueError(f"{name} Spearman data contains an unexpected dataset")

        if set(df["similarity_type"]) != {args.similarity_type}:
            raise ValueError(f"{name} Spearman data contains an unexpected similarity type")

        coefficients = pd.to_numeric(
            df["observed_spearman_coefficient"],
            errors="coerce",
        )

        if coefficients.isna().any() or ((coefficients < -1) | (coefficients > 1)).any():
            raise ValueError(f"{name} Spearman data contains invalid coefficients")

        df["observed_spearman_coefficient"] = coefficients
        df["label"] = [
            model_label(model, stimuli_type)
            for model, stimuli_type in zip(
                df["model"],
                df["stimuli_type"],
            )
        ]

    if model_df["label"].duplicated().any():
        raise ValueError("More than one model-level Spearman coefficient was provided for the same model/stimuli type")

    if set(model_df["label"]) != set(concept_df["label"]):
        raise ValueError("Model-level and concept-level Spearman files contain different models")

    missing_parameters = set(model_df["model"]) - set(parameters_by_model)

    if missing_parameters:
        raise ValueError(f"No number of parameters was provided for models: {sorted(missing_parameters)}")

    model_df["family"] = model_df["model"].map(model_family)
    model_df["parameters"] = model_df["model"].map(parameters_by_model)
    model_df = model_df.sort_values(
        [
            "stimuli_type",
            "family",
            "parameters",
            "model",
        ]
    ).reset_index(drop=True)

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
    ax.plot(
        x,
        model_df["observed_spearman_coefficient"],
        marker="o",
        linewidth=1.8,
    )
    ax.axhline(
        0.0,
        linewidth=1,
        linestyle="--",
        alpha=0.6,
    )

    start = 0

    while start < len(model_df):
        stimuli_type = model_df.loc[start, "stimuli_type"]
        family = model_df.loc[start, "family"]
        end = start + 1

        while (
            end < len(model_df)
            and model_df.loc[end, "stimuli_type"] == stimuli_type
            and model_df.loc[end, "family"] == family
        ):
            end += 1

        if start > 0:
            ax.axvline(
                start - 0.5,
                linewidth=1,
                linestyle="--",
                alpha=0.6,
            )

        midpoint = (start + end - 1)/2
        ax.text(
            midpoint,
            1.015,
            family.replace("_", " "),
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontweight="bold",
        )
        start = end

    ax.set_xticks(x)
    ax.set_xticklabels(
        labels,
        rotation=55,
        ha="right",
    )
    ax.set_xlabel("Model")
    ax.set_ylabel("Spearman's rank correlation coefficient")
    ax.set_title(f"Brain-model Spearman alignment\n"
                 f"dataset={args.dataset}, similarity={args.similarity_type}",
                 pad=32,)
    ax.set_ylim(-1, 1)
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
    hashes = pd.util.hash_pandas_object(
        concept_df[["label", "concept"]].astype(str),
        index=False,
    ).to_numpy(dtype=np.uint64)
    jitter = (
        hashes.astype(np.float64)/np.iinfo(np.uint64).max - 0.5
    )*0.5

    concept_level_path = Path(args.concept_level_plot)
    concept_level_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(10, 0.6*len(labels))
    fig, ax = plt.subplots(figsize=(fig_width, 7))
    ax.scatter(
        concept_df["x_position"] + jitter,
        concept_df["observed_spearman_coefficient"],
        s=18,
        alpha=0.45,
        edgecolors="none",
    )
    ax.axhline(
        0.0,
        linestyle="--",
        linewidth=1.2,
        label="No rank correlation",
    )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(
        labels,
        rotation=90,
    )
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(-1, 1)
    ax.set_title(f"Concept-level LLM-brain Spearman alignment\n"
                 f"dataset={args.dataset}, similarity={args.similarity_type}")
    ax.set_xlabel("Model")
    ax.set_ylabel("Spearman's rank correlation coefficient")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        concept_level_path,
        dpi=300,
    )
    plt.close(fig)

if __name__ == "__main__":
    main()
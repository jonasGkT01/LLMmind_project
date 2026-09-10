#!/usr/bin/env python3
import argparse
import hashlib
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from libraries.manage_model_metadata import model_family, model_label, parse_model_parameters

def parse_spearman_path(path):
    filename = Path(path).name
    pattern = (
        r"dataset-(?P<dataset>.+?)"
        r"_model-(?P<model>.+?)-(?P<stimuli_type>[^_]+)"
        r"_brain_(?P<similarity_type>.+?)"
        r"-similarity_spearman-alignment"
        r"\.parquet$"
    )
    match = re.fullmatch(pattern, filename)

    if match is None:
        raise ValueError(f"Could not parse concept-level Spearman filename: {filename}")

    return match.groupdict()

def model_sort_key(label, model_metadata, parameters_by_model):
    metadata = model_metadata[label]
    model = metadata["model"]
    stimuli_type = metadata["stimuli_type"]

    if model not in parameters_by_model:
        raise ValueError(f"No number of parameters was provided for model {model}")

    return (stimuli_type, model_family(model), parameters_by_model[model], model,)

def deterministic_jitter(label, concept, width=0.5):
    digest = hashlib.sha256(f"{label}\0{concept}".encode("utf-8")).digest()
    unit_interval_value = int.from_bytes(digest[:8], byteorder="big")/(2**64 - 1)

    return (unit_interval_value - 0.5)*width

def read_model_coefficients(path, expected_dataset, expected_similarity_type):
    metadata = parse_spearman_path(path)

    if metadata["dataset"] != expected_dataset:
        raise ValueError(f"Unexpected dataset in {path}: {metadata['dataset']}")

    if metadata["similarity_type"] != expected_similarity_type:
        raise ValueError(f"Unexpected similarity type in {path}: {metadata['similarity_type']}")

    coefficient_df = pd.read_parquet(path, engine="pyarrow")
    required_columns = {
        "concept",
        "spearman_coefficient",
    }
    missing_columns = required_columns - set(coefficient_df.columns)

    if missing_columns:
        raise ValueError(f"Spearman file {path} is missing columns: {sorted(missing_columns)}")

    duplicated_concepts = coefficient_df.loc[
        coefficient_df["concept"].duplicated(keep=False),
        "concept",
    ].tolist()

    if duplicated_concepts:
        raise ValueError(f"Spearman file {path} contains duplicated concepts: {duplicated_concepts[:10]}")

    coefficients = pd.to_numeric(coefficient_df["spearman_coefficient"], errors="coerce",)

    if coefficients.isna().any():
        invalid_concepts = coefficient_df.loc[coefficients.isna(), "concept",].tolist()
        raise ValueError(f"Spearman file {path} contains invalid coefficients for concepts: {invalid_concepts[:10]}")

    if ((coefficients < -1) | (coefficients > 1)).any():
        invalid_concepts = coefficient_df.loc[(coefficients < -1) | (coefficients > 1), "concept",].tolist()
        raise ValueError(f"Spearman file {path} contains coefficients outside [-1, 1] for concepts: {invalid_concepts[:10]}")

    output_df = coefficient_df[["concept"]].copy()
    output_df["spearman_coefficient"] = coefficients
    output_df["model"] = metadata["model"]
    output_df["stimuli_type"] = metadata["stimuli_type"]
    output_df["label"] = model_label(metadata["model"], metadata["stimuli_type"],)

    return output_df, metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept_spearman_scores", nargs="+", required=True, help="LLM-brain concept-level Spearman-alignment Parquet files",)
    parser.add_argument("--model_parameters", nargs="+", required=True, help="Model parameter counts formatted as model=parameters_millions",)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--plot", required=True)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)
    model_dataframes = []
    model_metadata = {}

    for path in args.concept_spearman_scores:
        coefficient_df, metadata = read_model_coefficients(
            path=path,
            expected_dataset=args.dataset,
            expected_similarity_type=args.similarity_type,
        )
        label = coefficient_df["label"].iloc[0]

        if label in model_metadata:
            raise ValueError(f"More than one Spearman file was provided for {label}")

        model_metadata[label] = {
            "model": metadata["model"],
            "stimuli_type": metadata["stimuli_type"],
        }
        model_dataframes.append(coefficient_df)

    if not model_dataframes:
        raise ValueError("No concept-level Spearman files were provided")

    coefficient_df = pd.concat(model_dataframes, ignore_index=True,)
    labels = sorted(
        model_metadata,
        key=lambda label: model_sort_key(
            label,
            model_metadata,
            parameters_by_model,
        ),
    )
    x_positions = {
        label: position
        for position, label in enumerate(labels)
    }
    x_values = [
        x_positions[row.label] + deterministic_jitter(row.label, str(row.concept),)
        for row in coefficient_df.itertuples(index=False)
    ]

    output_path = Path(args.plot)
    output_path.parent.mkdir(parents=True, exist_ok=True,)

    fig_width = max(10, 0.6*len(labels),)
    fig, ax = plt.subplots(figsize=(fig_width, 7,))
    
    ax.scatter(x_values, coefficient_df["spearman_coefficient"], s=18, alpha=0.45, edgecolors="none",)
    ax.axhline(0.0, linestyle="--", linewidth=1.2, label="No rank correlation",)
    
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90,)
    
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(-1.0, 1.0)
    
    ax.set_title(f"Concept-level LLM-brain Spearman alignment\n"
                 f"dataset={args.dataset}, similarity={args.similarity_type}")
    ax.set_xlabel("Model")
    ax.set_ylabel("Spearman's rank correlation coefficient")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    
    fig.tight_layout()
    fig.savefig(
        output_path,
        dpi=300,
    )
    plt.close(fig)

if __name__ == "__main__":
    main()
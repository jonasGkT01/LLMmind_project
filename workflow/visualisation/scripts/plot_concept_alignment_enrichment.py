#!/usr/bin/env python3
import argparse
import hashlib
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

def parse_alignment_score_path(path):
    filename = Path(path).name
    pattern = (
        r"dataset-(?P<dataset>.+?)"
        r"_model-(?P<model>.+?)-(?P<stimuli_type>[^_]+)"
        r"_brain_(?P<similarity_type>.+?)"
        r"-alignment_score_(?P<number_of_neighbours>\d+)NN"
        r"\.parquet$"
    )
    match = re.fullmatch(pattern, filename)
    if match is None:
        raise ValueError(f"Could not parse LLM-brain alignment-score filename: {filename}")
    metadata = match.groupdict()
    metadata["number_of_neighbours"] = int(metadata["number_of_neighbours"])
    return metadata

def parse_model_parameters(model_parameters):
    parameters_by_model = {}
    for model_parameter in model_parameters:
        if "=" not in model_parameter:
            raise ValueError(f"Invalid model-parameter specification: {model_parameter}")
        model, number_of_parameters = model_parameter.split("=", 1)
        if model in parameters_by_model:
            raise ValueError(f"Parameters were provided more than once for model {model}")
        parameters_by_model[model] = float(number_of_parameters)
    return parameters_by_model

def model_family(model):
    if "_" not in model:
        return model
    return model.rsplit("_", 1)[0]

def model_label(model, stimuli_type):
    return f"{model}-{stimuli_type}"

def model_sort_key(label, model_metadata, parameters_by_model):
    metadata = model_metadata[label]
    model = metadata["model"]
    stimuli_type = metadata["stimuli_type"]
    if model not in parameters_by_model:
        raise ValueError(f"No number of parameters was provided for model {model}")
    return (
        stimuli_type,
        model_family(model),
        parameters_by_model[model],
        model,
    )

def deterministic_jitter(label, concept, width=0.5):
    digest = hashlib.sha256(
        f"{label}\0{concept}".encode("utf-8")
    ).digest()
    unit_interval_value = (
        int.from_bytes(digest[:8], byteorder="big")/(2**64 - 1)
    )
    return (unit_interval_value - 0.5)*width

def read_model_enrichments(
    path,
    expected_dataset,
    expected_similarity_type,
    expected_number_of_neighbours,
):
    metadata = parse_alignment_score_path(path)
    if metadata["dataset"] != expected_dataset:
        raise ValueError(f"Unexpected dataset in {path}: {metadata['dataset']}")
    if metadata["similarity_type"] != expected_similarity_type:
        raise ValueError(f"Unexpected similarity type in {path}: {metadata['similarity_type']}")
    if metadata["number_of_neighbours"] != expected_number_of_neighbours:
        raise ValueError(f"Unexpected number of neighbours in {path}: {metadata['number_of_neighbours']}")
    alignment_df = pd.read_parquet(path, engine="pyarrow",)
    required_columns = {
        "concept",
        "alignment_score",
    }
    missing_columns = required_columns - set(alignment_df.columns)
    if missing_columns:
        raise ValueError(f"Alignment-score file {path} is missing columns: {sorted(missing_columns)}")
    duplicated_concepts = alignment_df.loc[
        alignment_df["concept"].duplicated(keep=False),
        "concept",
    ].tolist()
    if duplicated_concepts:
        raise ValueError(f"Alignment-score file {path} contains duplicated concepts: {duplicated_concepts[:10]}")
    alignment_scores = pd.to_numeric(
        alignment_df["alignment_score"],
        errors="coerce",
    )
    if alignment_scores.isna().any():
        invalid_concepts = alignment_df.loc[
            alignment_scores.isna(),
            "concept",
        ].tolist()
        raise ValueError(f"Alignment-score file {path} contains invalid alignment scores for concepts: {invalid_concepts[:10]}")
    if ((alignment_scores < 0) | (alignment_scores > 1)).any():
        invalid_concepts = alignment_df.loc[
            (alignment_scores < 0)
            | (alignment_scores > 1),
            "concept",
        ].tolist()
        raise ValueError(f"Alignment-score file {path} contains scores outside [0, 1] for concepts: {invalid_concepts[:10]}")
    number_of_concepts = len(alignment_df)
    population_size = number_of_concepts - 1
    if population_size <= 0:
        raise ValueError(f"At least two concepts are required in {path}")
    if expected_number_of_neighbours > population_size:
        raise ValueError(f"{path} uses {expected_number_of_neighbours} neighbours, but only {number_of_concepts} concepts are available")

    expected_alignment_score = expected_number_of_neighbours/population_size
    output_df = alignment_df[["concept",]].copy()
    output_df["enrichment"] = alignment_scores/expected_alignment_score
    output_df["model"] = metadata["model"]
    output_df["stimuli_type"] = metadata["stimuli_type"]
    output_df["label"] = model_label(
        metadata["model"],
        metadata["stimuli_type"],
    )
    return output_df, metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores",
                        nargs="+",
                        required=True,
                        help="LLM-brain concept-level alignment-score Parquet files",)
    parser.add_argument("--model_parameters",
                        nargs="+",
                        required=True,
                        help="Model parameter counts formatted as model=parameters_millions",)
    parser.add_argument("--dataset",
                        required=True,)
    parser.add_argument("--similarity_type",
                        required=True,)
    parser.add_argument("--number_of_neighbours",
                        type=int,
                        required=True,)
    parser.add_argument("--plot",
                        required=True,)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)

    model_dataframes = []
    model_metadata = {}
    for path in args.llm_brain_alignment_scores:
        enrichment_df, metadata = read_model_enrichments(
            path=path,
            expected_dataset=args.dataset,
            expected_similarity_type=args.similarity_type,
            expected_number_of_neighbours=(
                args.number_of_neighbours
            ),
        )
        label = enrichment_df["label"].iloc[0]
        if label in model_metadata:
            raise ValueError(f"More than one alignment-score file was provided for {label}")
        model_metadata[label] = {
            "model": metadata["model"],
            "stimuli_type": metadata["stimuli_type"],
        }
        model_dataframes.append(enrichment_df)
    if not model_dataframes:
        raise ValueError("No LLM-brain alignment-score files were provided")
    enrichment_df = pd.concat(
        model_dataframes,
        ignore_index=True,
    )
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
        (
            x_positions[row.label]
            + deterministic_jitter(
                row.label,
                str(row.concept),
            )
        )
        for row in enrichment_df.itertuples(index=False)
    ]
    output_path = Path(args.plot)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    fig_width = max(
        10,
        0.6*len(labels),
    )
    fig, ax = plt.subplots(
        figsize=(
            fig_width,
            7,
        )
    )
    ax.scatter(
        x_values,
        enrichment_df["enrichment"],
        s=18,
        alpha=0.45,
        edgecolors="none",
    )
    ax.axhline(
        1.0,
        linestyle="--",
        linewidth=1.2,
        label="Hypergeometric expectation",
    )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(
        labels,
        rotation=90,
    )
    ax.set_xlim(-0.6, len(labels) - 0.4,)
    ax.set_ylim(bottom=0,)
    ax.set_title(f"Concept-level LLM-brain alignment enrichment\ndataset={args.dataset}, similarity={args.similarity_type}, neighbours={args.number_of_neighbours}")
    ax.set_xlabel("Model")
    ax.set_ylabel("Observed alignment / hypergeometric expected alignment")
    ax.grid(axis="y", alpha=0.25,)
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        output_path,
        dpi=300,
    )
    plt.close(fig)

if __name__ == "__main__":
    main()
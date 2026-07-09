#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def parse_llm_brain_path(path):
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
        raise ValueError(f"Could not parse LLM-brain filename: {filename}")

    return match.groupdict()

def parse_llm_llm_path(path):
    filename = Path(path).name

    pattern = (
        r"dataset-(?P<dataset>.+?)"
        r"_model-(?P<model_1>.+?)-(?P<stimuli_type_1>[^_]+)"
        r"_model-(?P<model_2>.+?)-(?P<stimuli_type_2>[^_]+)"
        r"_(?P<similarity_type>.+?)"
        r"-alignment_score_(?P<number_of_neighbours>\d+)NN"
        r"\.parquet$"
    )

    match = re.fullmatch(pattern, filename)

    if match is None:
        raise ValueError(f"Could not parse LLM-LLM filename: {filename}")

    return match.groupdict()

def read_mean_alignment_score(path):
    df = pd.read_parquet(path, engine="pyarrow")

    if "alignment_score" not in df.columns:
        raise ValueError(f"{path} does not contain an 'alignment_score' column")

    return float(df["alignment_score"].mean())

def model_label(model, stimuli_type):
    return f"{model}-{stimuli_type}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--llm_brain_alignment_scores",
        nargs="*",
        default=[],
        help="LLM-brain alignment score parquet files",
    )
    parser.add_argument(
        "--llm_llm_alignment_scores",
        nargs="*",
        default=[],
        help="LLM-LLM alignment score parquet files",
    )
    parser.add_argument("--heatmap", type=str, required=True)
    args = parser.parse_args()

    values = {}
    labels = set()

    for path in args.llm_brain_alignment_scores:
        metadata = parse_llm_brain_path(path)

        label = model_label(
            metadata["model"],
            metadata["stimuli_type"],
        )

        score = read_mean_alignment_score(path)

        labels.add(label)
        labels.add("brain")

        values[(label, "brain")] = score
        values[("brain", label)] = score

    for path in args.llm_llm_alignment_scores:
        metadata = parse_llm_llm_path(path)

        label_1 = model_label(
            metadata["model_1"],
            metadata["stimuli_type_1"],
        )
        label_2 = model_label(
            metadata["model_2"],
            metadata["stimuli_type_2"],
        )

        score = read_mean_alignment_score(path)

        labels.add(label_1)
        labels.add(label_2)

        values[(label_1, label_2)] = score
        values[(label_2, label_1)] = score

    if not labels:
        raise ValueError("No alignment score files were provided")

    labels = sorted(labels, key=lambda x: (x == "brain", x))

    matrix = np.full((len(labels), len(labels)), np.nan)

    for i, row_label in enumerate(labels):
        for j, col_label in enumerate(labels):
            if row_label == col_label:
                matrix[i, j] = 1.0
            elif (row_label, col_label) in values:
                matrix[i, j] = values[(row_label, col_label)]

    output_path = Path(args.heatmap)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(8, 0.45 * len(labels))
    fig_height = max(7, 0.45 * len(labels))

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    image = ax.imshow(matrix, vmin=0, vmax=1)

    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))

    ax.set_xticklabels(labels, rotation=90)
    ax.set_yticklabels(labels)

    ax.set_title("Alignment scores")
    ax.set_xlabel("Model / brain")
    ax.set_ylabel("Model / brain")

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Mean alignment score")

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

if __name__ == "__main__":
    main()
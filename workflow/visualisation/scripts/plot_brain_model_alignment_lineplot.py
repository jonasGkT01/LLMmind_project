#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from libraries.manage_model_metadata import model_family, parse_model_parameters

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

    return match.groupdict()

def read_mean_alignment_score(path):
    df = pd.read_parquet(path, engine="pyarrow")

    if "alignment_score" not in df.columns:
        raise ValueError(f"{path} does not contain an 'alignment_score' column")

    return float(df["alignment_score"].mean())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", nargs="+", required=True, help="LLM-brain alignment score parquet files")
    parser.add_argument("--model_parameters", nargs="+", required=True, help="Model parameter counts formatted as model=parameters_millions")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--plot", required=True)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)
    alignment_scores = {}
    available_models = set()
    numbers_of_neighbours = set()

    for path in args.llm_brain_alignment_scores:
        metadata = parse_alignment_score_path(path)

        if metadata["dataset"] != args.dataset:
            raise ValueError(f"{path} belongs to dataset {metadata['dataset']}, expected {args.dataset}")

        if metadata["similarity_type"] != args.similarity_type:
            raise ValueError(f"{path} uses similarity type {metadata['similarity_type']}, expected {args.similarity_type}")

        model = metadata["model"]
        number_of_neighbours = int(metadata["number_of_neighbours"])

        if model not in parameters_by_model:
            raise ValueError(f"No number of parameters was provided for model {model}")

        key = (model, number_of_neighbours)

        if key in alignment_scores:
            raise ValueError(f"More than one alignment score was found for model {model} and k={number_of_neighbours}")

        alignment_scores[key] = read_mean_alignment_score(path)
        available_models.add(model)
        numbers_of_neighbours.add(number_of_neighbours)

    if not alignment_scores:
        raise ValueError("No alignment score files were provided")

    family_order = {}

    for model in parameters_by_model:
        family = model_family(model)

        if family not in family_order:
            family_order[family] = len(family_order)

    models = sorted(
        available_models,
        key=lambda model: (
            family_order[model_family(model)],
            parameters_by_model[model],
            model,
        ),
    )
    numbers_of_neighbours = sorted(numbers_of_neighbours)

    missing_scores = [
        (model, number_of_neighbours)
        for model in models
        for number_of_neighbours in numbers_of_neighbours
        if (model, number_of_neighbours) not in alignment_scores
    ]

    if missing_scores:
        raise ValueError(f"Missing alignment scores for model/k combinations: {missing_scores}")

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

    for number_of_neighbours in numbers_of_neighbours:
        values = [alignment_scores[(model, number_of_neighbours)] for model in models]
        ax.plot(x, values, marker="o", linewidth=1.8, label=f"k={number_of_neighbours}")

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
    ax.set_xlabel("Model")
    ax.set_ylabel("Mean brain-model alignment")
    ax.set_title(f"Brain-model alignment\n"
                 f"dataset={args.dataset}, similarity={args.similarity_type}", 
                 pad=32)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.25)

    if len(numbers_of_neighbours) > 1:
        ax.legend(title="Number of neighbours")

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.24, top=0.82)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    main()
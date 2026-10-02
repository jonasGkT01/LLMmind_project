#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

import matplotlib.pyplot as plt
import numpy as np

from libraries.compute_alignment import (
    common_hypergeometric_expectation, 
    read_alignment_scores, 
)
from libraries.manage_model_metadata import (
    model_key, 
    parse_model_parameters, 
    sorted_pairwise_labels, 
)
from libraries.visualisation_utils import (
    MEAN_ALIGNMENT_SCORE_LABEL, 
    PAIRWISE_ALIGNMENT_SCORE, 
    PAIRWISE_LEVEL, 
    plot_pairwise_heatmap, 
    plot_title, 
    save_figure, 
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", 
                        nargs = "*", 
                        default = [], 
                        help = "LLM-brain alignment score parquet files")
    parser.add_argument("--llm_llm_alignment_scores", 
                        nargs = "*", 
                        default = [], 
                        help = "LLM-LLM alignment score parquet files")
    parser.add_argument("--model_parameters", 
                        nargs = "+", 
                        required = True, 
                        help = "Model parameter counts formatted as model=parameters_millions")
    parser.add_argument("--dataset", 
                        required = True)
    parser.add_argument("--similarity_type", 
                        required = True)
    parser.add_argument("--number_of_neighbours", 
                        type = int, 
                        required = True)
    parser.add_argument("--heatmap", 
                        type = str, 
                        required = True)
    args = parser.parse_args()

    # read the mean alignment score of every model-brain and model-model pair
    values = {}
    model_metadata = {}
    expectations = []

    for path in args.llm_brain_alignment_scores + args.llm_llm_alignment_scores:
        scores_df, metadata, expectation = read_alignment_scores(
            path, 
            args.dataset, 
            args.similarity_type, 
            args.number_of_neighbours, 
        )
        expectations.append(expectation)

        if "model" in metadata:
            sides = [(metadata["model"], metadata["stimuli_type"]), ("brain", None)]
        else:
            sides = [
                (metadata["model_1"], metadata["stimuli_type_1"]), 
                (metadata["model_2"], metadata["stimuli_type_2"]), 
            ]

        pair_labels = []

        for model, stimuli_type in sides:
            label = "brain" if model == "brain" else model_key(model, stimuli_type)

            if label != "brain":
                model_metadata[label] = {"model": model, "stimuli_type": stimuli_type}

            pair_labels.append(label)

        values[tuple(pair_labels)] = values[tuple(pair_labels[::-1])] = float(
            scores_df["alignment_score"].mean()
        )

    expected_alignment_score = common_hypergeometric_expectation(expectations)
    labels = sorted_pairwise_labels(
        model_metadata, 
        parse_model_parameters(args.model_parameters), 
    )

    # self-cells stay NaN, so they are drawn blank: they are 1 by definition, not computed
    matrix = np.full((len(labels), len(labels)), np.nan)

    for i, row_label in enumerate(labels):
        for j, column_label in enumerate(labels):
            if row_label != column_label and (row_label, column_label) in values:
                matrix[i, j] = values[(row_label, column_label)]

    # plot the heatmap with the score written in each cell
    figure_size = (max(8, 0.55*len(labels)), max(7, 0.55*len(labels)))
    fig, ax = plt.subplots(figsize = figure_size)

    plot_pairwise_heatmap(
        ax, 
        matrix, 
        [[f"{value:.4f}" for value in row] for row in matrix], 
        labels, 
        model_metadata, 
        (0, 1), 
        MEAN_ALIGNMENT_SCORE_LABEL, 
    )
    ax.set_title(
        plot_title(
            PAIRWISE_LEVEL, 
            PAIRWISE_ALIGNMENT_SCORE, 
            args.dataset, 
            args.similarity_type, 
            args.number_of_neighbours, 
        )
        + f"\nexpected alignment score (hypergeometric): {expected_alignment_score:.4f}"
    )

    save_figure(fig, args.heatmap, model_figure = False)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

import pandas as pd

from libraries.compute_alignment import (
    common_hypergeometric_expectation, 
    read_alignment_scores,
)
from libraries.compute_statistics import model_level_significance
from libraries.manage_model_metadata import (
    model_key, 
    parse_model_parameters, 
    sort_models,
)
from libraries.visualisation_utils import (
    add_null_line,
    ALIGNMENT_SCORE_LABEL,
    BRAIN_MODEL_ALIGNMENT_SCORE,
    CONCEPT_LEVEL,
    create_model_figure,
    plot_concept_distributions,
    plot_title,
    save_figure,
    set_alignment_score_y_axis,
    stimuli_type_legend_handles,
    style_model_axes,
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", nargs="+", required=True, help="LLM-brain concept-level alignment-score Parquet files",)
    parser.add_argument("--model_level_statistics", required=True, help="TSV file containing model-level statistics",)
    parser.add_argument("--model_parameters", nargs="+", required=True, help="Model parameter counts formatted as model=parameters_millions",)
    parser.add_argument("--dataset", required=True,)
    parser.add_argument("--similarity_type", required=True,)
    parser.add_argument("--number_of_neighbours", type=int, required=True,)
    parser.add_argument("--plot", required=True,)
    args = parser.parse_args()

    # load every model's concept-level alignment scores
    concept_dataframes = []
    expectations = []

    for path in args.llm_brain_alignment_scores:
        scores_df, metadata, expectation = read_alignment_scores(
            path, 
            args.dataset, 
            args.similarity_type, 
            args.number_of_neighbours,
        )
        scores_df["model"] = metadata["model"]
        scores_df["stimuli_type"] = metadata["stimuli_type"]
        scores_df["label"] = model_key(metadata["model"], metadata["stimuli_type"])
        concept_dataframes.append(scores_df)
        expectations.append(expectation)

    concept_df = pd.concat(concept_dataframes, ignore_index = True)
    model_df = sort_models(
        concept_df[["label", "model", "stimuli_type"]].drop_duplicates(), 
        parse_model_parameters(args.model_parameters),
    )

    if len(model_df) != len(concept_dataframes):
        raise ValueError(
            "More than one alignment-score file was provided for the same model"
        )

    labels = model_df["label"].tolist()
    p_values, q_values = model_level_significance(
        labels, 
        args.model_level_statistics, 
        args.dataset, 
        args.similarity_type, 
        args.number_of_neighbours,
    )

    # plot the concept scores of each model against the hypergeometric expectation
    fig, ax = create_model_figure(len(labels))

    plot_concept_distributions(ax, labels, concept_df, "alignment_score")
    add_null_line(
        ax, 
        common_hypergeometric_expectation(expectations), 
        "Null expectation (hypergeometric)",
    )
    style_model_axes(
        ax, 
        model_df["model"].tolist(), 
        model_df["stimuli_type"].tolist(), 
        plot_title(
            CONCEPT_LEVEL, 
            BRAIN_MODEL_ALIGNMENT_SCORE, 
            args.dataset, 
            args.similarity_type, 
            args.number_of_neighbours,
        ), 
        ALIGNMENT_SCORE_LABEL, 
        p_values, 
        q_values, 
        stimuli_type_legend_handles(model_df["stimuli_type"]),
    )
    set_alignment_score_y_axis(ax)

    save_figure(fig, args.plot)

if __name__ == "__main__":
    main()

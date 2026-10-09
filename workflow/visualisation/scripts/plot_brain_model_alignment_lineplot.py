#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details
import argparse

from libraries.compute_alignment import summarise_alignment_scores
from libraries.compute_statistics import model_level_significance
from libraries.manage_model_metadata import parse_model_parameters, sort_models
from libraries.visualisation_utils import (
    add_null_line, 
    BRAIN_MODEL_ALIGNMENT_SCORE, 
    create_model_figure, 
    HYPERGEOMETRIC_NULL_LABEL, 
    MEAN_ALIGNMENT_SCORE_LABEL, 
    MODEL_LEVEL, 
    plot_model_points, 
    plot_title, 
    save_figure, 
    set_alignment_score_y_axis, 
    STANDARD_ERROR, 
    style_model_axes, 
    y_axis_label, 
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", 
                        nargs = "+", 
                        required = True, 
                        help = "LLM-brain alignment score parquet files")
    parser.add_argument("--model_level_statistics", 
                        required = True, 
                        help = "TSV file containing model-level statistics")
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
    parser.add_argument("--plot", 
                        required = True)
    args = parser.parse_args()

    # summarise each model's concept-level alignment scores by their mean and standard error
    model_df, expectation = summarise_alignment_scores(
        args.llm_brain_alignment_scores, 
        args.dataset, 
        args.similarity_type, 
        args.number_of_neighbours, 
    )
    model_df = sort_models(model_df, parse_model_parameters(args.model_parameters))

    labels = model_df["label"].tolist()
    p_values, q_values = model_level_significance(
        labels, 
        args.model_level_statistics, 
        args.dataset, 
        args.similarity_type, 
        args.number_of_neighbours, 
    )

    # plot the model means with their standard errors against the hypergeometric expectation
    fig, ax = create_model_figure(len(labels))

    plot_model_points(
        ax, 
        model_df["mean"], 
        model_df["standard_error"], 
        model_df["stimuli_type"], 
    )
    add_null_line(ax, expectation, HYPERGEOMETRIC_NULL_LABEL)
    style_model_axes(
        ax, 
        model_df["model"].tolist(), 
        model_df["stimuli_type"].tolist(), 
        plot_title(
            MODEL_LEVEL, 
            BRAIN_MODEL_ALIGNMENT_SCORE, 
            args.dataset, 
            args.similarity_type, 
            args.number_of_neighbours, 
        ), 
        y_axis_label(MEAN_ALIGNMENT_SCORE_LABEL, STANDARD_ERROR), 
        p_values, 
        q_values, 
        [], 
    )
    set_alignment_score_y_axis(ax)

    save_figure(fig, args.plot)

if __name__ == "__main__":
    main()

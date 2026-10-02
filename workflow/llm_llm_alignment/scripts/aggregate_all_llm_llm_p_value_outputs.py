#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

from libraries.aggregate_alignment_scores import aggregate_all_p_value_outputs
from libraries.path_metadata import parse_alignment_path

# identifies one LLM-LLM result, in the order the p-value files are paired up
KEY_COLUMNS = ["dataset", "model_1", "stimuli_type_1", "model_2", "stimuli_type_2", "similarity_type", "number_of_neighbours"]
# the same columns in all_model_model_alignment_scores.tsv's column (and sort) order
METADATA_COLUMNS = ["dataset", "similarity_type", "number_of_neighbours", "model_1", "stimuli_type_1", "model_2", "stimuli_type_2"]

def validate_canonical_pair_order(paths, model_order):
    # Pairs are unordered; the workflow writes each one once, with model_1 no later than model_2 in
    # the config's model order (llm_llm_pairings() in workflow/Snakefile). Fail on anything else.
    model_rank = {model: rank for rank, model in enumerate(model_order)}
    seen_pairs = set()

    for path in paths:
        metadata = parse_alignment_path(path)
        side_1 = (metadata["model_1"], metadata["stimuli_type_1"])
        side_2 = (metadata["model_2"], metadata["stimuli_type_2"])

        for model, _ in [side_1, side_2]:
            if model not in model_rank:
                raise ValueError(f"Model {model} in {path} is not in --model_order")

        if side_1 == side_2 or model_rank[side_1[0]] > model_rank[side_2[0]]:
            raise ValueError(f"{path} is not in canonical pair order (model_1 must come no later than model_2 in the config)")

        configuration = (metadata["dataset"], metadata["similarity_type"], metadata["number_of_neighbours"])

        if configuration + (side_2, side_1) in seen_pairs:
            raise ValueError(f"The pair in {path} was also found in the reverse order")

        seen_pairs.add(configuration + (side_1, side_2))

def main():
    # "@file" reads one argument per line: the path lists exceed the 2 MB command-line limit
    parser = argparse.ArgumentParser(
        description = (
            "Aggregate all concept-level LLM-LLM empirical and hypergeometric p-value TSV "
            "files into one long model-pair-level summary TSV"
        ),
        fromfile_prefix_chars = "@",
    )
    parser.add_argument("--empirical_p_values",
                        nargs="+",
                        required=True,
                        help="Concept-level empirical p-value TSV files",)
    parser.add_argument("--hypergeometric_p_values",
                        nargs="+",
                        required=True,
                        help="Concept-level hypergeometric p-value TSV files",)
    parser.add_argument("--relabelled_common_neighbours",
                        nargs="+",
                        required=True,
                        help="All-k relabelled common-neighbours Parquet files",)
    parser.add_argument("--model_order",
                        nargs="+",
                        required=True,
                        help="Model keys in config order, which fixes each pair's canonical order",)
    parser.add_argument("--all_model_model_alignment_scores_tsv",
                        required=True,
                        help="Output long model-pair-level summary TSV",)
    parser.add_argument("--threads", 
                        type = int, 
                        required = True, 
                        help = "Number of relabelled files processed in parallel")
    args = parser.parse_args()

    validate_canonical_pair_order(args.empirical_p_values, args.model_order)

    aggregate_all_p_value_outputs(
        empirical_p_values=args.empirical_p_values,
        hypergeometric_p_values=args.hypergeometric_p_values,
        relabelled_common_neighbours=args.relabelled_common_neighbours,
        key_columns=KEY_COLUMNS,
        metadata_columns=METADATA_COLUMNS,
        tsv_path=args.all_model_model_alignment_scores_tsv,
        threads = args.threads,
    )

if __name__ == "__main__":
    main()

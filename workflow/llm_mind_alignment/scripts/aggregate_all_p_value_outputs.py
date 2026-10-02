#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

from libraries.aggregate_alignment_scores import aggregate_all_p_value_outputs

# identifies one LLM-brain result, in the order the p-value files are paired up
KEY_COLUMNS = ["dataset", "model", "stimuli_type", "similarity_type", "number_of_neighbours"]
# the same columns in all_model_brain_alignment_scores.tsv's column (and sort) order
METADATA_COLUMNS = ["dataset", "stimuli_type", "similarity_type", "number_of_neighbours", "model"]

def main():
    parser = argparse.ArgumentParser(description="Aggregate all concept-level empirical and hypergeometric p-value TSV files into one long model-level summary TSV")
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
    parser.add_argument("--all_model_brain_alignment_scores_tsv",
                        required=True,
                        help="Output long model-level summary TSV",)
    parser.add_argument("--threads", 
                        type = int, 
                        required = True, 
                        help = "Number of relabelled files processed in parallel")
    args = parser.parse_args()

    aggregate_all_p_value_outputs(
        empirical_p_values=args.empirical_p_values,
        hypergeometric_p_values=args.hypergeometric_p_values,
        relabelled_common_neighbours=args.relabelled_common_neighbours,
        key_columns=KEY_COLUMNS,
        metadata_columns=METADATA_COLUMNS,
        tsv_path=args.all_model_brain_alignment_scores_tsv,
        threads = args.threads,
    )

if __name__ == "__main__":
    main()

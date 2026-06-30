#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

def parse_p_value_path(path):
    filename = Path(path).name

    pattern = (
        r"dataset-(?P<dataset>.+?)"
        r"_model-(?P<model>.+?)-(?P<stimuli_type>[^_]+)"
        r"_brain_(?P<method>empirical|hypergeometric)"
        r"_(?P<similarity_type>.+?)"
        r"-alignment_score_(?P<number_of_neighbours>\d+)NN"
        r"\.p_value\.tsv"
    )

    match = re.fullmatch(pattern, filename)

    if match is None:
        raise ValueError(
            f"Could not parse p-value filename: {path}"
        )

    metadata = match.groupdict()
    metadata["number_of_neighbours"] = int(metadata["number_of_neighbours"])

    return metadata

def result_key(metadata):
    return (
        metadata["dataset"],
        metadata["model"],
        metadata["stimuli_type"],
        metadata["similarity_type"],
        metadata["number_of_neighbours"],
    )

def read_empirical_p_values(path):
    empirical_df = pd.read_csv(path, sep="\t")

    required_columns = {
        "concept",
        "observed_common_neighbours",
        "observed_alignment_score",
        "empirical_null_mean_alignment_score",
        "number_of_relabellings",
        "number_of_null_scores_at_least_as_large",
        "empirical_upper_tail_p_value",
    }

    missing_columns = required_columns - set(empirical_df.columns)

    if missing_columns:
        raise ValueError(
            f"Empirical p-value file {path} is missing columns: {sorted(missing_columns)}"
        )

    duplicated_concepts = empirical_df[
        empirical_df["concept"].duplicated(keep=False)
    ]["concept"].tolist()

    if duplicated_concepts:
        raise ValueError(
            f"Empirical p-value file {path} contains duplicated concepts: {duplicated_concepts[:10]}"
        )

    return empirical_df

def read_hypergeometric_p_values(path):
    hypergeometric_df = pd.read_csv(path, sep="\t")

    required_columns = {
        "concept",
        "common_neighbours",
        "alignment_score",
        "hypergeometric_upper_tail_p_value",
    }

    missing_columns = required_columns - set(hypergeometric_df.columns)

    if missing_columns:
        raise ValueError(
            f"Hypergeometric p-value file {path} is missing columns: {sorted(missing_columns)}"
        )

    duplicated_concepts = hypergeometric_df[
        hypergeometric_df["concept"].duplicated(keep=False)
    ]["concept"].tolist()

    if duplicated_concepts:
        raise ValueError(
            f"Hypergeometric p-value file {path} contains duplicated concepts: {duplicated_concepts[:10]}"
        )

    return hypergeometric_df

def validate_matching_p_values(
    empirical_df,
    hypergeometric_df,
    dataset,
    model,
    stimuli_type,
    similarity_type,
    number_of_neighbours,
):
    empirical_concepts = set(empirical_df["concept"])
    hypergeometric_concepts = set(hypergeometric_df["concept"])

    result_description = (f"dataset={dataset}, model={model}, stimuli_type={stimuli_type}, similarity_type={similarity_type}, number_of_neighbours={number_of_neighbours}")

    if empirical_concepts != hypergeometric_concepts:
        only_empirical = sorted(empirical_concepts - hypergeometric_concepts)
        only_hypergeometric = sorted(hypergeometric_concepts - empirical_concepts)

        raise ValueError(
            f"Empirical and hypergeometric concept sets differ for {result_description}. Only empirical: {only_empirical[:10]}. Only hypergeometric: {only_hypergeometric[:10]}"
        )

    comparison_df = empirical_df[
        [
            "concept",
            "observed_common_neighbours",
            "observed_alignment_score",
        ]
    ].merge(
        hypergeometric_df[
            [
                "concept",
                "common_neighbours",
                "alignment_score",
            ]
        ],
        on="concept",
        how="inner",
        validate="one_to_one",
    )

    common_neighbours_match = np.isclose(
        comparison_df["observed_common_neighbours"].to_numpy(dtype=float),
        comparison_df["common_neighbours"].to_numpy(dtype=float),
        equal_nan=True,
    )

    if not common_neighbours_match.all():
        mismatching_concepts = comparison_df.loc[
            ~common_neighbours_match,
            "concept",
        ].tolist()

        raise ValueError(
            f"Observed common-neighbour values differ between empirical and hypergeometric files for {result_description}. Mismatching concepts: {mismatching_concepts[:10]}"
        )

    alignment_scores_match = np.isclose(
        comparison_df["observed_alignment_score"].to_numpy(dtype=float),
        comparison_df["alignment_score"].to_numpy(dtype=float),
        equal_nan=True,
    )

    if not alignment_scores_match.all():
        mismatching_concepts = comparison_df.loc[
            ~alignment_scores_match,
            "concept",
        ].tolist()

        raise ValueError(
            f"Observed alignment scores differ between empirical and hypergeometric files for {result_description}. Mismatching concepts: {mismatching_concepts[:10]}"
        )

def aggregate_model_results(
    dataset,
    model,
    stimuli_type,
    similarity_type,
    number_of_neighbours,
    empirical_df,
    hypergeometric_df,
):
    validate_matching_p_values(
        empirical_df=empirical_df,
        hypergeometric_df=hypergeometric_df,
        dataset=dataset,
        model=model,
        stimuli_type=stimuli_type,
        similarity_type=similarity_type,
        number_of_neighbours=number_of_neighbours,
    )

    number_of_concepts = len(empirical_df)
    population_size = number_of_concepts - 1

    if population_size <= 0:
        hypergeom_expected_common_neighbours = np.nan
        hypergeom_expected_alignment_score = np.nan
    else:
        if number_of_neighbours > population_size:
            raise ValueError(
                f"Model {model} uses {number_of_neighbours} neighbours, but only {number_of_concepts} concepts are available"
            )

        hypergeom_expected_common_neighbours = number_of_neighbours*number_of_neighbours/population_size
        hypergeom_expected_alignment_score = number_of_neighbours/population_size

    observed_average_common_neighbours = empirical_df["observed_common_neighbours"].mean()
    observed_average_alignment_score = empirical_df["observed_alignment_score"].mean()
    empirical_null_mean_alignment_score = empirical_df["empirical_null_mean_alignment_score"].mean()
    empirical_null_mean_common_neighbours = empirical_null_mean_alignment_score*number_of_neighbours

    number_of_relabellings_series = pd.to_numeric(empirical_df["number_of_relabellings"], errors="coerce")

    if number_of_relabellings_series.isna().any():
        raise ValueError(
            f"Invalid number_of_relabellings values for model {model}"
        )

    number_of_relabellings_values = number_of_relabellings_series.unique()

    if len(number_of_relabellings_values) != 1:
        raise ValueError(
            f"Expected one number of relabellings for model {model}, but found: {number_of_relabellings_values.tolist()}"
        )

    number_of_relabellings = int(number_of_relabellings_values[0])

    return {
        "dataset": dataset,
        "model": model,
        "stimuli_type": stimuli_type,
        "similarity_type": similarity_type,
        "number_of_neighbours": number_of_neighbours,
        "number_of_concepts": number_of_concepts,
        "observed_average_number_of_common_neighbours": observed_average_common_neighbours,
        "observed_average_alignment_score": observed_average_alignment_score,
        "empirical_null_mean_common_neighbours": empirical_null_mean_common_neighbours,
        "empirical_null_mean_alignment_score": empirical_null_mean_alignment_score,
        "number_of_relabellings": number_of_relabellings,
        "mean_empirical_p_value_across_concepts": empirical_df["empirical_upper_tail_p_value"].mean(),
        "median_empirical_p_value_across_concepts": empirical_df["empirical_upper_tail_p_value"].median(),
        "min_empirical_p_value_across_concepts": empirical_df["empirical_upper_tail_p_value"].min(),
        "hypergeom_population_size": population_size,
        "hypergeom_expected_common_neighbours": hypergeom_expected_common_neighbours,
        "hypergeom_expected_alignment_score": hypergeom_expected_alignment_score,
        "mean_hypergeom_p_value_across_concepts": hypergeometric_df["hypergeometric_upper_tail_p_value"].mean(),
        "median_hypergeom_p_value_across_concepts": hypergeometric_df["hypergeometric_upper_tail_p_value"].median(),
        "min_hypergeom_p_value_across_concepts": hypergeometric_df["hypergeometric_upper_tail_p_value"].min(),
    }

def reshape_summary(summary_df):
    metadata_columns = [
        "dataset",
        "stimuli_type",
        "similarity_type",
        "number_of_neighbours",
        "model",
    ]

    statistic_columns = [
        column
        for column in summary_df.columns
        if column not in metadata_columns
    ]

    summary_long_df = summary_df.melt(
        id_vars=metadata_columns,
        value_vars=statistic_columns,
        var_name="statistic",
        value_name="value",
    )

    duplicated_results = summary_long_df[
        summary_long_df.duplicated(
            subset=[
                "dataset",
                "stimuli_type",
                "similarity_type",
                "number_of_neighbours",
                "statistic",
                "model",
            ],
            keep=False,
        )
    ]

    if not duplicated_results.empty:
        duplicated_keys = duplicated_results[
            [
                "dataset",
                "stimuli_type",
                "similarity_type",
                "number_of_neighbours",
                "statistic",
                "model",
            ]
        ].drop_duplicates().to_dict(orient="records")

        raise ValueError(
            f"Duplicate model results were found: {duplicated_keys[:10]}"
        )

    summary_wide_df = summary_long_df.pivot(
        index=[
            "dataset",
            "stimuli_type",
            "similarity_type",
            "number_of_neighbours",
            "statistic",
        ],
        columns="model",
        values="value",
    ).reset_index()

    summary_wide_df.columns.name = None

    statistic_order = {
        statistic: index
        for index, statistic in enumerate(statistic_columns)
    }

    summary_wide_df["_statistic_order"] = summary_wide_df["statistic"].map(statistic_order)

    summary_wide_df = summary_wide_df.sort_values(
        [
            "dataset",
            "stimuli_type",
            "similarity_type",
            "number_of_neighbours",
            "_statistic_order",
        ]
    ).drop(columns="_statistic_order").reset_index(drop=True)

    fixed_columns = [
        "dataset",
        "stimuli_type",
        "similarity_type",
        "number_of_neighbours",
        "statistic",
    ]

    model_columns = sorted(
        [
            column
            for column in summary_wide_df.columns
            if column not in fixed_columns
        ]
    )

    summary_wide_df = summary_wide_df[fixed_columns + model_columns]

    return summary_wide_df

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate all concept-level empirical and hypergeometric p-value TSV files into one transposed model-level summary TSV"
        )
    )
    parser.add_argument(
        "--empirical_p_values",
        nargs="+",
        required=True,
        help="Concept-level empirical p-value TSV files",)
    parser.add_argument(
        "--hypergeometric_p_values",
        nargs="+",
        required=True,
        help="Concept-level hypergeometric p-value TSV files",)
    parser.add_argument(
        "--all_alignment_scores_tsv",
        required=True,
        help="Output transposed model-level summary TSV",)
    args = parser.parse_args()

    empirical_paths_by_key = {}

    for path in args.empirical_p_values:
        metadata = parse_p_value_path(path)

        if metadata["method"] != "empirical":
            raise ValueError(
                f"Expected an empirical p-value file, but found: {path}"
            )

        key = result_key(metadata)

        if key in empirical_paths_by_key:
            raise ValueError(
                f"Duplicate empirical p-value file for result: {key}"
            )

        empirical_paths_by_key[key] = path

    hypergeometric_paths_by_key = {}

    for path in args.hypergeometric_p_values:
        metadata = parse_p_value_path(path)

        if metadata["method"] != "hypergeometric":
            raise ValueError(
                f"Expected a hypergeometric p-value file, but found: {path}"
            )

        key = result_key(metadata)

        if key in hypergeometric_paths_by_key:
            raise ValueError(
                f"Duplicate hypergeometric p-value file for result: {key}"
            )

        hypergeometric_paths_by_key[key] = path

    empirical_keys = set(empirical_paths_by_key)
    hypergeometric_keys = set(hypergeometric_paths_by_key)

    if empirical_keys != hypergeometric_keys:
        only_empirical = sorted(empirical_keys - hypergeometric_keys)
        only_hypergeometric = sorted(hypergeometric_keys - empirical_keys)

        raise ValueError(
            f"Empirical and hypergeometric result sets differ. Only empirical: {only_empirical}. Only hypergeometric: {only_hypergeometric}"
        )

    summary_rows = []

    for key in sorted(empirical_keys):
        dataset, model, stimuli_type, similarity_type, number_of_neighbours = key

        empirical_path = empirical_paths_by_key[key]
        hypergeometric_path = hypergeometric_paths_by_key[key]

        empirical_df = read_empirical_p_values(empirical_path)
        hypergeometric_df = read_hypergeometric_p_values(hypergeometric_path)

        summary_rows.append(
            aggregate_model_results(
                dataset=dataset,
                model=model,
                stimuli_type=stimuli_type,
                similarity_type=similarity_type,
                number_of_neighbours=number_of_neighbours,
                empirical_df=empirical_df,
                hypergeometric_df=hypergeometric_df,
            )
        )

    summary_df = pd.DataFrame(summary_rows)

    if summary_df.empty:
        raise ValueError(
            "No model results were available for aggregation"
        )

    summary_wide_df = reshape_summary(summary_df)

    tsv_path = Path(args.all_alignment_scores_tsv)
    tsv_path.parent.mkdir(parents=True, exist_ok=True)

    summary_wide_df.to_csv(
        tsv_path,
        sep="\t",
        index=False,
        float_format="%.10g",
    )

if __name__ == "__main__":
    main()
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.path_metadata import parse_llm_brain_alignment_score_path

RELABELLED_SUFFIX = "_relabelled.parquet"

def observed_path_for_relabelled_path(relabelled_path):
    relabelled_path = Path(relabelled_path)

    if not relabelled_path.name.endswith(RELABELLED_SUFFIX):
        raise ValueError(f"Relabelled alignment-score filename does not end in {RELABELLED_SUFFIX}: {relabelled_path.name}")

    return relabelled_path.with_name(relabelled_path.name[:-len(RELABELLED_SUFFIX)] + ".parquet")

def read_validated_alignment_scores(path, required_columns):
    df = pd.read_parquet(path, engine="pyarrow", columns=sorted(required_columns),)

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Alignment-score file {path} is missing columns: {sorted(missing_columns)}")

    alignment_scores = pd.to_numeric(df["alignment_score"], errors="coerce",)

    if alignment_scores.isna().any():
        raise ValueError(f"{path} contains non-numeric alignment scores")

    if ((alignment_scores < 0) | (alignment_scores > 1)).any():
        raise ValueError(f"{path} contains alignment scores outside [0, 1]")

    df["alignment_score"] = alignment_scores.astype(float)

    return df

def relabelled_null_matrix(relabelled_df, concepts, source):
    # (relabellings x concepts) matrix of relabelled scores, columns in the order of `concepts`. Built
    # from the categorical codes rather than a pivot, which is far too slow on the ~10^7-row files.
    shuffle_ids = relabelled_df["shuffle_id"].astype("category").cat.remove_unused_categories()
    concept_ids = relabelled_df["concept"].astype("category")

    concept_position = {concept: position for position, concept in enumerate(concepts)}
    category_positions = np.asarray([concept_position.get(str(concept), -1) for concept in concept_ids.cat.categories], dtype=np.int64)
    concept_codes = concept_ids.cat.codes.to_numpy()
    column_positions = category_positions[concept_codes]

    if (concept_codes < 0).any() or (column_positions < 0).any():
        raise ValueError(f"{source} contains concepts that are not in the observed alignment scores")

    number_of_relabellings = len(shuffle_ids.cat.categories)
    null_matrix = np.full((number_of_relabellings, len(concepts)), np.nan)
    null_matrix[shuffle_ids.cat.codes.to_numpy(), column_positions] = relabelled_df["alignment_score"].to_numpy(dtype=float)

    if len(relabelled_df) != null_matrix.size or np.isnan(null_matrix).any():
        raise ValueError(f"{source} does not contain exactly one score per concept per relabelling")

    return null_matrix

def compute_model_alignment_enrichment(observed_path, relabelled_path, expected_dataset, expected_similarity_type, expected_number_of_neighbours):
    """
    Enrichment of one model's observed brain-model alignment over its
    relabelling null.

    The expected alignment is the mean relabelled alignment score over every
    relabelling and every concept. Both levels are divided by this same
    value, so the model-level enrichment is exactly the mean of the
    concept-level enrichments.

    - concept level: enrichment = observed score / expected; error = SD across
      relabellings of that concept's relabelled score / expected
    - model level: enrichment = mean observed score / expected; error = SD
      across relabellings of the mean relabelled score / expected

    Both errors are the spread of the null distribution in enrichment units,
    so a point whose bar clears 1 stands out from chance.
    """
    metadata = parse_llm_brain_alignment_score_path(observed_path)

    if metadata["dataset"] != expected_dataset:
        raise ValueError(f"{observed_path} belongs to dataset {metadata['dataset']}, expected {expected_dataset}")

    if metadata["similarity_type"] != expected_similarity_type:
        raise ValueError(f"{observed_path} uses similarity type {metadata['similarity_type']}, expected {expected_similarity_type}")

    if metadata["number_of_neighbours"] != expected_number_of_neighbours:
        raise ValueError(f"{observed_path} uses k={metadata['number_of_neighbours']}, expected k={expected_number_of_neighbours}")

    observed_df = read_validated_alignment_scores(observed_path, {"concept", "alignment_score",})
    observed_df["concept"] = observed_df["concept"].astype(str)
    relabelled_df = read_validated_alignment_scores(relabelled_path, {"shuffle_id", "concept", "alignment_score",})

    duplicated_concepts = observed_df.loc[observed_df["concept"].duplicated(keep=False), "concept",].tolist()

    if duplicated_concepts:
        raise ValueError(f"Alignment-score file {observed_path} contains duplicated concepts: {duplicated_concepts[:10]}")

    # rows: relabellings, columns: concepts (in the observed order); every observed concept must appear
    null_values = relabelled_null_matrix(relabelled_df, observed_df["concept"].tolist(), relabelled_path)

    if null_values.shape[0] < 2:
        raise ValueError(f"{relabelled_path} contains fewer than two relabellings, so no null standard deviation can be computed")
    expected_alignment_score = float(null_values.mean())

    if expected_alignment_score <= 0:
        raise ValueError(f"The mean relabelled alignment score in {relabelled_path} is {expected_alignment_score}, so no enrichment can be computed")

    observed_scores = observed_df["alignment_score"].to_numpy(dtype=float)

    concept_df = pd.DataFrame(
        {
            "model": metadata["model"],
            "stimuli_type": metadata["stimuli_type"],
            "label": metadata["model"],
            "concept": observed_df["concept"].to_numpy(),
            "enrichment": observed_scores/expected_alignment_score,
            "null_standard_deviation": null_values.std(axis=0, ddof=1)/expected_alignment_score,
        }
    )

    model_summary = {
        "model": metadata["model"],
        "stimuli_type": metadata["stimuli_type"],
        "label": metadata["model"],
        "enrichment": float(observed_scores.mean()/expected_alignment_score),
        "null_standard_deviation": float(null_values.mean(axis=1).std(ddof=1)/expected_alignment_score),
        "expected_alignment_score": expected_alignment_score,
    }

    return concept_df, model_summary

def compute_alignment_enrichment(observed_paths, relabelled_paths, expected_dataset, expected_similarity_type, expected_number_of_neighbours):
    observed_path_by_name = {Path(path).name: path for path in observed_paths}
    relabelled_path_by_observed_name = {observed_path_for_relabelled_path(path).name: path for path in relabelled_paths}

    if set(observed_path_by_name) != set(relabelled_path_by_observed_name):
        unmatched = sorted(set(observed_path_by_name) ^ set(relabelled_path_by_observed_name))
        raise ValueError(f"Observed and relabelled alignment-score files do not match one-to-one, e.g. {unmatched[:5]}")

    concept_dataframes = []
    model_summaries = []

    for observed_name, observed_path in observed_path_by_name.items():
        relabelled_path = relabelled_path_by_observed_name[observed_name]
        concept_df, model_summary = compute_model_alignment_enrichment(
            observed_path=observed_path,
            relabelled_path=relabelled_path,
            expected_dataset=expected_dataset,
            expected_similarity_type=expected_similarity_type,
            expected_number_of_neighbours=expected_number_of_neighbours,
        )
        concept_dataframes.append(concept_df)
        model_summaries.append(model_summary)

    if not model_summaries:
        raise ValueError("No relabelled alignment-score files were provided")

    model_df = pd.DataFrame(model_summaries)

    if model_df["label"].duplicated().any():
        raise ValueError(f"More than one alignment-score file was provided for: {sorted(model_df.loc[model_df['label'].duplicated(), 'label'].unique())}")

    return pd.concat(concept_dataframes, ignore_index=True,), model_df

def enrichment_ylim(concept_df, model_df, padding=0.15):
    # Shared by the concept- and model-level enrichment plots of one (dataset, similarity, k), so both
    # scripts derive the same limits from the same inputs. The top always leaves the enrichment = 1
    # reference line visible, and the padding leaves room for the significance asterisks.
    upper_values = np.concatenate(
        [
            (concept_df["enrichment"] + concept_df["null_standard_deviation"]).to_numpy(dtype=float),
            (model_df["enrichment"] + model_df["null_standard_deviation"]).to_numpy(dtype=float),
        ]
    )
    top = max(1.0, float(np.nanmax(upper_values)))*(1.0 + padding)

    return 0.0, top

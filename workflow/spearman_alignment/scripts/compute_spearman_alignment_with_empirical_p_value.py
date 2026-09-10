import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

def rank_and_normalize(values, name):
    ranks = rankdata(values, method="average")
    ranks = ranks - ranks.mean()
    norm = np.linalg.norm(ranks)

    if norm == 0:
        raise ValueError(f"The {name} similarities have constant ranks")

    return ranks/norm

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain_similarity", required=True)
    parser.add_argument("--model_similarity", required=True)
    parser.add_argument("--model_level_output", required=True)
    parser.add_argument("--concept_level_output", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--stimuli_type", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--number_of_relabellings", type=int, required=True)
    parser.add_argument("--random_seed", type=int, default=0)
    args = parser.parse_args()

    if args.number_of_relabellings <= 0:
        raise ValueError("--number_of_relabellings must be a positive integer")

    brain_similarity_df = pd.read_parquet(args.brain_similarity, engine="pyarrow")
    model_similarity_df = pd.read_parquet(args.model_similarity, engine="pyarrow")

    for name, similarity_df in [
        ("brain", brain_similarity_df),
        ("model", model_similarity_df),
    ]:
        if similarity_df.shape[0] != similarity_df.shape[1]:
            raise ValueError(f"The {name} similarity matrix is not square: shape={similarity_df.shape}")

        if similarity_df.index.has_duplicates or similarity_df.columns.has_duplicates:
            raise ValueError(f"The {name} similarity matrix contains duplicate labels")

        if set(similarity_df.index) != set(similarity_df.columns):
            raise ValueError(f"The {name} similarity matrix contains different row and column concepts")

        similarity = similarity_df.loc[
            similarity_df.index,
            similarity_df.index,
        ].to_numpy(dtype=np.float64, copy=False)

        if not np.isfinite(similarity).all():
            raise ValueError(f"The {name} similarity matrix contains non-finite values")

        if not np.allclose(similarity, similarity.T, rtol=1e-10, atol=1e-12):
            raise ValueError(f"The {name} similarity matrix is not symmetric")

    concepts = brain_similarity_df.index.to_numpy()

    if set(concepts) != set(model_similarity_df.index):
        raise ValueError("Brain and model similarity matrices contain different concepts")

    if len(concepts) < 3:
        raise ValueError("At least three concepts are required to compute Spearman alignment")

    brain_similarity_df = brain_similarity_df.loc[concepts, concepts]
    model_similarity_df = model_similarity_df.loc[concepts, concepts]
    brain_similarity = brain_similarity_df.to_numpy(dtype=np.float64, copy=False)
    model_similarity = model_similarity_df.to_numpy(dtype=np.float64, copy=False)
    number_of_concepts = len(concepts)
    concept_indices = np.arange(number_of_concepts)

    row_indices, column_indices = np.triu_indices(number_of_concepts, k=1)
    brain_model_rank = rank_and_normalize(
        brain_similarity[row_indices, column_indices],
        "brain pairwise",
    )
    model_model_rank = rank_and_normalize(
        model_similarity[row_indices, column_indices],
        "model pairwise",
    )
    observed_model_coefficient = float(
        np.clip(
            np.dot(brain_model_rank, model_model_rank),
            -1.0,
            1.0,
        )
    )

    brain_concept_rank = np.zeros_like(brain_similarity, dtype=np.float64)
    model_concept_rank = np.zeros_like(model_similarity, dtype=np.float64)

    for concept_i in range(number_of_concepts):
        other_concepts = concept_indices != concept_i
        brain_concept_rank[concept_i, other_concepts] = rank_and_normalize(
            brain_similarity[concept_i, other_concepts],
            f"brain concept {concepts[concept_i]}",
        )
        model_concept_rank[concept_i, other_concepts] = rank_and_normalize(
            model_similarity[concept_i, other_concepts],
            f"model concept {concepts[concept_i]}",
        )

    observed_concept_coefficients = np.clip(
        np.einsum(
            "ij,ij->i",
            brain_concept_rank,
            model_concept_rank,
        ),
        -1.0,
        1.0,
    )

    model_global_rank_matrix = np.zeros_like(model_similarity, dtype=np.float64)
    model_global_rank_matrix[row_indices, column_indices] = model_model_rank
    model_global_rank_matrix[column_indices, row_indices] = model_model_rank

    model_null_sum = 0.0
    model_exceedances = 0
    concept_null_sum = np.zeros(number_of_concepts, dtype=np.float64)
    concept_exceedances = np.zeros(number_of_concepts, dtype=np.int64)

    for shuffle_i in range(args.number_of_relabellings):
        rng = np.random.default_rng(args.random_seed + shuffle_i)
        permutation = rng.permutation(number_of_concepts)

        relabelled_model_rank = model_global_rank_matrix[
            permutation[row_indices],
            permutation[column_indices],
        ]
        model_coefficient = float(
            np.clip(
                np.dot(brain_model_rank, relabelled_model_rank),
                -1.0,
                1.0,
            )
        )
        model_null_sum += model_coefficient
        model_exceedances += model_coefficient >= observed_model_coefficient

        relabelled_concept_rank = model_concept_rank[
            np.ix_(permutation, permutation)
        ]
        concept_coefficients = np.clip(
            np.einsum(
                "ij,ij->i",
                brain_concept_rank,
                relabelled_concept_rank,
            ),
            -1.0,
            1.0,
        )
        concept_null_sum += concept_coefficients
        concept_exceedances += concept_coefficients >= observed_concept_coefficients

        if shuffle_i == 0 or (shuffle_i + 1) % 100 == 0 or shuffle_i + 1 == args.number_of_relabellings:
            print(f"completed relabelling {shuffle_i + 1}/{args.number_of_relabellings}")

    model_level_df = pd.DataFrame(
        {
            "dataset": [args.dataset],
            "model": [args.model],
            "stimuli_type": [args.stimuli_type],
            "similarity_type": [args.similarity_type],
            "number_of_concepts": [number_of_concepts],
            "number_of_pairs": [len(row_indices)],
            "observed_spearman_coefficient": [observed_model_coefficient],
            "empirical_null_mean_spearman_coefficient": [model_null_sum/args.number_of_relabellings],
            "number_of_relabellings": [args.number_of_relabellings],
            "number_of_null_scores_at_least_as_large": [model_exceedances],
            "empirical_upper_tail_p_value": [(model_exceedances + 1)/(args.number_of_relabellings + 1)],
        }
    )
    concept_level_df = pd.DataFrame(
        {
            "dataset": args.dataset,
            "model": args.model,
            "stimuli_type": args.stimuli_type,
            "similarity_type": args.similarity_type,
            "concept": concepts,
            "number_of_relations": number_of_concepts - 1,
            "observed_spearman_coefficient": observed_concept_coefficients,
            "empirical_null_mean_spearman_coefficient": concept_null_sum/args.number_of_relabellings,
            "number_of_relabellings": args.number_of_relabellings,
            "number_of_null_scores_at_least_as_large": concept_exceedances,
            "empirical_upper_tail_p_value": (concept_exceedances + 1)/(args.number_of_relabellings + 1),
        }
    )

    model_level_path = Path(args.model_level_output)
    concept_level_path = Path(args.concept_level_output)
    model_level_path.parent.mkdir(parents=True, exist_ok=True)
    concept_level_path.parent.mkdir(parents=True, exist_ok=True)

    model_level_df.to_csv(
        model_level_path,
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    concept_level_df.to_csv(
        concept_level_path,
        sep="\t",
        index=False,
        float_format="%.6f",
    )

if __name__ == "__main__":
    main()
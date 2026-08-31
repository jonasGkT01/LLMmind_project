import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.compute_alignment import compute_common_neighbours
from libraries.compute_nearest_neighbours import compute_topk_indices, create_neighbour_mask, relabel_nearest_neighbours

def make_concept_index(concepts):
    return {concept: i for i, concept in enumerate(concepts)}

def encode_brain_nearest_neighbours(brain_nearest_neighbours_df, concepts, number_of_neighbours):
    concept_to_index = make_concept_index(concepts)
    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False)["neighbour"].agg(list).to_dict()
    rows = []

    for concept in concepts:
        concept_neighbours = neighbours_by_concept.get(concept, [])

        if len(concept_neighbours) < number_of_neighbours:
            raise ValueError(f"Concept {concept} has only {len(concept_neighbours)} brain neighbours, but {number_of_neighbours} were requested")

        encoded_neighbours = []

        for neighbour in concept_neighbours[:number_of_neighbours]:
            if neighbour not in concept_to_index:
                raise ValueError(f"Brain neighbour {neighbour} for concept {concept} is not present in the similarity matrix")

            encoded_neighbours.append(concept_to_index[neighbour])

        rows.append(encoded_neighbours)

    return np.asarray(rows, dtype=np.int64)

def select_common_neighbour_dtype(number_of_neighbours):
    if number_of_neighbours <= np.iinfo(np.uint8).max:
        return np.uint8

    if number_of_neighbours <= np.iinfo(np.uint16).max:
        return np.uint16

    if number_of_neighbours <= np.iinfo(np.uint32).max:
        return np.uint32

    raise ValueError("The requested number of neighbours is too large to store")

def create_relabelled_alignment_dataframe(common_neighbours_matrix, concepts, model, number_of_neighbours):
    number_of_relabellings, number_of_concepts = common_neighbours_matrix.shape
    number_of_rows = number_of_relabellings * number_of_concepts
    shuffle_codes = np.repeat(np.arange(number_of_relabellings, dtype=np.int32), number_of_concepts)
    concept_codes = np.tile(np.arange(number_of_concepts, dtype=np.int32), number_of_relabellings)
    common_neighbours = common_neighbours_matrix.reshape(-1)
    alignment_scores = common_neighbours.astype(np.float64) / number_of_neighbours

    result_df = pd.DataFrame(
        {
            "shuffle_id": pd.Categorical.from_codes(
                shuffle_codes,
                categories=[f"shuffle_{shuffle_i}" for shuffle_i in range(number_of_relabellings)],
                ordered=True,
            ),
            "model": pd.Categorical.from_codes(
                np.zeros(number_of_rows, dtype=np.int8),
                categories=[model],
            ),
            "concept": pd.Categorical.from_codes(
                concept_codes,
                categories=concepts,
                ordered=True,
            ),
            "common_neighbours": common_neighbours,
            "alignment_score": alignment_scores,
            "alignment_score_percentage": alignment_scores * 100,
        }
    )

    return result_df

def compute_relabelled_alignment_scores(similarity_df, brain_nearest_neighbours_df, number_of_relabellings, number_of_neighbours, random_seed, model):
    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"The LLM similarity matrix is not square: shape={similarity_df.shape}")

    if similarity_df.index.has_duplicates:
        raise ValueError("The LLM similarity matrix contains duplicate row labels")

    if similarity_df.columns.has_duplicates:
        raise ValueError("The LLM similarity matrix contains duplicate column labels")

    concepts = similarity_df.index.to_numpy()
    column_concepts = similarity_df.columns.to_numpy()

    if set(concepts) != set(column_concepts):
        raise ValueError("The LLM similarity matrix does not contain the same concepts in its rows and columns")

    similarity_df = similarity_df.loc[concepts, concepts]
    brain_nearest_neighbours_df = brain_nearest_neighbours_df[brain_nearest_neighbours_df["concept"].isin(concepts)].copy()
    brain_concepts = set(brain_nearest_neighbours_df["concept"])
    missing_brain_concepts = sorted(set(concepts) - brain_concepts)

    if missing_brain_concepts:
        raise ValueError(f"The brain nearest-neighbours dataframe is missing concepts: {missing_brain_concepts}")

    observed_llm_neighbours = compute_topk_indices(
        similarity = similarity_df.to_numpy(copy = True),
        number_of_neighbours = number_of_neighbours,
    )

    brain_neighbours = encode_brain_nearest_neighbours(
        brain_nearest_neighbours_df = brain_nearest_neighbours_df,
        concepts = concepts,
        number_of_neighbours = number_of_neighbours,
    )

    brain_neighbour_mask, concept_indices = create_neighbour_mask(brain_neighbours)

    common_neighbour_dtype = select_common_neighbour_dtype(number_of_neighbours)
    common_neighbours_matrix = np.empty(
        (number_of_relabellings, len(concepts)),
        dtype=common_neighbour_dtype,
    )
    inverse_permutation = np.empty(len(concepts), dtype=np.int64)

    for shuffle_i in range(number_of_relabellings):
        rng = np.random.default_rng(random_seed + shuffle_i)
        permutation = rng.permutation(len(concepts))
        relabelled_llm_neighbours = relabel_nearest_neighbours(
            observed_neighbours=observed_llm_neighbours,
            permutation=permutation,
            inverse_permutation=inverse_permutation,
            concept_indices=concept_indices,
        )
        common_neighbours_matrix[shuffle_i] = compute_common_neighbours(
            neighbours = relabelled_llm_neighbours,
            brain_neighbour_mask = brain_neighbour_mask,
            concept_indices = concept_indices,
        )

        if shuffle_i == 0 or (shuffle_i + 1) % 100 == 0 or shuffle_i + 1 == number_of_relabellings:
            print(f"completed relabelling {shuffle_i + 1}/{number_of_relabellings}")

    return create_relabelled_alignment_dataframe(
        common_neighbours_matrix=common_neighbours_matrix,
        concepts=concepts,
        model=model,
        number_of_neighbours=number_of_neighbours,
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_similarity", required=True)
    parser.add_argument("--isc_nearest_neighbours", required=True)
    parser.add_argument("--relabelled_alignment_score", required=True)
    parser.add_argument("--number_of_relabellings", type=int, required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--random_seed", type=int, default=0)
    parser.add_argument("--model", type=str, required=True)
    args = parser.parse_args()

    if args.number_of_relabellings <= 0:
        raise ValueError("--number_of_relabellings must be a positive integer")

    if args.number_of_neighbours <= 0:
        raise ValueError("--number_of_neighbours must be a positive integer")

    llm_similarity_df = pd.read_parquet(args.llm_similarity, engine="pyarrow")
    brain_nearest_neighbours_df = pd.read_parquet(args.isc_nearest_neighbours, engine="pyarrow")
    result = compute_relabelled_alignment_scores(
        similarity_df=llm_similarity_df,
        brain_nearest_neighbours_df=brain_nearest_neighbours_df,
        number_of_relabellings=args.number_of_relabellings,
        number_of_neighbours=args.number_of_neighbours,
        random_seed=args.random_seed,
        model=args.model,
    )

    output_path = Path(args.relabelled_alignment_score)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, engine="pyarrow", compression="snappy", index=True)

if __name__ == "__main__":
    main()
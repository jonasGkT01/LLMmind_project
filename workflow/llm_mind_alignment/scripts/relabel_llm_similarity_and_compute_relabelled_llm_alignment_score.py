import argparse
from pathlib import Path

import numpy as np
import pandas as pd

def make_concept_index(concepts):
    return {
        concept: i
        for i, concept in enumerate(concepts)
    }

def encode_brain_nearest_neighbours(
    brain_nearest_neighbours_df,
    concepts,
    number_of_neighbours,
):
    concept_to_index = make_concept_index(concepts)

    rows = []

    for concept in concepts:
        concept_neighbours = (
            brain_nearest_neighbours_df[
                brain_nearest_neighbours_df["concept"] == concept
            ]["neighbour"]
            .to_numpy()
        )

        if len(concept_neighbours) < number_of_neighbours:
            raise ValueError(
                f"Concept {concept} has only {len(concept_neighbours)} brain neighbours, but {number_of_neighbours} were requested"
            )

        encoded_neighbours = []

        for neighbour in concept_neighbours[:number_of_neighbours]:
            if neighbour not in concept_to_index:
                raise ValueError(
                    f"Brain neighbour {neighbour} for concept {concept} is not present in the similarity matrix"
                )

            encoded_neighbours.append(concept_to_index[neighbour])

        rows.append(encoded_neighbours)

    return np.asarray(rows, dtype=np.int64)

def compute_observed_topk_indices(
    similarity_df,
    number_of_neighbours,
):
    X = similarity_df.to_numpy(copy=True)

    np.fill_diagonal(X, -np.inf)

    if X.shape[0] < number_of_neighbours + 1:
        raise ValueError(
            f"Requested {number_of_neighbours} neighbours, but only {X.shape[0]} concepts are available"
        )

    idx_part = np.argpartition(X, -number_of_neighbours, axis=1)[:, -number_of_neighbours:]
    scores_part = np.take_along_axis(X, idx_part, axis=1)

    order = np.argsort(scores_part, axis=1)[:, ::-1]
    idx_topk = np.take_along_axis(idx_part, order, axis=1)

    return idx_topk.astype(np.int64)

def compute_common_neighbours(
    llm_neighbours,
    brain_neighbours,
):
    n_concepts = llm_neighbours.shape[0]

    common_neighbours = np.zeros(n_concepts, dtype=np.int64)

    for i in range(n_concepts):
        common_neighbours[i] = np.intersect1d(
            llm_neighbours[i],
            brain_neighbours[i],
            assume_unique=False,
        ).size

    return common_neighbours

def compute_relabelled_alignment_scores(
    similarity_df,
    brain_nearest_neighbours_df,
    number_of_relabellings,
    number_of_neighbours,
    random_seed,
    model,
):
    concepts = similarity_df.index.to_numpy()

    brain_nearest_neighbours_df = brain_nearest_neighbours_df[
        brain_nearest_neighbours_df["concept"].isin(concepts)
    ].copy()

    brain_concepts = set(brain_nearest_neighbours_df["concept"])
    missing_brain_concepts = sorted(set(concepts) - brain_concepts)

    if missing_brain_concepts:
        raise ValueError(
            f"The brain nearest-neighbours dataframe is missing concepts: {missing_brain_concepts}"
        )

    observed_llm_neighbours = compute_observed_topk_indices(
        similarity_df=similarity_df,
        number_of_neighbours=number_of_neighbours,
    )

    brain_neighbours = encode_brain_nearest_neighbours(
        brain_nearest_neighbours_df=brain_nearest_neighbours_df,
        concepts=concepts,
        number_of_neighbours=number_of_neighbours,
    )

    rows = []

    for shuffle_i in range(number_of_relabellings):
        rng = np.random.default_rng(random_seed + shuffle_i)

        permutation = rng.permutation(len(concepts))
        inverse_permutation = np.empty_like(permutation)
        inverse_permutation[permutation] = np.arange(len(permutation))

        relabelled_llm_neighbours = inverse_permutation[
            observed_llm_neighbours[permutation]
        ]

        common_neighbours = compute_common_neighbours(
            llm_neighbours=relabelled_llm_neighbours,
            brain_neighbours=brain_neighbours,
        )

        shuffle_df = pd.DataFrame(
            {
                "shuffle_id": f"shuffle_{shuffle_i}",
                "model": model,
                "concept": concepts,
                "common_neighbours": common_neighbours,
                "alignment_score": common_neighbours / number_of_neighbours,
                "alignment_score_percentage": common_neighbours / number_of_neighbours * 100,
            }
        )

        rows.append(shuffle_df)

        print(f"completed relabelling {shuffle_i + 1}/{number_of_relabellings}")

    return pd.concat(rows, ignore_index=True)

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

    result.to_parquet(output_path, engine="pyarrow", index=True)

if __name__ == "__main__":
    main()
import argparse

import pandas as pd

from libraries.compute_nearest_neighbours import compute_blockwise_topk_from_embeddings, write_nearest_neighbours_parquet
from libraries.compute_similarity import extract_embedding_matrix, normalize_l2, pearson_normalize

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding_dataframe",
                        type = str,
                        help = "Path to dataframe of embeddings")
    parser.add_argument("--number_of_neighbours",
                        type = int,
                        required = True,
                        help = "Number of neighbours to compute and store (the dataset's largest configured neighbourhood size)")
    parser.add_argument("--cosine_nearest_neighbours",
                        type = str,
                        help = "Path to the file containing the cosine nearest neighbours of concepts")
    parser.add_argument("--pearson_nearest_neighbours",
                        type = str,
                        help = "Path to the file containing the Pearson nearest neighbours of concepts")
    args = parser.parse_args()

    if args.number_of_neighbours <= 0:
        raise ValueError("--number_of_neighbours must be a positive integer")

    embedding_df = pd.read_parquet(args.embedding_dataframe)
    embedding_matrix = extract_embedding_matrix(embedding_df)
    concepts = embedding_df.index

    ##### COSINE SIMILARITY #####
    cosine_indices, cosine_scores = compute_blockwise_topk_from_embeddings(
        embedding_matrix = embedding_matrix,
        number_of_neighbours = args.number_of_neighbours,
        normalize_fn = normalize_l2,
    )
    write_nearest_neighbours_parquet(
        concepts = concepts,
        neighbour_indices = cosine_indices,
        neighbour_scores = cosine_scores,
        number_of_neighbours = args.number_of_neighbours,
        output_path = args.cosine_nearest_neighbours,
    )
    del cosine_indices, cosine_scores

    ##### PEARSON SIMILARITY #####
    pearson_indices, pearson_scores = compute_blockwise_topk_from_embeddings(
        embedding_matrix = embedding_matrix,
        number_of_neighbours = args.number_of_neighbours,
        normalize_fn = pearson_normalize,
    )
    write_nearest_neighbours_parquet(
        concepts = concepts,
        neighbour_indices = pearson_indices,
        neighbour_scores = pearson_scores,
        number_of_neighbours = args.number_of_neighbours,
        output_path = args.pearson_nearest_neighbours,
    )

if __name__ == "__main__":
    main()

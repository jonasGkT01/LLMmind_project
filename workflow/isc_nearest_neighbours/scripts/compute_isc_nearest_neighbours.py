# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details

import argparse

from libraries.compute_nearest_neighbours import write_all_nearest_neighbours
from libraries.compute_similarity import dataframe_to_embedding_matrix
from libraries.parquet_io import read_parquet

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--isc_dataframe", 
                        type = str, 
                        help = "Path to dataframe of ISC's")
    parser.add_argument("--number_of_neighbours", 
                        type = int, 
                        required = True, 
                        help = "Number of neighbours to compute and store (the dataset's largest configured neighbourhood size)")
    parser.add_argument("--isc_cosine_nearest_neighbours", 
                        type = str, 
                        help = "Path to the file containing the cosine nearest neighbours of concepts")
    parser.add_argument("--isc_pearson_nearest_neighbours", 
                        type = str, 
                        help = "Path to the file containing the Pearson nearest neighbours of concepts")
    parser.add_argument("--isc_spearman_nearest_neighbours", 
                        type = str, 
                        help = "Path to the file containing the Spearman nearest neighbours of concepts")
    args = parser.parse_args()

    if args.number_of_neighbours <= 0:
        raise ValueError("--number_of_neighbours must be a positive integer")

    isc_df = read_parquet(args.isc_dataframe)
    embedding_matrix = dataframe_to_embedding_matrix(isc_df)
    concepts = isc_df.index

    write_all_nearest_neighbours(
        embedding_matrix = embedding_matrix, 
        concepts = concepts, 
        number_of_neighbours = args.number_of_neighbours, 
        output_path_by_similarity_type = {
            "cosine": args.isc_cosine_nearest_neighbours, 
            "pearson": args.isc_pearson_nearest_neighbours, 
            "spearman": args.isc_spearman_nearest_neighbours, 
        }, 
    )

if __name__ == "__main__":
    main()

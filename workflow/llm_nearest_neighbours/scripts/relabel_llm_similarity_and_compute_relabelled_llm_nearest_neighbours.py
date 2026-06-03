import argparse
from pathlib import Path
import pandas as pd
from similarity_lib import relabel_wide_similarity, compute_nearest_neighbours

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--similarity_dataframe", 
                        required=True,
                        help="Path to the input similarity dataframe")
    parser.add_argument("--relabelled_nearest_neighbours", 
                        required=True,
                        help="Path to dataframe of the computed relabelled nearest neighbours")
    parser.add_argument("--number_of_relabellings", 
                        type=int, 
                        required=True,
                        help="Number of random relabellings to perform")
    parser.add_argument("--random_seed", 
                        type=int, 
                        default=0)
    parser.add_argument("--number_of_neighbours", 
                        type=int, 
                        required=True,
                        help="Number of nearest neighbours to compute for each concept")
    args = parser.parse_args()

    

    similarity_df = pd.read_parquet(args.similarity_dataframe)
    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"Expected a square matrix, got {similarity_df.shape}.")

    if list(similarity_df.index) != list(similarity_df.columns):
        similarity_df.index = similarity_df.columns

    relabelled_nearest_neighbours = {}
    for i in range(args.number_of_relabellings):
        relabelled_similarity_df = relabel_wide_similarity(similarity_df, seed=args.random_seed + i)
        nearest_neighbours = compute_nearest_neighbours(relabelled_similarity_df, args.number_of_neighbours)
        relabelled_nearest_neighbours[f"shuffle_{i}"] = nearest_neighbours

    output_path = Path(args.relabelled_nearest_neighbours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    relabelled_nearest_neighbours_df = pd.concat(relabelled_nearest_neighbours, names=["shuffle_id", "row"])
    relabelled_nearest_neighbours_df.to_parquet(output_path, engine="pyarrow")

if __name__ == "__main__":
    main()

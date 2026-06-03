import argparse
from pathlib import Path
import pandas as pd
from similarity_lib import compute_nearest_neighbours

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", 
                        type=int, 
                        required=True, 
                        help="Number of nearest neighbours to compute for each concept")
    parser.add_argument("--similarity_dataframe", 
                        required=True, 
                        help="Path to dataframe of computed similarities")
    parser.add_argument("--nearest_neighbours", 
                        required=True, 
                        help="Path to save the computed nearest neighbours dataframe")
    args = parser.parse_args()

    similarity_df = pd.read_parquet(args.similarity_dataframe)
    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"Expected a square similarity matrix, got {similarity_df.shape}.")

    if list(similarity_df.index) != list(similarity_df.columns):
        similarity_df.index = similarity_df.columns
        
    nearest_neighbours_df = compute_nearest_neighbours(similarity_df, args.number_of_neighbours)
    output_path = Path(args.nearest_neighbours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nearest_neighbours_df.to_parquet(output_path, engine="pyarrow", index=False)

if __name__ == "__main__":
    main()

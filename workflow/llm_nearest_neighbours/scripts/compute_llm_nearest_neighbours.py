import argparse
from pathlib import Path

from libraries.compute_nearest_neighbours import stream_nearest_neighbours_from_parquet

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--similarity_dataframe", required=True)
    parser.add_argument("--nearest_neighbours", required=True)
    args = parser.parse_args()

    nearest_neighbours_df = stream_nearest_neighbours_from_parquet(
        similarity_parquet_path=args.similarity_dataframe,
        number_of_neighbours=args.number_of_neighbours,
    )

    output_path = Path(args.nearest_neighbours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nearest_neighbours_df.to_parquet(output_path, engine="pyarrow", index=True)

if __name__ == "__main__":
    main()
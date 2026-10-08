# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-08, see docs/changelog/developers/ for details
import argparse

from libraries.compute_alignment import compute_alignment_scores
from libraries.compute_nearest_neighbours import read_nearest_neighbours

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", 
                        type = int, 
                        required = True, 
                        help = "Number of neighbours per concept to compare")
    parser.add_argument("--llm_nearest_neighbours_1", 
                        type = str, 
                        required = True, 
                        help = "Path to the nearest neighbours of the first model's embeddings")
    parser.add_argument("--llm_nearest_neighbours_2", 
                        type = str, 
                        required = True, 
                        help = "Path to the nearest neighbours of the second model's embeddings")
    parser.add_argument("--alignment_score", 
                        type = str, 
                        required = True, 
                        help = "Path to the output alignment scores")
    args = parser.parse_args()

    if args.number_of_neighbours <= 0:
        raise ValueError("--number_of_neighbours must be a positive integer")

    # load both neighbour files and keep the first number_of_neighbours of each concept
    nearest_neighbours_df_1 = read_nearest_neighbours(
        args.llm_nearest_neighbours_1, 
        args.number_of_neighbours
    )
    nearest_neighbours_df_2 = read_nearest_neighbours(
        args.llm_nearest_neighbours_2, 
        args.number_of_neighbours
    )

    # compute the alignment score of every shared concept
    alignment_score_df = compute_alignment_scores(
        nearest_neighbours_df_1 = nearest_neighbours_df_1, 
        nearest_neighbours_df_2 = nearest_neighbours_df_2, 
        number_of_neighbours = args.number_of_neighbours, 
    )

    if alignment_score_df.empty:
        raise ValueError(
            "No shared concepts found between the two nearest-neighbour files"
        )

    # save the alignment scores as a parquet file
    alignment_score_df.to_parquet(
        args.alignment_score, 
        engine = "pyarrow", 
        index = False
    )

if __name__ == "__main__":
    main()

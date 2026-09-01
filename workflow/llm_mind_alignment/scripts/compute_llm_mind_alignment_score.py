import argparse

import pandas as pd

from libraries.compute_alignment import compute_alignment_scores

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", 
                        type = int, 
                        help = "Set the number of neighbours to compute")
    parser.add_argument("--isc_nearest_neighbours", 
                        type = str, 
                        help = "Path to dataframe of computed nearest neighbours for the ISC model")
    parser.add_argument("--llm_nearest_neighbours", 
                        type = str, 
                        help = "Path to dataframe of computed nearest neighbours for the LLM model")
    parser.add_argument("--alignment_score", 
                        type = str, 
                        help = "Path to the file containing the alignment score")
    args = parser.parse_args()

    number_of_neighbours = args.number_of_neighbours
    isc_nearest_neighbours = args.isc_nearest_neighbours
    llm_nearest_neighbours = args.llm_nearest_neighbours
    alignment_score = args.alignment_score

    if number_of_neighbours is None or number_of_neighbours <= 0:
        raise ValueError("--number_of_neighbours must be a positive integer")

    # load the dataframes
    nearest_neighbours_df_1 = pd.read_parquet(isc_nearest_neighbours, engine = "pyarrow")
    nearest_neighbours_df_2 = pd.read_parquet(llm_nearest_neighbours, engine = "pyarrow")

    required_columns = {"concept", "neighbour"}

    missing_columns_1 = required_columns - set(nearest_neighbours_df_1.columns)
    missing_columns_2 = required_columns - set(nearest_neighbours_df_2.columns)

    if missing_columns_1:
        raise ValueError(f"The first nearest-neighbours dataframe is missing columns: {sorted(missing_columns_1)}")

    if missing_columns_2:
        raise ValueError(f"The second nearest-neighbours dataframe is missing columns: {sorted(missing_columns_2)}")

    alignment_score_df = compute_alignment_scores(
        nearest_neighbours_df_1=nearest_neighbours_df_1,
        nearest_neighbours_df_2=nearest_neighbours_df_2,
        number_of_neighbours=number_of_neighbours,
    )

    # save the alignment scores as a parquet file
    alignment_score_df.to_parquet(alignment_score, engine = "pyarrow",index = True)

#    # print the alignment score dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(alignment_score_df)

if __name__ == "__main__":
    main()
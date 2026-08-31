import argparse

import pandas as pd

from libraries.compute_nearest_neighbours import create_nearest_neighbours_dataframe

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--isc_cosine_similarity_dataframe", 
                      type = str, 
                      help = "Path to the file containing computed cosine similarities")
    parser.add_argument("--isc_pearson_similarity_dataframe", 
                      type = str, 
                      help = "Path to the file containing computed Pearson similarities")
    parser.add_argument("--isc_cosine_nearest_neighbours", 
                      type = str, 
                      help = "Path to the file containing the cosine nearest neighbours of concepts")
    parser.add_argument("--isc_pearson_nearest_neighbours", 
                      type = str, 
                      help = "Path to the file containing the Pearson nearest neighbours of concepts")
    parser.add_argument("--number_of_neighbours", 
                      type = int, 
                      help = "Set the number of neighbours to compute")
    args = parser.parse_args()

    isc_cosine_similarity_dataframe = args.isc_cosine_similarity_dataframe
    isc_pearson_similarity_dataframe = args.isc_pearson_similarity_dataframe
    isc_cosine_nearest_neighbours = args.isc_cosine_nearest_neighbours
    isc_pearson_nearest_neighbours = args.isc_pearson_nearest_neighbours
    number_of_neighbours = args.number_of_neighbours

    ##### COSINE SIMILARITY #####
    # load the dataframe
    cosine_similarity_df = pd.read_parquet(isc_cosine_similarity_dataframe, engine = "pyarrow")

    cosine_nearest_neighbours_df = (
        create_nearest_neighbours_dataframe(
            similarity_df=cosine_similarity_df,
            number_of_neighbours=number_of_neighbours,
        )
    )

    cosine_nearest_neighbours_df = (
        cosine_nearest_neighbours_df.rename(
            columns={"similarity": "cosine_similarity",}
        )
    )
    
    # save the nearest neighbours to primary concept as a parquet file
    cosine_nearest_neighbours_df.to_parquet(isc_cosine_nearest_neighbours, engine = "pyarrow", index = True)
    
#    # print the cosine nearest neighbours dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(cosine_nearest_neighbours_df)

    ##### PEARSON SIMILARITY #####
    # load the dataframe
    pearson_similarity_df = pd.read_parquet(isc_pearson_similarity_dataframe, engine="pyarrow")

    pearson_nearest_neighbours_df = (
        create_nearest_neighbours_dataframe(
            similarity_df=pearson_similarity_df,
            number_of_neighbours=number_of_neighbours,
        )
    )

    pearson_nearest_neighbours_df = (
        pearson_nearest_neighbours_df.rename(
            columns={"similarity": "pearson_similarity",}
        )
    )
    
    # save the nearest neighbours to primary concept as a parquet file
    pearson_nearest_neighbours_df.to_parquet(isc_pearson_nearest_neighbours, engine = "pyarrow", index = True)

if __name__ == "__main__":
    main()
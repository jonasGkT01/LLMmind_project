import numpy as np
import pandas as pd

import argparse

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
    cosine_similarity_df = pd.read_parquet(isc_cosine_similarity_dataframe, engine="pyarrow")

    X = cosine_similarity_df.values
    concepts = cosine_similarity_df.index.to_numpy()
    neighbours = cosine_similarity_df.columns.to_numpy()
    k_eff = min(number_of_neighbours, X.shape[1] - 1)

    # row by row, partition it storing the indices of largest values in the last positions, then keep only those
    idx_part = np.argpartition(X, -k_eff, axis = 1)[:, -k_eff:]
    # row by row, take the values corresponding to the indices selected above
    scores_part = np.take_along_axis(X, idx_part, axis = 1)

    # row by row, returns the indices that would sort that row in ascending order, then reverse it
    order = np.argsort(scores_part, axis = 1)[:, ::-1]
    # row by row, take the indices according to the order selected above
    idx_topk = np.take_along_axis(idx_part, order, axis = 1)
    # row by row, take the values according to the indices selected above
    scores_topk = np.take_along_axis(X, idx_topk, axis = 1)

    # create a pandas dataframe to store the nearest neighbours of each concept
    cosine_nearest_neighbours_df = pd.DataFrame({
        "concept": np.repeat(concepts, k_eff), 
        "neighbour": neighbours[idx_topk.reshape(-1)], 
        "cosine_similarity": scores_topk.reshape(-1)
    })
#    cosine_nearest_neighbours_df = cosine_nearest_neighbours_df.sort_index()
    
    # save the nearest neighbours to primary concept as a parquet file
    cosine_nearest_neighbours_df.to_parquet(isc_cosine_nearest_neighbours, engine = "pyarrow", index = True)
    
#    # print the cosine nearest neighbours dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(cosine_nearest_neighbours_df)

    ##### PEARSON SIMILARITY #####
    # load the dataframe
    pearson_similarity_df = pd.read_parquet(isc_pearson_similarity_dataframe, engine="pyarrow")

    X = pearson_similarity_df.values
    concepts = pearson_similarity_df.index.to_numpy()
    neighbours = pearson_similarity_df.columns.to_numpy()
    k_eff = min(number_of_neighbours, X.shape[1] - 1)

    # row by row, partition it storing the indices of largest values in the last positions, then keep only those
    idx_part = np.argpartition(X, -k_eff, axis = 1)[:, -k_eff:]
    # row by row, take the values corresponding to the indices selected above
    scores_part = np.take_along_axis(X, idx_part, axis = 1)

    # row by row, returns the indices that would sort that row in ascending order, then reverse it
    order = np.argsort(scores_part, axis = 1)[:, ::-1]
    # row by row, take the indices according to the order selected above
    idx_topk = np.take_along_axis(idx_part, order, axis = 1)
    # row by row, take the values according to the indices selected above
    scores_topk = np.take_along_axis(X, idx_topk, axis = 1)

    # create a pandas dataframe to store the nearest neighbours of each concept
    pearson_nearest_neighbours_df = pd.DataFrame({
        "concept": np.repeat(concepts, k_eff), 
        "neighbour": neighbours[idx_topk.reshape(-1)], 
        "pearson_similarity": scores_topk.reshape(-1)
    })
#    pearson_nearest_neighbours_df = pearson_nearest_neighbours_df.sort_index()
    
    # save the nearest neighbours to primary concept as a parquet file
    pearson_nearest_neighbours_df.to_parquet(isc_pearson_nearest_neighbours, engine = "pyarrow", index = True)

if __name__ == "__main__":
    main()
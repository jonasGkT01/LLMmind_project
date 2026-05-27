import numpy as np
import pandas as pd

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", 
                      type = int, 
                      help = "Set the number of neighbours to compute")
    parser.add_argument("--cosine_similarity_dataframe", 
                      type = str, 
                      help = "Path to the file containing computed cosine similarities")
    parser.add_argument("--pearson_similarity_dataframe", 
                      type = str, 
                      help = "Path to the file containing computed Pearson similarities")
    parser.add_argument("--cosine_nearest_neighbours", 
                      type = str, 
                      help = "Path to the file containing the nearest neighbours of the primary concepts")
    parser.add_argument("--pearson_nearest_neighbours", 
                      type = str, 
                      help = "Path to the file containing the nearest neighbours of the primary concepts")
    args = parser.parse_args()

    number_of_neighbours = args.number_of_neighbours
    cosine_similarity_dataframe = args.cosine_similarity_dataframe
    pearson_similarity_dataframe = args.pearson_similarity_dataframe
    cosine_nearest_neighbours = args.cosine_nearest_neighbours
    pearson_nearest_neighbours = args.pearson_nearest_neighbours

    # load the dataframe
    cosine_similarity_df = pd.read_parquet(cosine_similarity_dataframe, engine="pyarrow")
    pearson_similarity_df = pd.read_parquet(pearson_similarity_dataframe, engine="pyarrow")

    ##### COSINE SIMILARITY #####
    # process cosine similarities
    X_cosine = cosine_similarity_df.values
    concepts = cosine_similarity_df.index.to_numpy()
    neighbours = cosine_similarity_df.columns.to_numpy()
    k_eff = min(number_of_neighbours, X_cosine.shape[1] - 1)

    # row by row, partition it storing the indices of largest values in the last positions, then keep only those
    idx_part = np.argpartition(X_cosine, -k_eff, axis=1)[:, -k_eff:]
    # row by row, take the values corresponding to the indices selected above
    scores_part = np.take_along_axis(X_cosine, idx_part, axis=1)

    # row by row, returns the indices that would sort that row in ascending order, then reverse it
    order = np.argsort(scores_part, axis=1)[:, ::-1]
    # row by row, take the indices according to the order selected above
    idx_topk = np.take_along_axis(idx_part, order, axis=1)
    # row by row, take the values according to the indices selected above
    scores_topk = np.take_along_axis(X_cosine, idx_topk, axis=1)

    # create a pandas dataframe to store the nearest neighbours of each concept
    cosine_nearest_neighbours_df = pd.DataFrame({
        "concept": np.repeat(concepts, k_eff), 
        "neighbour": neighbours[idx_topk.reshape(-1)], 
        "cosine_similarity": scores_topk.reshape(-1)
    })
#    cosine_nearest_neighbours_df = cosine_nearest_neighbours_df.sort_index()

    # save the nearest neighbours to primary concept as a parquet file
    cosine_nearest_neighbours_df.to_parquet(cosine_nearest_neighbours, engine="pyarrow", index=True)
    
#    # print the cosine similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(cosine_nearest_neighbours_df)

    ##### PEARSON SIMILARITY #####
    # process Pearson similarities
    X_pearson = pearson_similarity_df.values
    concepts = pearson_similarity_df.index.to_numpy()
    neighbours = pearson_similarity_df.columns.to_numpy()
    k_eff = min(number_of_neighbours, X_pearson.shape[1] - 1)

    # row by row, partition it storing the indices of largest values in the last positions, then keep only those
    idx_part = np.argpartition(X_pearson, -k_eff, axis=1)[:, -k_eff:]
    # row by row, take the values corresponding to the indices selected above
    scores_part = np.take_along_axis(X_pearson, idx_part, axis=1)

    # row by row, returns the indices that would sort that row in ascending order, then reverse it
    order = np.argsort(scores_part, axis=1)[:, ::-1]
    # row by row, take the indices according to the order selected above
    idx_topk = np.take_along_axis(idx_part, order, axis=1)
    # row by row, take the values according to the indices selected above
    scores_topk = np.take_along_axis(X_pearson, idx_topk, axis=1)

    # create a pandas dataframe to store the nearest neighbours of each concept
    pearson_nearest_neighbours_df = pd.DataFrame({
        "concept": np.repeat(concepts, k_eff), 
        "neighbour": neighbours[idx_topk.reshape(-1)], 
        "pearson_similarity": scores_topk.reshape(-1)
    })
#    pearson_nearest_neighbours_df = pearson_nearest_neighbours_df.sort_index()

    # save the nearest neighbours to primary concept as a parquet file
    pearson_nearest_neighbours_df.to_parquet(pearson_nearest_neighbours, engine="pyarrow", index=True)
    
#    # print the pearsonnearest neighbours dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(pearson_nearest_neighbours_df)

if __name__ == "__main__":
    main()
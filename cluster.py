from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import pandas as pd


def run_cluster(df: pd.DataFrame, k: int):
    """
    Performing k-means clustering on the given DataFrame.
    Parameters:
    df (pd.DataFrame): The input DataFrame.
    k (int): The number of clusters to create.
    """
    kmeans = KMeans(n_clusters=k, random_state=0)
    kmeans.fit(df.drop("name", axis=1))
    df["Cluster"] = kmeans.labels_
    return df

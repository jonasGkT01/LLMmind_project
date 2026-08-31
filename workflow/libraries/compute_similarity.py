import numpy as np

def normalize_l2(x):
    x = np.asarray(x, dtype=np.float64)

    if x.ndim == 1:
        norm = np.linalg.norm(x)

        if norm == 0:
            return x

        return x / norm

    if x.ndim != 2:
        raise ValueError(
            f"Expected 1D or 2D array, got {x.ndim}D"
        )

    norm = np.linalg.norm(x, 2, axis=1, keepdims=True,)

    return np.divide(x, norm, out=np.zeros_like(x), where=norm != 0,)

def pearson_normalize(x):
    x = np.asarray(x, dtype=np.float64)

    if x.ndim != 2:
        raise ValueError(
            f"Expected 2D embedding matrix, got {x.ndim}D"
        )

    x = x - np.mean(x, axis=1, keepdims=True,)

    return normalize_l2(x)

def cosine_similarity(x):
    x = normalize_l2(x)

    return x @ x.T

def pearson_similarity(x):
    x = pearson_normalize(x)

    return x @ x.T
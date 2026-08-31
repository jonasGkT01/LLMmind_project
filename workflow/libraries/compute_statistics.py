import numpy as np

def empirical_upper_tail_p_value(
    number_at_least_as_large,
    number_of_relabellings,
):
    return (number_at_least_as_large + 1)/(number_of_relabellings + 1)

def benjamini_hochberg(p_values):
    p_values = np.asarray(p_values, dtype = float,)

    if len(p_values) == 0:
        return np.asarray([], dtype=float)

    order = np.argsort(p_values)
    ordered_p_values = p_values[order]

    ordered_q_values = ordered_p_values*len(p_values)/np.arange(1, len(p_values) + 1,)
    ordered_q_values = np.minimum.accumulate(ordered_q_values[::-1])[::-1]
    q_values = np.empty_like(ordered_q_values)
    q_values[order] = np.minimum(ordered_q_values, 1.0,)

    return q_values
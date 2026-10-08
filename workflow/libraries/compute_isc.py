# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-08, see docs/changelog/developers/ for details
import numpy as np

# a float32 signal whose range is within a few ulps of its magnitude is only rounding noise.
# np.isclose() defaults (rtol=1e-5) were too loose: they flagged real low-amplitude signals
# (e.g. < ~0.01 variation on BOLD values around 1000) as constant
CONSTANT_SIGNAL_RTOL = 8*np.finfo(np.float32).eps

def is_constant_signal(x, axis = 0):
    x = np.asarray(x, dtype = np.float64,)
    signal_range = np.ptp(x, axis = axis,)
    magnitude = np.max(np.abs(x), axis = axis,)

    return signal_range <= CONSTANT_SIGNAL_RTOL*magnitude

def compute_leave_one_out_isc(data):
    """
        Leave-one-out ISC, vectorized across parcels.

        For every parcel, the mean over subjects of the Pearson r between each subject's
        time course and the mean time course of the other subjects. A constant signal
        gives r = 0.
    """
    n_subjects = data.shape[0]
    n_parcels = data.shape[2]

    isc = np.zeros((n_subjects, n_parcels), dtype = np.float64,)

    for subject_idx in range(n_subjects):
        other_subjects = np.arange(n_subjects) != subject_idx
        x = data[subject_idx].astype(np.float64,)
        y = data[other_subjects].mean(axis = 0,).astype(np.float64,)

        x_centered = x - x.mean(axis = 0, keepdims = True,)
        y_centered = y - y.mean(axis = 0, keepdims = True,)

        numerator = (x_centered*y_centered).sum(axis = 0,)
        denominator = np.sqrt(
            (x_centered**2).sum(axis = 0,)*(y_centered**2).sum(axis = 0,)
        )

        with np.errstate(invalid = "ignore", divide = "ignore",):
            r = numerator/denominator

        is_constant_x = is_constant_signal(x, axis = 0,)
        is_constant_y = is_constant_signal(y, axis = 0,)

        r = np.where(is_constant_x | is_constant_y, 0.0, r,)

        isc[subject_idx] = np.nan_to_num(r, nan = 0.0, posinf = 0.0, neginf = 0.0,)

    return isc.mean(axis = 0).astype(np.float32)

def average_repeats_by_subject(arrays, subjects):
    # one (time x parcel) array per subject: the time-point-wise mean of that subject's
    # repeats, so the leave-one-out ISC never compares a subject with itself
    if len(arrays) != len(subjects):
        raise ValueError(f"Got {len(arrays)} arrays but {len(subjects)} subjects")

    repeats_by_subject = {}

    for array, subject in zip(arrays, subjects):
        repeats_by_subject.setdefault(str(subject), []).append(array)

    return [
        np.mean(np.stack(repeats_by_subject[subject], axis = 0), axis = 0)
        for subject in sorted(repeats_by_subject)
    ]

def compute_isc_from_files(
    paths, 
    n_rois, 
    subjects = None, 
    truncate_to_shortest = False, 
):
    # load the (time x parcel) arrays and check their shapes
    if len(paths) < 2:
        raise ValueError(
            f"ISC requires at least two parcel time-series files, got {len(paths)}"
        )

    arrays = [np.load(path) for path in paths]

    for path, array in zip(paths, arrays):
        if array.ndim != 2 or array.shape[1] != n_rois:
            raise ValueError(
                f"Expected a (time x {n_rois}) parcel time series, "
                f"got shape {array.shape}: {path}"
            )

    # make all time lengths equal, or stop
    lengths = [array.shape[0] for array in arrays]
    shortest = min(lengths)

    if shortest != max(lengths):
        if not truncate_to_shortest:
            details = ", ".join(
                f"{path}: {length}"
                for path, length in zip(paths, lengths)
            )
            raise ValueError(f"Mismatched time lengths across parcel files: {details}")

        truncated = [
            f"{path}: {length}"
            for path, length in zip(paths, lengths)
            if length != shortest
        ]
        print(f"Truncating to {shortest} time points: {', '.join(truncated)}")
        arrays = [array[:shortest] for array in arrays]

    # average each subject's repeats first, when the files are repeated presentations
    if subjects is not None:
        arrays = average_repeats_by_subject(arrays, subjects)

        if len(arrays) < 2:
            raise ValueError(
                f"ISC requires at least two subjects, got {len(arrays)}: "
                f"{sorted(set(subjects))}"
            )

    return compute_leave_one_out_isc(np.stack(arrays, axis = 0).astype(np.float32))

def single_value(df, column, group):
    values = df[column].unique()

    if len(values) != 1:
        raise ValueError(f"{group} has {len(values)} values of {column}: {values}")

    return values[0]

import nibabel as nib
import numpy as np

from nilearn.image import resample_to_img
from scipy import sparse
from scipy.stats import pearsonr

def build_parcel_matrix(labels_3d, n_rois):
    labels = labels_3d.reshape(-1).astype(np.int32)
    valid = (labels > 0) & (labels <= n_rois)

    voxel_idx = np.where(valid)[0]
    parcel_idx = labels[valid] - 1

    counts = np.bincount(parcel_idx, minlength=n_rois).astype(np.float32)

    if np.any(counts == 0):
        missing = np.where(counts == 0)[0] + 1
        raise ValueError(
            f"Atlas has empty parcels after resampling: {missing.tolist()}"
        )

    weights = 1.0/counts[parcel_idx]

    return sparse.csr_matrix(
        (weights, (parcel_idx, voxel_idx)),
        shape=(n_rois, labels.size),
        dtype=np.float32,
    )

def bold_grid_key(img):
    return (
        img.shape[:3],
        tuple(np.round(img.affine.ravel(), 6)),
    )

def get_resampled_parcel_matrix(img, atlas_img, n_rois, cache):
    key = bold_grid_key(img)

    if key not in cache:
        resampled_atlas_img = resample_to_img(
            source_img=atlas_img,
            target_img=img,
            interpolation="nearest",
            force_resample=True,
            copy_header=True,
        )

        labels = resampled_atlas_img.get_fdata().astype(np.int32)
        cache[key] = build_parcel_matrix(labels, n_rois)

    return cache[key]

def extract_parcels(
    bold_file,
    atlas_img,
    n_rois,
    parcel_matrix_cache,
):
    img = nib.load(str(bold_file))

    if img.ndim != 4:
        raise ValueError(
            f"Expected 4D BOLD image, got shape {img.shape}: {bold_file}"
        )

    parcel_matrix = get_resampled_parcel_matrix(
        img=img,
        atlas_img=atlas_img,
        n_rois=n_rois,
        cache=parcel_matrix_cache,
    )

    data = np.asarray(img.dataobj, dtype=np.float32)
    n_tp = data.shape[3]

    flat = data.reshape(-1, n_tp)
    ts = parcel_matrix @ flat
    ts = ts.T.astype(np.float32)

    return ts

def safe_pearsonr(x, y):
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return 0.0

    r, _ = pearsonr(x, y)

    return float(
        np.nan_to_num(
            r,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
    )

def compute_leave_one_out_isc(data):
    n_subjects = data.shape[0]
    n_parcels = data.shape[2]

    isc = np.zeros(
        (n_subjects, n_parcels),
        dtype=np.float32,
    )

    for subject_idx in range(n_subjects):
        other_subjects = np.arange(n_subjects) != subject_idx
        others_mean = data[other_subjects].mean(axis=0)

        for parcel_idx in range(n_parcels):
            isc[subject_idx, parcel_idx] = safe_pearsonr(
                data[subject_idx, :, parcel_idx],
                others_mean[:, parcel_idx],
            )

    return isc.mean(axis=0).astype(np.float32)
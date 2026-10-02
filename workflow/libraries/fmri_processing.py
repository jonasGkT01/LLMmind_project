# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details

import numpy as np
from scipy import sparse
import nibabel as nib
from nilearn.image import resample_to_img

def build_parcel_matrix(labels_3d, n_rois):
    labels = labels_3d.reshape(-1).astype(np.int32)
    valid = (labels > 0) & (labels <= n_rois)

    voxel_idx = np.where(valid)[0]
    parcel_idx = labels[valid] - 1

    counts = np.bincount(parcel_idx, minlength = n_rois).astype(np.float32)

    if np.any(counts == 0):
        missing = np.where(counts == 0)[0] + 1
        raise ValueError(
            f"Atlas has empty parcels after resampling: {missing.tolist()}"
        )

    weights = 1.0/counts[parcel_idx]

    return sparse.csr_matrix(
        (weights, (parcel_idx, voxel_idx)), 
        shape = (n_rois, labels.size), 
        dtype = np.float32
    )

def bold_grid_key(img):
    return (img.shape[:3], tuple(np.round(img.affine.ravel(), 6)),)

# sform codes of an image in scanner or unknown coordinates: an MNI atlas does not apply to it
NATIVE_SFORM_CODES = {0, 1}

def get_resampled_parcel_matrix(img, atlas_img, n_rois, cache):
    # the atlas is matched to the image by world coordinates only, so the image must already
    # be in the atlas space
    if int(img.header["sform_code"]) in NATIVE_SFORM_CODES:
        raise ValueError(
            f"The image has sform_code {int(img.header['sform_code'])} (scanner or "
            "unknown coordinates), so the MNI atlas cannot be applied to it without "
            "registration"
        )

    key = bold_grid_key(img)

    if key not in cache:
        resampled_atlas_img = resample_to_img(
            source_img = atlas_img, 
            target_img = img, 
            interpolation = "nearest", 
            force_resample = True, 
            copy_header = True, 
        )

        labels = resampled_atlas_img.get_fdata().astype(np.int32)
        cache[key] = build_parcel_matrix(labels, n_rois)

    return cache[key]

def extract_parcels(bold_file, atlas_img, n_rois, parcel_matrix_cache,):
    img = nib.load(str(bold_file))

    if img.ndim != 4:
        raise ValueError(f"Expected 4D BOLD image, got shape {img.shape}: {bold_file}")

    parcel_matrix = get_resampled_parcel_matrix(
        img = img, 
        atlas_img = atlas_img, 
        n_rois = n_rois, 
        cache = parcel_matrix_cache, 
    )

    data = np.asarray(img.dataobj, dtype = np.float32)
    n_tp = data.shape[3]

    flat = data.reshape(-1, n_tp)
    ts = parcel_matrix @ flat
    ts = ts.T.astype(np.float32)

    return ts

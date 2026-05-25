import numpy as np
from scipy.stats import pearsonr
from nilearn import datasets, image
import nibabel as nib

# inpouts/outputs from Snakemake
ts_files = list(snakemake.input)
isc_npy = snakemake.output["isc_npy"]
isc_nii = snakemake.output["isc_nii"]

# parameters from Snakemake
n_rois = snakemake.params["n_rois"]
yeo_networks = snakemake.params["yeo_networks"]
atlas_dir = snakemake.params["atlas_dir"]

# load atlas to project ISC back to brain
atlas = datasets.fetch_atlas_schaefer_2018(
    n_rois=n_rois,
    data_dir=atlas_dir,
    yeo_networks=yeo_networks
)
atlas_img = image.load_img(atlas.maps)
atlas_data = atlas_img.get_fdata().astype(int)

# load parcel data
data_list = [np.load(f) for f in ts_files]

# check that all parcels have the same number of timepoints; if not, trim to the minimum number of timepoints across all files
time_lengths = [x.shape[0] for x in data_list]
if len(set(time_lengths)) != 1:
    minimum_time = min(time_lengths)
    data_list = [x[:minimum_time, :] for x in data_list]
#    details = ", ".join(
#        f"{f}: {arr.shape[0]} timepoints"
#        for f, arr in zip(ts_files, data_list)
#    )
#    raise ValueError(f"Mismatched time lengths across input files: {details}")

#T = minimum_time
n_subjects, n_parcels = len(data_list), data_list[0].shape[1]
data = np.stack(data_list, axis=0)

# compute leave-one-out ISC
isc = np.zeros((n_subjects, n_parcels), dtype=np.float32)

for s in range(n_subjects):
    others_mean = data[np.arange(n_subjects) != s].mean(axis=0)
    for p in range(n_parcels):
        # compute Pearson correlation between subject's parcel time series and mean of others, and drop p-value
        # consider r,_ = 1 - pearsonr(data[s, :, p], others_mean[:, p]), instead
        r, _ = pearsonr(data[s, :, p], others_mean[:, p])
        isc[s, p] = np.nan_to_num(r, nan=0.0)

# average leave-one-out ISC across subjects
isc_mean = isc.mean(axis=0)

# save parcel ISC
np.save(isc_npy, isc_mean)

# map average ISC back to brain
out_data = np.zeros_like(atlas_data, dtype=np.float32)

for parcel_idx in range(n_parcels):
    label_value = parcel_idx + 1
    out_data[atlas_data == label_value] = isc_mean[parcel_idx]

# save mean ISC to NIfTI file
out_img = nib.Nifti1Image(out_data, affine=atlas_img.affine, header=atlas_img.header)
nib.save(out_img, isc_nii)

print(f"Saved ISC to {isc_npy} and {isc_nii}")
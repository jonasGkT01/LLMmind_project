import numpy as np
from nilearn import datasets
from nilearn.maskers import NiftiLabelsMasker

# inputs/outputs from Snakemake
bold_file = snakemake.input["bold"]
npy_file = snakemake.output["npy"]

# parameters from Snakemake
n_rois = snakemake.params["n_rois"]
yeo_networks = snakemake.params["yeo_networks"]
atlas_dir = snakemake.params["atlas_dir"]

print(f"Computing parcels from: {bold_file}")

# load atlas to mask data
atlas = datasets.fetch_atlas_schaefer_2018(
    n_rois=n_rois,
    data_dir=atlas_dir,
    yeo_networks=yeo_networks
)

# create masker of input data
masker = NiftiLabelsMasker(
    labels_img=atlas.maps,
    standardize="zscore_sample",
    detrend=False
)

# extract timeseries from parcels
ts = masker.fit_transform(bold_file)

# save parcel timeseries
np.save(npy_file, ts)
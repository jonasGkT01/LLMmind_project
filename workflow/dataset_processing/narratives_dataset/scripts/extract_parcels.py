import numpy as np
from nilearn import datasets
from nilearn.maskers import NiftiLabelsMasker

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--bold_file", required=True)
parser.add_argument("--parcel_ts", required=True)
parser.add_argument("--n_rois", type=int, required=True)
parser.add_argument("--yeo_networks", type=int, required=True)
parser.add_argument("--atlas_dir", type=str, required=True)
args = parser.parse_args()

bold_file = args.bold_file
parcel_ts = args.parcel_ts
n_rois = args.n_rois
yeo_networks = args.yeo_networks
atlas_dir = args.atlas_dir

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
np.save(parcel_ts, ts)
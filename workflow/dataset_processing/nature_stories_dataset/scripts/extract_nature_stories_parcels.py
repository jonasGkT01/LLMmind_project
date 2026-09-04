import argparse
from pathlib import Path
import h5py
import nibabel.freesurfer.io as fsio
import numpy as np
import pandas as pd

from netneurotools.datasets import fetch_schaefer2018
from scipy.sparse import csr_matrix, diags

def load_mapper(path):
    """
    Load the voxel -> fsaverage sparse CSR mapper supplied by
    the Nature Stories dataset.
    """

    with h5py.File(path, "r") as f:
        shape = tuple(
            int(x)
            for x in f["voxel_to_fsaverage_shape"][:]
        )

        mapper = csr_matrix(
            (
                f["voxel_to_fsaverage_data"][:],
                f["voxel_to_fsaverage_indices"][:],
                f["voxel_to_fsaverage_indptr"][:],
            ),
            shape=shape,
        )

    return mapper

def compute_valid_voxel_mask(
    bold_file,
    chunk_size=256,
):
    """
    Return native voxels that are finite for every TR in both
    zRresp and zPresp.

    The HDF datasets are scanned in chunks to avoid loading
    the complete response matrix into memory.
    """

    bold_file = Path(bold_file)

    with h5py.File(bold_file, "r") as f:
        required_keys = ["zRresp", "zPresp",]

        for key in required_keys:
            if key not in f:
                raise KeyError(f"{bold_file} does not contain {key}.")

        n_voxels = f["zRresp"].shape[1]

        if f["zPresp"].shape[1] != n_voxels:
            raise ValueError(f"{bold_file}: zRresp and zPresp have different voxel dimensions.")

        valid_voxels = np.ones(n_voxels, dtype=bool,)

        for key in required_keys:
            dataset = f[key]

            if dataset.ndim != 2:
                raise ValueError(f"{bold_file}:{key} has shape {dataset.shape}; expected time x voxels.")

            for start in range(0, dataset.shape[0], chunk_size,):
                stop = min(start + chunk_size, dataset.shape[0],)

                block = dataset[start:stop, :]

                valid_voxels &= np.isfinite(block).all(axis=0)

    return valid_voxels


def clean_mapper(
    mapper,
    valid_voxels,
):
    """
    Remove invalid native-voxel columns from the mapper and
    renormalize each surviving fsaverage row so that its total
    interpolation weight is unchanged.
    """

    if mapper.shape[1] != len(valid_voxels):
        raise ValueError("Mapper voxel dimension does not match valid-voxel mask.")

    if not np.isfinite(mapper.data).all():
        raise ValueError("Mapper contains non-finite weights.")

    # The supplied voxel->surface mapper is expected to contain
    # interpolation weights, not signed coefficients.
    if np.any(mapper.data < 0):
        raise ValueError("Mapper contains negative weights; row-sum renormalization is not appropriate.")

    original_row_sums = np.asarray(mapper.sum(axis=1)).ravel()

    cleaned_mapper = mapper[:, valid_voxels,].tocsr()

    cleaned_mapper.eliminate_zeros()

    support = (np.diff(cleaned_mapper.indptr) > 0)

    cleaned_row_sums = np.asarray(cleaned_mapper.sum(axis = 1)).ravel()

    if np.any(cleaned_row_sums[support] <= 0):
        raise ValueError("Cleaned mapper contains supported rows with non-positive total weight.")

    scale = np.zeros(cleaned_mapper.shape[0], dtype=np.float64,)

    scale[support] = original_row_sums[support]/cleaned_row_sums[support]

    cleaned_mapper = (diags(scale) @ cleaned_mapper).tocsr()

    cleaned_mapper.eliminate_zeros()

    return cleaned_mapper, support

def decode_name(name):
    if isinstance(name, bytes):
        return name.decode("utf-8")

    return str(name)

def remap_hemisphere(
    vertex_labels,
    annotation_names,
    parcel_offset,
    expected_parcels,
):
    """
    Convert a FreeSurfer annotation into sequential parcel IDs.

    Output value 0 means background/medial wall.
    """

    names = [
        decode_name(name)
        for name in annotation_names
    ]

    parcel_annotation_ids = []

    for annotation_id, name in enumerate(names):
        lower_name = name.lower()

        if (
            "background" in lower_name
            or "medial_wall" in lower_name
            or "medialwall" in lower_name
            or name.lower() == "unknown"
        ):
            continue

        parcel_annotation_ids.append((annotation_id, name))

    if len(parcel_annotation_ids) != expected_parcels:
        raise ValueError(f"Unexpected number of parcels in hemisphere: expected {expected_parcels}, found {len(parcel_annotation_ids)}.")

    remapped = np.zeros(vertex_labels.shape, dtype=np.int32,)

    parcel_names = []

    for local_idx, (annotation_id, name) in enumerate(
        parcel_annotation_ids,
        start=1,
    ):
        global_idx = parcel_offset + local_idx

        remapped[vertex_labels == annotation_id] = global_idx

        parcel_names.append(name)

    return remapped, parcel_names

def load_schaefer_fsaverage(
    n_rois,
    yeo_networks,
    atlas_dir,
):
    """
    Load Schaefer labels on the full-resolution fsaverage mesh.

    Vertex order is:
        left hemisphere followed by right hemisphere.
    """

    atlas = fetch_schaefer2018(
        version="fsaverage",
        data_dir=atlas_dir,
        verbose=1,
    )
    
    scale = f"{n_rois}Parcels{yeo_networks}Networks"
    
    if scale not in atlas:
        raise KeyError(
            f"Schaefer scale {scale} not found. "
            f"Available scales: {list(atlas.keys())}"
        )
    
    annotation = atlas[scale]
    
    if hasattr(annotation, "L"):
        lh_annotation = annotation.L
        rh_annotation = annotation.R
    else:
        lh_annotation = annotation.lh
        rh_annotation = annotation.rh
    
    lh_labels, _, lh_names = fsio.read_annot(str(lh_annotation))
    rh_labels, _, rh_names = fsio.read_annot(str(rh_annotation))

    if n_rois % 2 != 0:
        raise ValueError("Expected an even number of Schaefer parcels.")

    parcels_per_hemisphere = n_rois//2

    lh_remapped, lh_parcel_names = remap_hemisphere(
        lh_labels,
        lh_names,
        parcel_offset=0,
        expected_parcels=parcels_per_hemisphere,
    )

    rh_remapped, rh_parcel_names = remap_hemisphere(
        rh_labels,
        rh_names,
        parcel_offset=parcels_per_hemisphere,
        expected_parcels=parcels_per_hemisphere,
    )

    labels = np.concatenate(
        [
            lh_remapped,
            rh_remapped,
        ]
    )

    parcel_names = lh_parcel_names + rh_parcel_names

    if len(parcel_names) != n_rois:
        raise ValueError(f"Expected {n_rois} parcel names, found {len(parcel_names)}.")

    return labels, parcel_names

def compute_common_support(manifest):
    """
    Compute fsaverage support after excluding native voxels
    containing non-finite BOLD values.

    Also return one fixed valid-voxel mask per subject.
    """

    subject_sources = (
        manifest[
            [
                "subject",
                "bold_file",
                "mapper_file",
            ]
        ].drop_duplicates()
    )

    subject_counts = subject_sources.groupby("subject").size()

    if np.any(subject_counts != 1):
        raise ValueError("Each subject must correspond to exactly one BOLD file and one mapper file.")

    common_support = None
    expected_vertices = None

    valid_voxel_masks = {}
    qc_rows = []

    for row in subject_sources.itertuples(index=False):
        valid_voxels = compute_valid_voxel_mask(row.bold_file)
        mapper = load_mapper(row.mapper_file)
        cleaned_mapper, support = clean_mapper(mapper, valid_voxels,)

        if expected_vertices is None:
            expected_vertices = cleaned_mapper.shape[0]
        elif (cleaned_mapper.shape[0] != expected_vertices):
            raise ValueError("Mapper fsaverage dimensions differ across subjects.")

        if common_support is None:
            common_support = support.copy()
        else:
            common_support &= support

        valid_voxel_masks[row.subject] = valid_voxels

        qc_rows.append(
            {
                "subject": row.subject,
                "total_voxels": len(
                    valid_voxels
                ),
                "valid_voxels": int(
                    valid_voxels.sum()
                ),
                "invalid_voxels": int(
                    (~valid_voxels).sum()
                ),
                "invalid_fraction": float(
                    (~valid_voxels).mean()
                ),
            }
        )

    if common_support is None:
        raise ValueError("No subjects were found.")

    return (common_support, valid_voxel_masks, pd.DataFrame(qc_rows),)

def build_parcel_averager(
    vertex_labels,
    common_support,
    n_rois,
):
    """
    Build a sparse matrix:

        parcels x fsaverage_vertices

    Each parcel contains equal averaging weights over the
    vertices that:
      1. belong to the parcel, and
      2. are mapped in every subject.
    """

    rows = []
    columns = []
    values = []

    coverage_rows = []

    for parcel_id in range(1, n_rois + 1):
        all_vertices = np.flatnonzero(vertex_labels == parcel_id)

        common_vertices = np.flatnonzero((vertex_labels == parcel_id) & common_support)

        n_total = len(all_vertices)
        n_common = len(common_vertices)

        if n_total == 0:
            raise ValueError(f"Schaefer parcel {parcel_id} contains no vertices.")

        if n_common == 0:
            raise ValueError(f"Schaefer parcel {parcel_id} has no vertices shared by all subjects.")

        weight = 1.0 / n_common

        rows.extend([parcel_id - 1]*n_common)
        columns.extend(common_vertices.tolist())
        values.extend([weight]*n_common)

        coverage_rows.append(
            {
                "parcel": parcel_id,
                "total_vertices": n_total,
                "common_vertices": n_common,
                "coverage": n_common / n_total,
            }
        )

    averager = csr_matrix((values, (rows, columns),), shape=(n_rois, len(vertex_labels),), dtype=np.float64,)

    coverage = pd.DataFrame(coverage_rows)

    return averager, coverage

def extract_subject(
    subject_df,
    parcel_averager,
    n_rois,
    valid_voxels,
):
    """
    Process all stories for one subject.

    The expensive voxel->parcel projection is composed once
    and then reused for all 11 stories.
    """

    subjects = subject_df["subject"].unique()

    if len(subjects) != 1:
        raise ValueError("extract_subject received multiple subjects.")

    subject = subjects[0]

    bold_files = subject_df["bold_file"].unique()
    mapper_files = subject_df["mapper_file"].unique()

    if len(bold_files) != 1:
        raise ValueError(f"{subject} has multiple BOLD files: {bold_files}")

    if len(mapper_files) != 1:
        raise ValueError(f"{subject} has multiple mapper files: {mapper_files}")

    bold_file = Path(bold_files[0])
    mapper_file = Path(mapper_files[0])

    if not bold_file.exists():
        raise FileNotFoundError(f"Missing BOLD file: {bold_file}")

    if not mapper_file.exists():
        raise FileNotFoundError(f"Missing mapper file: {mapper_file}")

    print(f"Preparing voxel-to-parcel projection for {subject}")

    mapper = load_mapper(mapper_file)

    mapper, subject_support = clean_mapper(mapper, valid_voxels,)

    if parcel_averager.shape[1] != mapper.shape[0]:
        raise ValueError(f"Parcel averager expects {parcel_averager.shape[1]} fsaverage vertices, but {subject} mapper contains {mapper.shape[0]}.")

    # This is mathematically:
    #
    # native voxels
    #   -> fsaverage vertices
    #   -> common-support Schaefer means
    #
    # but avoids materializing T x 327684 in memory.
    voxel_to_parcel = (parcel_averager @ mapper).tocsr()

    with h5py.File(bold_file, "r") as bold_hdf:
        for row in subject_df.itertuples(index=False):
            if row.response_key not in bold_hdf:
                raise KeyError(f"{bold_file} does not contain {row.response_key}.")

            dataset = bold_hdf[row.response_key]

            if dataset.ndim != 2:
                raise ValueError(f"{bold_file}:{row.response_key} has shape {dataset.shape}; expected time x voxels.")

            if dataset.shape[1] != len(valid_voxels):
                raise ValueError(f"{subject}: BOLD contains {dataset.shape[1]} voxels, but the valid-voxel mask expects {len(valid_voxels)}.")

            start = int(row.onset)
            length = int(row.length)
            stop = start + length

            if stop > dataset.shape[0]:
                raise ValueError(f"{subject}/{row.story}: requested TRs [{start}:{stop}], but {row.response_key} contains only {dataset.shape[0]} TRs.")

            response = dataset[start:stop, valid_voxels]

            if not np.isfinite(response).all():
                raise ValueError(f"{subject}/{row.story}: non-finite values remain after valid-voxel masking.")

            if response.shape[0] != length:
                raise ValueError(f"{subject}/{row.story}: expected {length} TRs, obtained {response.shape[0]}.")

            print(f"{subject}: {row.story} {response.shape} -> ({length}, {n_rois})")

            parcel_ts = (voxel_to_parcel @ response.T).T

            if not np.isfinite(parcel_ts).all():
                raise ValueError(f"{subject}/{row.story}: non-finite parcel values produced.")

            if parcel_ts.shape != (length, n_rois,):
                raise ValueError(f"Unexpected parcel shape for {subject}/{row.story}: {parcel_ts.shape}")

            output_path = Path(row.parcel_ts)

            output_path.parent.mkdir(parents=True, exist_ok=True,)

            np.save(output_path, parcel_ts.astype(np.float32),)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True,)
    parser.add_argument("--n_rois", type=int, required=True,)
    parser.add_argument("--yeo_networks", type=int, required=True,)
    parser.add_argument("--atlas_dir", required=True,)
    parser.add_argument("--common_support_output", required=True,)
    parser.add_argument("--coverage_output", required=True,)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t",)

    required_columns = {"subject", "story", "bold_file", "mapper_file", "response_key", "onset", "length", "parcel_ts",}

    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(f"Manifest is missing columns: {sorted(missing_columns)}")

    print(f"Computing fsaverage support shared across {manifest['subject'].nunique()} subjects")

    common_support, valid_voxel_masks, voxel_qc = compute_common_support(manifest)

    print(f"Common fsaverage support: {common_support.sum()} / {len(common_support)} ({100 * common_support.mean():.2f}%)")

    common_support_output = Path(args.common_support_output)
    common_support_output.parent.mkdir(parents=True, exist_ok=True,)

    np.save(common_support_output, common_support,)

    voxel_qc_output = common_support_output.parent / "valid_voxel_counts.tsv"

    voxel_qc.to_csv(
        voxel_qc_output,
        sep="\t",
        index=False,
    )

    print("Native-voxel QC:")
    print(voxel_qc.to_string(index=False))

    vertex_labels, parcel_names = load_schaefer_fsaverage(
        n_rois=args.n_rois,
        yeo_networks=args.yeo_networks,
        atlas_dir=args.atlas_dir,
    )

    if len(vertex_labels) != len(common_support):
        raise ValueError(f"Schaefer fsaverage vertex count ({len(vertex_labels)}) does not match mapper vertex count ({len(common_support)}).")

    parcel_averager, coverage = build_parcel_averager(
        vertex_labels=vertex_labels,
        common_support=common_support,
        n_rois=args.n_rois,
    )

    coverage.insert(1, "parcel_name", parcel_names,)

    coverage_output = Path(args.coverage_output)

    coverage_output.parent.mkdir(parents=True, exist_ok=True,)

    coverage.to_csv(
        coverage_output,
        sep="\t",
        index=False,
    )

    print("Schaefer common-support coverage:")
    print(coverage["coverage"].describe())

    for subject, subject_df in (manifest.groupby("subject", sort=False,)):
        extract_subject(
            subject_df=subject_df,
            parcel_averager=parcel_averager,
            n_rois=args.n_rois,
            valid_voxels=valid_voxel_masks[subject],
        )

if __name__ == "__main__":
    main()
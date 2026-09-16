import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from nilearn import datasets, image
from libraries.fmri_processing import extract_parcels

def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--output_root',required=True); p.add_argument('--n_rois',type=int,required=True); p.add_argument('--yeo_networks',type=int,required=True); p.add_argument('--atlas_dir',required=True); a=p.parse_args()
    df=pd.read_csv(a.manifest,sep='\t'); samples=df[['subject','stimulus_id','output_bold']].drop_duplicates().sort_values(['stimulus_id','subject'])
    atlas=datasets.fetch_atlas_schaefer_2018(n_rois=a.n_rois,data_dir=a.atlas_dir,yeo_networks=a.yeo_networks); atlas_img=image.load_img(atlas.maps); cache={}; root=Path(a.output_root)
    for r in samples.itertuples(index=False):
        bold=Path(r.output_bold); out=root/'parcels'/f'task-{r.stimulus_id}'/f'sub-{int(r.subject):02d}_task-{r.stimulus_id}_parcel_ts.npy'; out.parent.mkdir(parents=True,exist_ok=True)
        if not bold.exists(): raise FileNotFoundError(bold)
        ts=extract_parcels(bold_file=bold,atlas_img=atlas_img,n_rois=a.n_rois,parcel_matrix_cache=cache); np.save(out,ts.astype(np.float32)); print(out,ts.shape)
if __name__=='__main__': main()

import argparse
from pathlib import Path
import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image
from libraries.fmri_processing import compute_leave_one_out_isc

def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--parcel_root',required=True); p.add_argument('--isc_root',required=True); p.add_argument('--n_rois',type=int,required=True); p.add_argument('--yeo_networks',type=int,required=True); p.add_argument('--atlas_dir',required=True); a=p.parse_args()
    df=pd.read_csv(a.manifest,sep='\t')[['subject','stimulus_id']].drop_duplicates().sort_values(['stimulus_id','subject'])
    atlas=datasets.fetch_atlas_schaefer_2018(n_rois=a.n_rois,data_dir=a.atlas_dir,yeo_networks=a.yeo_networks); ai=image.load_img(atlas.maps); ad=ai.get_fdata().astype(int)
    proot=Path(a.parcel_root); iroot=Path(a.isc_root); iroot.mkdir(parents=True,exist_ok=True)
    for stim,g in df.groupby('stimulus_id',sort=False):
        arrays=[]
        for r in g.itertuples(index=False):
            f=proot/f'task-{stim}'/f'sub-{int(r.subject):02d}_task-{stim}_parcel_ts.npy'; arr=np.load(f)
            if arr.ndim!=2 or arr.shape[1]!=a.n_rois: raise ValueError(f'Bad parcel shape {arr.shape}: {f}')
            arrays.append(arr)
        if len(arrays)<2: raise ValueError(f'Need >=2 subjects for {stim}')
        lens=[x.shape[0] for x in arrays]
        if len(set(lens))!=1:
            m=min(lens); arrays=[x[:m] for x in arrays]
        isc=compute_leave_one_out_isc(np.stack(arrays,axis=0)); npy=iroot/f'task-{stim}_isc_mean.npy'; nii=iroot/f'task-{stim}_isc_mean.nii.gz'; np.save(npy,isc)
        vol=np.zeros_like(ad,dtype=np.float32)
        for j,v in enumerate(isc): vol[ad==j+1]=v
        nib.save(nib.Nifti1Image(vol,ai.affine,header=ai.header.copy()),str(nii)); print(stim,len(arrays),arrays[0].shape[0])
if __name__=='__main__': main()

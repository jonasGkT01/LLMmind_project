import argparse, tempfile
from pathlib import Path
import nibabel as nib
import numpy as np
import pandas as pd
from nsdcode.nsd_mapdata import NSDmapdata

def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--dataset_dir',required=True); p.add_argument('--interpolation',default='cubic'); a=p.parse_args()
    df=pd.read_csv(a.manifest,sep='\t'); required={'subject','stimulus_id','repetition','source_bold','start_vol','end_vol','output_bold'}
    if required-set(df): raise ValueError(f'Manifest missing {sorted(required-set(df))}')
    mapper=NSDmapdata(a.dataset_dir)
    for (sub,stim),g in df.groupby(['subject','stimulus_id'],sort=False):
        g=g.sort_values('repetition'); outputs=g.output_bold.astype(str).unique()
        if len(outputs)!=1: raise ValueError(f'Multiple outputs for {sub} {stim}')
        ref=None; chunks=[]
        for r in g.itertuples(index=False):
            img=nib.load(r.source_bold); start=int(r.start_vol); end=int(r.end_vol)
            if img.ndim!=4 or start<0 or end>img.shape[3] or end<=start: raise ValueError(f'Bad crop for {r.source_bold}: {start}:{end}')
            if ref is None: ref=img
            else:
                if ref.shape[:3]!=img.shape[:3] or not np.allclose(ref.affine,img.affine,atol=1e-5): raise ValueError(f'Functional geometry changed within subj{sub:02d}')
            chunks.append(np.asarray(img.dataobj[...,start:end],dtype=np.float32))
        data=np.concatenate(chunks,axis=3); out=Path(outputs[0]); out.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='nsd_map_') as td:
            native=Path(td)/f'sub-{int(sub):02d}_task-{stim}_func1pt8.nii.gz'
            ni=nib.Nifti1Image(data,ref.affine,header=ref.header.copy()); ni.header.set_data_dtype(np.float32); ni.header.set_data_shape(data.shape); nib.save(ni,str(native))
            mapper.fit(int(sub),'func1pt8','MNI',str(native),interptype=a.interpolation,badval=0,outputfile=str(out))
        mapped=nib.load(str(out))
        if mapped.ndim!=4 or mapped.shape[3]!=data.shape[3]: raise ValueError(f'Unexpected mapped output {out}: {mapped.shape}')
        print(f'{stim} subj{sub:02d}: {data.shape[3]} volumes -> MNI')
if __name__=='__main__': main()

import argparse
from pathlib import Path
import h5py
import numpy as np
import pandas as pd
from PIL import Image

def rgb(a):
    a=np.asarray(a)
    if a.ndim!=3: raise ValueError(f'Expected 3D image, got {a.shape}')
    if a.shape[-1]==3: x=a
    elif a.shape[0]==3: x=np.moveaxis(a,0,-1)
    else: raise ValueError(f'Cannot identify RGB axis: {a.shape}')
    if x.dtype!=np.uint8:
        if np.issubdtype(x.dtype,np.floating) and x.max()<=1: x=x*255
        x=np.clip(x,0,255).astype(np.uint8)
    return x

def main():
    p=argparse.ArgumentParser(); p.add_argument('--stimulus_manifest',required=True); p.add_argument('--stimuli_hdf5',required=True); p.add_argument('--output_dir',required=True); a=p.parse_args()
    df=pd.read_csv(a.stimulus_manifest,sep='\t'); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    with h5py.File(a.stimuli_hdf5,'r') as h:
        b=h['imgBrick']; shape=b.shape
        for r in df.itertuples(index=False):
            idx=int(r.hdf5_index)
            arr=b[idx] if shape[0]>10000 else b[...,idx] if shape[-1]>10000 else None
            if arr is None: raise ValueError(f'Cannot identify image axis: {shape}')
            Image.fromarray(rgb(arr)).save(out/f'{r.stimulus_id}.png')
    print(f'Exported {len(df)} images')
if __name__=='__main__': main()

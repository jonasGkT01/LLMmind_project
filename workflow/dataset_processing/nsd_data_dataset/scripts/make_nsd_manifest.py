import argparse
import re
import json
import math

from collections import defaultdict
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

DESIGN_RE = re.compile(r"design_session(?P<session>\d+)_run(?P<run>\d+)\.tsv$")
BOLD_RE = re.compile(r"timeseries_session(?P<session>\d+)_run(?P<run>\d+)\.nii\.gz$")

def sid(x): return f"nsd-{int(x):05d}"

def discover(dataset_dir, subject, functional_space):
    root=dataset_dir/'nsddata_timeseries'/'ppdata'/f'subj{subject:02d}'/functional_space
    ddir=root/'design'; bdir=root/'timeseries'

    if not ddir.is_dir():
        raise FileNotFoundError(ddir)
    
    if not bdir.is_dir():
        raise FileNotFoundError(bdir)

    ds={}
    bs={}

    for p in sorted(ddir.glob('design_session*_run*.tsv')):
        m=DESIGN_RE.match(p.name)

        if m:
            ds[(int(m['session']),int(m['run']))]=p

    for p in sorted(bdir.glob('timeseries_session*_run*.nii.gz')):
        m=BOLD_RE.match(p.name)

        if m:
            bs[(int(m['session']),int(m['run']))]=p

    keys=sorted(set(ds)&set(bs))

    if not keys:
        raise ValueError(f'No matching design/BOLD runs for subj{subject:02d}')
    
    return [(s,r,ds[(s,r)],bs[(s,r)]) for s,r in keys]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_dir', required=True); parser.add_argument('--subjects', nargs='+', type=int, required=True)
    parser.add_argument('--functional_space', default='func1pt8mm'); parser.add_argument('--tr', type=float, required=True)
    parser.add_argument('--event_duration_s', type=float, required=True); parser.add_argument('--onset_shift_volumes', type=int, default=0)
    parser.add_argument('--min_repetitions_per_subject', type=int, required=True); parser.add_argument('--repetitions_to_use', type=int, required=True)
    parser.add_argument('--output_manifest', required=True); parser.add_argument('--output_stimulus_manifest', required=True)
    parser.add_argument('--output_excluded_stimuli', required=True)
    args = parser.parse_args()

    root=Path(args.dataset_dir)

    if args.repetitions_to_use<1 or args.min_repetitions_per_subject<1 or args.repetitions_to_use>args.min_repetitions_per_subject:
        raise ValueError('Invalid repetition settings')
    
    n_vols=int(math.ceil(args.event_duration_s/args.tr))

    occ_by_sub={}
    counts_by_sub={}
    qc=[]

    for sub in args.subjects:
        occ=defaultdict(list)

        for ses,run,dpath,bpath in discover(root,sub,args.functional_space):
            design=np.asarray(np.loadtxt(dpath,dtype=np.int64,ndmin=1)).reshape(-1)
            img=nib.load(str(bpath))

            if img.ndim!=4:
                raise ValueError(f'Expected 4D BOLD: {bpath} {img.shape}')
            
            if img.shape[3] not in {len(design),len(design)+1}:
                raise ValueError(f'Unexpected design/BOLD lengths for {bpath}: {len(design)} vs {img.shape[3]}')

            nz=np.flatnonzero(design>0)

            for onset in nz:
                image_id=int(design[onset])
                start=int(onset) + args.onset_shift_volumes
                end=start + n_vols

                if start<0 or end>img.shape[3]:
                    raise ValueError(f'Crop [{start}:{end}] outside {bpath}')

                occ[image_id].append(dict(subject=sub, session=ses, run=run, nsd_73k_id=image_id, stimulus_id=sid(image_id), onset_vol=int(onset), start_vol=start, end_vol=end, n_vols=n_vols, source_design=str(dpath.resolve()), source_bold=str(bpath.resolve())))

            qc.append(dict(subject=sub,session=ses,run=run,n_design_volumes=len(design),n_bold_volumes=img.shape[3],n_stimulus_onsets=len(nz)))

        for image_id in occ:
            occ[image_id].sort(key=lambda x:(x['session'],x['run'],x['onset_vol']))
        
        occ_by_sub[sub]=occ
        counts_by_sub[sub]={k:len(v) for k,v in occ.items()}

    sets=[{
            k for k,v in counts_by_sub[s].items() if v>=args.min_repetitions_per_subject
        }
        for s in args.subjects
    ]

    keep=sorted(set.intersection(*sets)) if sets else []

    if not keep:
        raise ValueError('No image satisfies repetition criterion in all subjects')
    
    out_parent=Path(args.output_manifest).parent.parent
    rows=[]

    for sub in args.subjects:
        for image_id in keep:
            selected=occ_by_sub[sub][image_id][:args.repetitions_to_use]
            output=out_parent/'single_stimulus_bold_mni'/f'task-{sid(image_id)}'/f'sub-{sub:02d}_task-{sid(image_id)}_bold.nii.gz'

            for rep,row in enumerate(selected,1):
                r=dict(row)
                r['repetition']=rep
                r['output_bold']=str(output)
                rows.append(r)

    manifest=pd.DataFrame(rows).sort_values(['nsd_73k_id','subject','repetition'])
    sm=pd.DataFrame([dict(
            stimulus_id=sid(i),
            nsd_73k_id=i,
            hdf5_index=i - 1,
            n_subjects=len(args.subjects),
            repetitions_per_subject=args.repetitions_to_use,
            volumes_per_repetition=n_vols,
            volumes_per_subject_stimulus=n_vols*args.repetitions_to_use) 
        for i in keep])
    mp=Path(args.output_manifest); sp=Path(args.output_stimulus_manifest); ep=Path(args.output_excluded_stimuli)

    for p in (mp,sp,ep):
        p.parent.mkdir(parents=True, exist_ok=True)

    manifest.to_csv(mp, sep='\t', index=False)
    sm.to_csv(sp, sep='\t', index=False)
    ep.write_text('')

    pd.DataFrame(qc).to_csv(mp.parent/'run_length_qc.tsv', sep='\t', index=False)

    meta=dict(subjects=args.subjects,
              functional_space=args.functional_space,
              tr=args.tr,
              event_duration_s=args.event_duration_s,
              onset_shift_volumes=args.onset_shift_volumes,
              n_volumes_per_repetition=n_vols,
              min_repetitions_per_subject=args.min_repetitions_per_subject,
              repetitions_to_use=args.repetitions_to_use,
              n_retained_stimuli=len(keep),
              n_manifest_rows=len(manifest))
    
    (mp.parent/'manifest_metadata.json').write_text(json.dumps(meta, indent=2, sort_keys=True))

    print(f'Retained {len(keep)} stimuli; wrote {len(manifest)} occurrence rows')
    
if __name__=='__main__': main()

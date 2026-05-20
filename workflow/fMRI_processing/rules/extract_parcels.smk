rule extract_parcels:
    input:
        bold=lambda wc: config["bold_glob_pattern"].format(
            subject=wc.subject,
            task=wc.task,
            run_tag="" if wc.run_label == "norun" else f"_{wc.run_label}",
            space=wc.space,
            resolution=wc.resolution,
            descriptor=wc.descriptor,
        )
    output:
        npy=f"results/parcels/{{task}}/sub-{{subject}}_task-{{task}}_{{run_label}}_space-{{space}}_res-{{resolution}}_desc-{{descriptor}}_parcel_ts.npy"
    params:
        n_rois=config["atlas"]["n_rois"],
        yeo_networks=config["atlas"]["yeo_networks"],
        atlas_dir=config["atlas"]["atlas_dir"]
    conda:
        "../envs/extract_parcels_environment.yaml"
    script:
        "../scripts/extract_parcels.py"
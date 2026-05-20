from nilearn import plotting

# inputs/outputs from Snakemake
isc_nii = snakemake.input["isc_nii"]
png_file = snakemake.output["png"]

task = snakemake.wildcards["task"]

print(f"Plotting ISC map: {isc_nii}")

# create and save static PNG plot of ISC map
display = plotting.plot_stat_map(
    isc_nii,
    title=f"Mean ISC - Task '{task}'",
    display_mode="ortho",
    cut_coords=(0, -20, 40),
    colorbar=True
)
display.savefig(png_file)
display.close()
# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

from nilearn import plotting

def main():
    parser = argparse.ArgumentParser(description = "Draw a subject's T1w registered to MNI, with the template's edges on top")
    parser.add_argument("--warped_t1", 
                        required = True, 
                        help = "The subject's T1w resampled into template space")
    parser.add_argument("--template", 
                        required = True)
    parser.add_argument("--subject", 
                        required = True)
    parser.add_argument("--output", 
                        required = True)
    args = parser.parse_args()

    # draw the registered T1w and the template edges, and save the plot as a png file
    display = plotting.plot_anat(
        args.warped_t1, 
        display_mode = "ortho", 
        title = f"sub-{args.subject} T1w in MNI152NLin6Asym, template edges in red", 
        draw_cross = False, 
    )
    display.add_edges(args.template, color = "r")
    display.savefig(args.output, dpi = 100)
    display.close()

if __name__ == "__main__":
    main()

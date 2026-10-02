# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-01, see docs/changelog/developers/ for details

import argparse

from huggingface_hub import snapshot_download

def main():
    parser = argparse.ArgumentParser(description = "Download a pretrained model repository from the Hugging Face Hub")
    parser.add_argument("--model_name",
                        required = True,
                        help = "Hugging Face repository ID of the model")
    parser.add_argument("--save_dir",
                        required = True,
                        help = "Directory to download the repository into")
    args = parser.parse_args()

    snapshot_download(
        repo_id = args.model_name,
        local_dir = args.save_dir,
    )

if __name__ == "__main__":
    main()

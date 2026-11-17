import sys
from huggingface_hub import HfApi, hf_hub_download
import config

REPO = "Lichess/standard-chess-games"


def files_list(year, month):
    folder = f"data/year={year}/month={month:02d}"
    elements = HfApi().list_repo_tree(REPO, path_in_repo=folder, repo_type="dataset")
    return sorted(e.path for e in elements if e.path.endswith(".parquet"))


def main():
    test_mode = "test" in sys.argv  

    for year, month in config.MONTHS:
        files = files_list(year, month)
        print(f"{year}-{month:02d}: {len(files)} files")

        if test_mode:
            files = files[:1]

        for path in files:
            print("  downloading", path)
            hf_hub_download(
                repo_id=REPO,
                repo_type="dataset",
                filename=path,
                local_dir=config.RAW_DIR,
            )

        if test_mode:
            break


if __name__ == "__main__":
    main()

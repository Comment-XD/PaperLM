"""Download every extracted TEI XML object to a local folder."""

import sys
from pathlib import Path

from paperlm.config import get_settings
from paperlm.storage import download, list_keys


def main() -> None:
    """Download all .xml objects under the extracted prefix into <folder>."""
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.download_extracted <folder>")

    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    count = 0
    for key in list_keys(settings.extracted_prefix):
        if not key.endswith(".xml"):
            continue
        destination = folder / Path(key).name
        download(key, destination)
        print(f"downloaded {key} -> {destination}")
        count += 1

    print(f"Downloaded {count} XML file(s) to {folder}")


if __name__ == "__main__":
    main()

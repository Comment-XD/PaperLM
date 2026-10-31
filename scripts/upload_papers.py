"""Upload every *.pdf in a local folder to the raw prefix in S3."""

import sys
from pathlib import Path

from paperlm.config import get_settings
from paperlm.storage import upload_bytes


def main() -> None:
    """Upload all PDFs under the folder given as the first CLI argument."""
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.upload_papers <folder>")

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        sys.exit(f"not a directory: {folder}")

    settings = get_settings()
    count = 0
    for pdf in sorted(folder.glob("*.pdf")):
        key = f"{settings.raw_prefix}{pdf.name}"
        upload_bytes(key, pdf.read_bytes())
        print(f"uploaded {key}")
        count += 1

    print(f"Uploaded {count} PDF(s).")


if __name__ == "__main__":
    main()

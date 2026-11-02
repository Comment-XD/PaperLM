import time
import requests
from paperlm.storage import upload_bytes


def arxiv_extractor(arxiv_paper_ids_path, sample: int = 1):
    """Download arXiv PDFs and upload each one to our S3 bucket.

    Args:
        arxiv_paper_ids_path: path to a file with one arXiv id per line.
        sample: maximum number of papers to download.
    """
    with open(arxiv_paper_ids_path, "r") as arxiv_paper_ids:
        for count, line in enumerate(arxiv_paper_ids):
            if count >= sample:
                break

            arxiv_id = line.strip()
            if not arxiv_id:
                continue

            try:
                print(f"Reading Arxiv Paper: {arxiv_id}")
                response = requests.get(
                    f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    timeout=60,
                )
                response.raise_for_status()

                upload_bytes(f"raw/{arxiv_id}.pdf", response.content)
            except requests.RequestException as error:
                print(f"Failed to download {arxiv_id}: {error}")
            except Exception as error:
                print(f"Failed to upload {arxiv_id}: {error}")
            finally:
                time.sleep(3)

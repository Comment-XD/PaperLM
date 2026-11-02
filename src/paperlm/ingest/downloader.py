from paperlm.ingest.extractor import arxiv_extractor
    
if __name__ == "__main__":
    arxiv_extractor('arxiv_paper_ids.txt', sample=10000)
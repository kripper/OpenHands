import re
from fuzzywuzzy import fuzz
import arxiv
import os
def clean_filename(filename: str):
    # remove special characters
    filename = re.sub(r'[^\w\s-]', '', filename)
    # remove leading and trailing whitespace
    filename = filename.strip()
    return filename
def download_arxiv_pdf(query: str):
    """
    Searches arXiv for papers matching the given query and saves the pdf to the current directory.

    Args:
        query: The search query.
        max_results: The maximum number of results to return.

    Returns:
        A list of arXiv results.
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results= 10,  # Increase initial results for better fuzzy matching
        sort_by=arxiv.SortCriterion.Relevance # not working as expected
    )
    results = list(client.results(search))

    # Use fuzzy matching to find relevant results
    relevant_results = []
    for result in results:
        score = fuzz.partial_ratio(query.lower(), result.title.lower())
        if score >= 80:  # Adjust the threshold as needed
            relevant_results.append((result, score))

    # Sort by fuzzy matching score and return top results
    relevant_results.sort(key=lambda x: x[1], reverse=True)
    if len(relevant_results) > 0:
        relevant_result = relevant_results[0][0]
        print(relevant_result.download_pdf(filename=f"{clean_filename(relevant_result.title)}.pdf"))
        print(f"Downloaded to {relevant_result.title}.pdf")
    else:
        print("No relevant results found")
    

if __name__ == "__main__":  
    query = "OpenHands: An Open Platform for AI Software Developers as Generalist Agents"
    download_arxiv_pdf(query)


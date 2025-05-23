# -*- coding: utf-8 -*-
"""NLP _GRAD_ASSIGNMENT.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1IV4JGQYrQQVgT8RiYi0m7jfWXqU2VyFc
"""

pip install -qq pandas faiss-cpu sentence-transformers

import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

df = pd.read_csv("collaborative_book_metadata.csv")


def create_doc(row):
    return f"Title: {row['title']}\nAuthor: {row['name']}\nGenre: {row['genre']}\nDescription: {row['description']}"

documents = df.apply(create_doc, axis=1).tolist()


metadata = df[['title', 'name', 'genre', 'description']].to_dict(orient='records')


model = SentenceTransformer('all-mpnet-base-v2')
# model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(documents, show_progress_bar=True)

dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(np.array(embeddings))


faiss.write_index(index, "book_metadata_faiss.index")


index = faiss.read_index("book_metadata_faiss.index")


def search_faiss(query, top_k=5):

    query_vector = model.encode([query])


    distances, indices = index.search(np.array(query_vector), top_k)


    results = []
    for idx in indices[0]:
        result = metadata[idx]
        result['score'] = float(distances[0][list(indices[0]).index(idx)])
        results.append(result)
    return results

def search_faiss_and_keywords(query, top_k=5):

    query_vector = model.encode([query])
    distances, indices = index.search(np.array(query_vector), top_k)


    semantic_results = []
    for idx in indices[0]:
        result = metadata[idx].copy()
        result['score'] = float(distances[0][list(indices[0]).index(idx)])
        result['source'] = 'semantic'
        semantic_results.append(result)


    keyword_results = []
    query_lower = query.lower()
    for i, doc in enumerate(metadata):

        text = doc.get('text', '').lower()
        if query_lower in text:
            result = doc.copy()
            result['score'] = 1.0  
            result['source'] = 'keyword'
            keyword_results.append(result)


    seen_ids = set()
    combined_results = []

    for res in semantic_results + keyword_results:
        doc_id = res.get('id', res.get('text'))  # use 'id' if available
        if doc_id not in seen_ids:
            combined_results.append(res)
            seen_ids.add(doc_id)
        if len(combined_results) >= top_k:
            break

    return combined_results





import math
from typing import List, Dict, Set, Tuple, Callable

def precision_at_k(retrieved: List[str], relevant: Set[str], k: int = 5) -> float:
    """
    calculating precision at k
    """
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc in top_k if doc in relevant)
    return hits / k

def dcg_at_k(retrieved: List[str], relevant: Set[str], k: int = 5) -> float:
    """
    calculating dcg at k
    """
    dcg = 0.0
    for i, doc in enumerate(retrieved[:k], start=1):
        rel = 1 if doc in relevant else 0
        dcg += rel / math.log2(i + 1)
    return dcg

def idcg_at_k(n_rel: int, k: int = 5) -> float:
    """
    idcg at k
    """
    idcg = 0.0
    for i in range(1, min(n_rel, k) + 1):
        idcg += 1 / math.log2(i + 1)
    return idcg

def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int = 5) -> float:
    """
    ndcg @ k
    """
    dcg = dcg_at_k(retrieved, relevant, k)
    idcg = idcg_at_k(len(relevant), k)
    return (dcg / idcg) if idcg > 0 else 0.0

def evaluate(
    queries: List[str],
    ground_truth: Dict[str, Set[str]],
    search_fn: Callable[[str, int], List[Dict]],
    top_k: int = 5
) -> Tuple[float, float]:

    precisions = []
    ndcgs = []

    for query in queries:
        results = search_fn(query, top_k)
        retrieved_titles = [res['title'] for res in results]
        relevant_set = ground_truth.get(query, set())

        p = precision_at_k(retrieved_titles, relevant_set, top_k)
        n = ndcg_at_k(retrieved_titles, relevant_set, top_k)

        precisions.append(p)
        ndcgs.append(n)

        print(f"Query: {query!r}")
        print(f"  Precision@{top_k}: {p:.3f}")
        print(f"  nDCG@{top_k}:      {n:.3f}\n")

    mean_p = sum(precisions) / len(precisions) if precisions else 0.0
    mean_n = sum(ndcgs) / len(ndcgs) if ndcgs else 0.0

    print(f"Mean Precision@{top_k}: {mean_p:.3f}")
    print(f"Mean nDCG@{top_k}:      {mean_n:.3f}")

    return mean_p, mean_n


if __name__ == "__main__":
    query = "searching for woman realted books"
    results = search_faiss_and_keywords(query)


    for i, res in enumerate(results):
        print(f"\nResult {i+1} (Score: {res['score']:.2f})")
        print(f"Title: {res['title']}")
        print(f"Author: {res['name']}")
        print(f"Genre: {res['genre']}")
        print(f"Description: {res['description'][:200]}...")

    # 1) ground truth:
    ground_truth = {
        "Sharp Objects": {
            "Quantum Computation and Quantum Information",
            "Modern Quantum Mechanics",
            "Sharp Objects",
        },
        "Saga": {
            "Saga Vol 1 Saga 1",
            "Saga Vol 2 Saga 2",
            "Saga Vol 3 Saga 3"
        },
    }
    queries = list(ground_truth.keys())

    evaluate(queries, ground_truth, search_faiss_and_keywords, top_k=5)

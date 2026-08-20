"""
Lightweight RAG (Retrieval-Augmented Generation) module.

- extract_text_from_pdf(): pulls text out of an uploaded PDF (pypdf)
- chunk_text(): splits text into overlapping chunks for retrieval
- retrieve_relevant_chunks(): TF-IDF + cosine similarity search over a
  user's stored document chunks (no external LLM/API key needed - this
  is classic sparse-vector RAG, fully local).

This keeps the whole pipeline offline/local: no OpenAI/Anthropic key
required for the RAG step itself. If you want generative (abstractive)
answers instead of extractive snippets, swap `build_rag_answer()`'s
tail-end to call an LLM API with the retrieved chunks as context.
"""

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        text_parts.append(extracted)
    return "\n".join(text_parts)


def chunk_text(text, chunk_size=800, overlap=150):
    """Split text into overlapping character chunks (simple, robust, model-free)."""
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        if end == length:
            break
        start = end - overlap  # slide window with overlap
    return chunks


def retrieve_relevant_chunks(query, chunk_texts, top_k=3, min_similarity=0.08):
    """
    Return the top_k chunk texts most relevant to `query`, using TF-IDF
    cosine similarity. Chunks below `min_similarity` are dropped.
    """
    if not chunk_texts:
        return []

    corpus = chunk_texts + [query]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # e.g. empty vocabulary after stop-word removal
        return []

    query_vec = tfidf_matrix[-1]
    doc_vecs = tfidf_matrix[:-1]
    similarities = cosine_similarity(query_vec, doc_vecs).flatten()

    ranked = sorted(zip(chunk_texts, similarities), key=lambda x: x[1], reverse=True)
    results = [(chunk, score) for chunk, score in ranked[:top_k] if score >= min_similarity]
    return results


def build_rag_answer(query, chunk_texts, top_k=3):
    """
    Extractive RAG answer: retrieve the most relevant chunks and present
    them as the answer, with similarity scores for transparency.
    Returns None if nothing relevant enough was found.
    """
    results = retrieve_relevant_chunks(query, chunk_texts, top_k=top_k)
    if not results:
        return None

    parts = ["📄 From your uploaded document(s):\n"]
    for i, (chunk, score) in enumerate(results, start=1):
        snippet = chunk.strip()
        if len(snippet) > 500:
            snippet = snippet[:500].rsplit(" ", 1)[0] + "..."
        parts.append(f"{i}. (relevance {score:.2f}) {snippet}")
    return "\n\n".join(parts)

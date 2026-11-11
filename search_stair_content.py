
import math
from collections import Counter, defaultdict

from answer_stair_ollama import CORPUS_PATH, load
from route_stair_sections import tokens


def search_content(queries, limit=20):
    """
    Recherche lexicale dans les éléments du corpus Docling.

    Utilise une pondération de type TF-IDF.
    Ne nécessite ni vecteurs ni appel à Ollama.

    Les résultats sont des candidats documentaires,
    pas des preuves de pertinence sémantique.
    """

    if not isinstance(queries, list):
        raise ValueError("Liste de requêtes attendue.")

    if not 1 <= limit <= 100:
        raise ValueError("Limite invalide.")

    corpus = load(CORPUS_PATH)

    documents = []

    for page in corpus["pages"]:
        for element in page["elements"]:
            text = element.get("text", "")

            if not isinstance(text, str) or not text.strip():
                continue

            if element.get("label") in {
                "page_header",
                "page_footer",
            }:
                continue

            terms = tokens(text)

            if not terms:
                continue

            documents.append({
                "page": element["page"],
                "text": text,
                "source_refs": element["source_refs"],
                "term_counts": Counter(terms),
            })

    document_count = len(documents)

    if not document_count:
        return []

    document_frequency = Counter()

    for document in documents:
        document_frequency.update(
            document["term_counts"].keys()
        )

    query_terms = set()

    for query in queries:
        if isinstance(query, str):
            query_terms.update(tokens(query))

    if not query_terms:
        return []

    results = []

    for document in documents:
        score = 0.0
        matched_terms = []

        for term in query_terms:
            frequency = document["term_counts"].get(term, 0)

            if not frequency:
                continue

            idf = math.log(
                (document_count + 1)
                / (document_frequency[term] + 1)
            ) + 1

            score += (
                (1 + math.log(frequency))
                * idf
            )

            matched_terms.append(term)

        if score <= 0:
            continue

        # Éviter de favoriser mécaniquement
        # les passages très longs.
        length = sum(document["term_counts"].values())

        normalized_score = score / math.sqrt(
            max(length, 1)
        )

        results.append({
            "page": document["page"],
            "text": document["text"],
            "source_refs": document["source_refs"],
            "score": round(normalized_score, 4),
            "matched_terms": sorted(matched_terms),
        })

    results.sort(
        key=lambda item: (
            -item["score"],
            item["page"],
            str(item["source_refs"]),
        )
    )


    return results[:limit]

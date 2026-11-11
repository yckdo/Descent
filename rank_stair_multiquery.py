
from route_stair_sections import rank


def rank_multiquery(question, rewritten_queries, sections):
    """
    Combine le classement STAIR de plusieurs requêtes.

    Le score est une heuristique de navigation,
    pas une probabilité de pertinence.
    """

    queries = [question]

    for query in rewritten_queries:
        if (
            isinstance(query, str)
            and query.strip()
            and query.strip().casefold()
            not in {q.casefold() for q in queries}
        ):
            queries.append(query.strip())

    combined = {}

    for query_index, query in enumerate(queries):
        results = rank(query, sections)

        for result in results:
            section_id = result["id"]

            if section_id not in combined:
                combined[section_id] = {
                    "id": section_id,
                    "title": result["title"],
                    "page": result["page"],
                    "kind": result["kind"],
                    "best_score": 0,
                    "matched_queries": [],
                    "matches": [],
                }

            entry = combined[section_id]

            entry["best_score"] = max(
                entry["best_score"],
                result["score"],
            )

            entry["matched_queries"].append(query)

            entry["matches"].append({
                "query_index": query_index,
                "query": query,
                "score": result["score"],
                "matched_title": result["matched_title"],
            })

    output = []

    for entry in combined.values():
        match_count = len(entry["matched_queries"])

        # Favoriser les sections retrouvées par
        # plusieurs formulations indépendantes.
        # Plafonner ce bonus pour éviter qu'il domine
        # le score lexical principal.
        consensus_bonus = min(
            max(match_count - 1, 0) * 5,
            15,
        )

        entry["match_count"] = match_count
        entry["consensus_bonus"] = consensus_bonus

        entry["combined_score"] = (
            entry["best_score"] + consensus_bonus
        )

        output.append(entry)

    output.sort(
        key=lambda item: (
            -item["combined_score"],
            -item["match_count"],
            item["page"],
            item["id"],
        )
    )

    return output

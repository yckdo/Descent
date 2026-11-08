
from collections import Counter


def audit_evidence(answer, evidence):
    """
    Vérifie la provenance des citations d'une réponse.

    Ne juge ni la fidélité sémantique des affirmations
    ni l'exhaustivité de la réponse.
    """

    evidence_by_id = {
        item["id"]: item
        for item in evidence
    }

    points = answer.get("points", [])

    if not isinstance(points, list):
        raise ValueError(
            "Le champ 'points' doit être une liste."
        )

    results = []
    all_citations = []

    for number, point in enumerate(points, start=1):
        if not isinstance(point, dict):
            raise ValueError(
                f"Point {number} : objet attendu."
            )

        text = point.get("text", "")
        citations = point.get("source_ids", [])

        if not isinstance(text, str):
            raise ValueError(
                f"Point {number} : texte invalide."
            )

        if not isinstance(citations, list):
            raise ValueError(
                f"Point {number} : citations invalides."
            )

        valid_citations = []
        unknown_citations = []

        for source_id in citations:
            if (
                isinstance(source_id, str)
                and source_id in evidence_by_id
            ):
                valid_citations.append(source_id)
                all_citations.append(source_id)
            else:
                unknown_citations.append(source_id)

        pages = sorted({
            evidence_by_id[source_id]["page"]
            for source_id in valid_citations
        })

        sections = sorted({
            evidence_by_id[source_id]["section_id"]
            for source_id in valid_citations
        })

        results.append({
            "point": number,
            "has_text": bool(text.strip()),
            "has_citations": bool(citations),
            "valid_citations": valid_citations,
            "unknown_citations": unknown_citations,
            "pages": pages,
            "sections": sections,
        })

    citation_counts = Counter(all_citations)

    cited_sections = sorted({
        evidence_by_id[source_id]["section_id"]
        for source_id in all_citations
    })

    available_sections = sorted({
        item["section_id"]
        for item in evidence
    })

    errors = []

    for result in results:
        number = result["point"]

        if not result["has_text"]:
            errors.append(
                f"Point {number} : texte vide"
            )

        if not result["has_citations"]:
            errors.append(
                f"Point {number} : aucune citation"
            )

        if result["unknown_citations"]:
            errors.append(
                f"Point {number} : citation inconnue"
            )

    return {
        "valid": not errors,
        "point_count": len(points),
        "evidence_count": len(evidence),
        "cited_evidence_count": len(citation_counts),
        "available_sections": available_sections,
        "cited_sections": cited_sections,
        "points": results,
        "errors": errors,
        "semantic_validation_completed": False,
    }

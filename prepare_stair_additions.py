
from resolve_stair_docling_refs import resolve_docling_refs


def prepare_additions(coverage, reference, evidence):
    """
    Prépare les règles signalées par l'audit STAIR.

    Les sources sont retrouvées par références Docling,
    sans dépendre des identifiants temporaires Sxxx.

    Aucun appel à Ollama.
    """

    if not isinstance(coverage, dict):
        raise ValueError("Audit de couverture invalide.")

    if not isinstance(reference, dict):
        raise ValueError("Référentiel invalide.")

    if not isinstance(evidence, list):
        raise ValueError("Extraits STAIR invalides.")

    rules_by_id = {
        rule["id"]: rule
        for rule in reference["rules"]
    }

    evidence_by_id = {
        item["id"]: item
        for item in evidence
    }

    additions = []

    for check in coverage["checks"]:
        if check["signals_present"]:
            continue

        rule_id = check["rule_id"]

        if rule_id not in rules_by_id:
            raise ValueError(
                f"Règle inconnue : {rule_id}"
            )

        rule = rules_by_id[rule_id]

        docling_refs = rule.get("docling_refs")

        if not docling_refs:
            raise ValueError(
                f"Références Docling absentes : {rule_id}"
            )

        resolved = resolve_docling_refs(
            docling_refs,
            evidence,
            expected_section=reference["section_id"],
        )

        sources = []

        for item in resolved:
            source_id = item["source_id"]
            source = evidence_by_id[source_id]

            sources.append({
                "source_id": source_id,
                "docling_ref": item["docling_ref"],
                "pdf_page": item["pdf_page"],
                "section_id": item["section_id"],
                "text": source["text"],
            })

        additions.append({
            "rule_id": rule_id,
            "rule_name": rule["name"],
            "sources": sources,
        })

    return additions

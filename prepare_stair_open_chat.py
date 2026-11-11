
from answer_stair_ollama import (
    STRUCTURE_PATH,
    load,
    format_context,
)
from query_rewriter import rewrite_question
from rank_stair_multiquery import rank_multiquery
from retrieve_stair_multiquery import retrieve_multiquery
from retrieve_stair_hybrid import retrieve_hybrid
from order_stair_evidence import order_evidence_by_sections
from retrieve_stair_concepts import retrieve_concept_complements
from merge_stair_concepts import merge_concept_evidence


def prepare_open_chat(question):
    """
    Prépare les preuves pour une question libre.

    Retourne un contexte documentaire sourcé,
    sans générer la réponse finale.
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question vide.")

    question = question.strip()

    # 1. Reformulations automatiques par Ollama.
    queries = rewrite_question(question)

    # 2. Classement des sections STAIR.
    structure = load(STRUCTURE_PATH)

    ranked = rank_multiquery(
        question,
        queries,
        structure["sections"],
    )

    if not ranked:
        return {
            "question": question,
            "queries": queries,
            "evidence": [],
            "context": "",
            "selected": None,
            "added": [],
        }

    # 3. Récupération documentaire structurée.
    stair = retrieve_multiquery(
        ranked,
        max_roots=3,
        max_context_chars=28000,
    )

    # 4. Recherche complémentaire dans Docling.
    hybrid = retrieve_hybrid(
        stair,
        queries,
        max_extra=5,
        max_context_chars=28000,
    )

    # 5. Ordre documentaire STAIR pour Qwen3.
    # Sections principales d'abord, puis compléments.
    evidence = order_evidence_by_sections(
        hybrid["evidence"],
        ranked,
        max_roots=3,
    )

    # 6. Compléments par cooccurrence de concepts.
    complements = retrieve_concept_complements(
        queries,
        evidence,
        max_extra=5,
    )

    # 7. Fusion avec identifiants uniques et budget contrôlé.
    merged = merge_concept_evidence(
        evidence,
        complements["evidence"],
        max_context_chars=28000,
    )

    evidence = merged["evidence"]
    context = merged["context"]

    if len(context) > 28000:
        raise ValueError(
            "Le contexte dépasse le budget documentaire."
        )

    # Section principale compatible avec FastAPI.
    selected = None

    selected_roots = stair.get("selected_roots", [])

    if selected_roots:
        first = selected_roots[0]
        section_id = (
            first["id"] if isinstance(first, dict) else first
        )

        section = next(
            (
                item
                for item in structure["sections"]
                if item["id"] == section_id
            ),
            None,
        )

        if section is not None:
            selected = {
                "id": section["id"],
                "title": section["title"],
            }

    return {
        "question": question,
        "queries": queries,
        "evidence": evidence,
        "context": context,
        "selected": selected,
        "added": hybrid["added"],
    }

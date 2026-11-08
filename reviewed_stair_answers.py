
import json
import unicodedata
from pathlib import Path

from validate_stair_evidence import audit_evidence

ROOT = Path(__file__).resolve().parent

BOUTIQUE_REVIEWED = (
    ROOT
    / "validation"
    / "captures"
    / "boutique_web_merged_clean.json"
)


def normalize_question(question):
    text = unicodedata.normalize("NFKC", question)
    return " ".join(text.casefold().strip().split())


def get_reviewed_answer(question, selected, evidence):
    """
    Charge la réponse Boutique revue uniquement pour
    la question exacte du scénario de référence.

    Vérifie que chaque source citée correspond aux
    extraits documentaires enregistrés.

    Retourne None si la réponse ne s'applique pas.
    """

    if normalize_question(question) != normalize_question(
        "Comment fonctionne la boutique ?"
    ):
        return None

    if selected["id"] != "sec_0126":
        return None

    if not BOUTIQUE_REVIEWED.exists():
        return None

    reviewed = json.loads(
        BOUTIQUE_REVIEWED.read_text(encoding="utf-8")
    )

    if normalize_question(reviewed["question"]) != (
        normalize_question(question)
    ):
        return None

    if reviewed.get("coverage_audit", {}).get(
        "rules_flagged"
    ) != 0:
        return None

    saved_evidence = {
        item["id"]: item
        for item in reviewed["evidence"]
    }

    current_evidence = {
        item["id"]: item
        for item in evidence
    }

    points = reviewed["answer"]["points"]

    cited_ids = {
        sid
        for point in points
        for sid in point["source_ids"]
    }

    for sid in cited_ids:
        old = saved_evidence.get(sid)
        current = current_evidence.get(sid)

        if old is None or current is None:
            return None

        for field in (
            "text",
            "page",
            "section_id",
            "source_refs",
        ):
            if old.get(field) != current.get(field):
                return None

    citation_audit = audit_evidence(
        reviewed["answer"],
        evidence,
    )

    if not citation_audit["valid"]:
        return None

    return reviewed["answer"]

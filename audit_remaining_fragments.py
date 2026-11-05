
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "data/normalized/descent_rulebook.json"
OUTPUT = ROOT / "validation/fragment_review.json"
SUMMARY = ROOT / "validation/fragment_review_summary.txt"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def is_short_marker(text):
    """Repère un numéro ou un marqueur très court."""
    return bool(
        re.fullmatch(r"\d{1,2}", text.strip())
    )


def suggest(page, current, following):
    """Propose une catégorie, sans valider de correction."""

    text = current["text"].strip()
    next_text = following["text"].strip()

    # Les numéros isolés sont souvent issus de figures.
    # Leur exclusion nécessite toujours une confirmation.
    if is_short_marker(text):
        return (
            "exclude",
            "Numéro isolé potentiellement issu d'un schéma."
        )

    # Les intitulés du journal de campagne sont des
    # données distinctes, pas une phrase à reconstituer.
    if page == 21 and 779 <= int(
        current["source_refs"][0].split("/")[-1]
    ) <= 805:
        return (
            "preserve",
            "Intitulé ou champ du journal de campagne."
        )

    # Ne pas fusionner le récit avec l'explication
    # de la structure de campagne.
    if page == 19 and current["source_refs"] == [
        "#/texts/717"
    ]:
        return (
            "preserve",
            "Transition entre récit et explication de campagne."
        )

    # Les fragments internes aux cartes, particulièrement
    # sur ces pages, demandent une vérification visuelle.
    if page in (14, 16, 21) and len(text) < 45:
        return (
            "review",
            "Texte court : vérifier son origine documentaire."
        )

    # Un texte qui ne termine pas une phrase et dont
    # la suite commence par une minuscule est un bon
    # candidat à une fusion.
    if next_text and next_text[0].islower():
        return (
            "join",
            "Continuité probable d'une phrase."
        )

    return (
        "review",
        "Frontière documentaire à vérifier."
    )


def main():
    data = load_json(SOURCE)

    # Préserver le travail manuel déjà effectué.
    if OUTPUT.exists():
        raise FileExistsError(
            f"Registre existant : {OUTPUT}\n"
            "Aucun écrasement automatique."
        )

    findings = []

    for page in data["pages"]:
        page_number = page["page"]
        elements = page["elements"]

        for i, current in enumerate(elements[:-1]):

            if current["label"] != "text":
                continue

            text = current["text"].strip()

            if not text:
                continue

            # Même critère que dans le diagnostic initial.
            if text.endswith(
                (".", "!", "?", ":", '"', ")")
            ):
                continue

            following = elements[i + 1]

            if following["label"] not in (
                "text",
                "list_item"
            ):
                continue

            recommendation, reason = suggest(
                page_number, current, following
            )

            findings.append({
                "id": f"fragment_{len(findings) + 1:04d}",
                "page": page_number,
                "source_refs": current["source_refs"],
                "next_refs": following["source_refs"],
                "text": current["text"],
                "next_text": following["text"],
                "suggestion": recommendation,
                "reason": reason,
                "decision": "review",
                "status": "pending"
            })

    counts = Counter(
        item["suggestion"] for item in findings
    )

    result = {
        "schema_version": "1.0",
        "document": "descent_rulebook_en",
        "source": str(SOURCE.relative_to(ROOT)),
        "status": "review_pending",
        "notes": [
            "Les suggestions ne sont pas des décisions validées.",
            "Les paires successives peuvent se chevaucher.",
            "Une fusion doit préserver les frontières des paragraphes.",
            "Aucune correction n'est appliquée par ce script."
        ],
        "findings": findings
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    lines = [
        "=== AUDIT COMPLÉMENTAIRE DU CORPUS V2 ===",
        f"Signalements : {len(findings)}",
        "",
        "SUGGESTIONS (non validées)",
        f"join : {counts['join']}",
        f"exclude : {counts['exclude']}",
        f"preserve : {counts['preserve']}",
        f"review : {counts['review']}",
        "",
        "RÉPARTITION PAR PAGE"
    ]

    pages = Counter(
        item["page"] for item in findings
    )

    for page, number in sorted(pages.items()):
        lines.append(f"Page {page} : {number}")

    lines.extend([
        "",
        "POINTS À EXAMINER EN PRIORITÉ",
        "Page 14 : illustration de combat et calculs.",
        "Page 16 : schéma de carte et OCR dégradé.",
        "Page 21 : journal de campagne et intitulés.",
        "",
        "Aucune correction appliquée.",
        f"Registre : {OUTPUT.relative_to(ROOT)}"
    ])

    SUMMARY.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print("\n".join(lines))


if __name__ == "__main__":
    main()

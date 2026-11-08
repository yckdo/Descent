
import argparse
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from answer_stair_ollama import (
    prepare_evidence,
    format_context,
    call_ollama,
    validate_answer,
)
from validate_stair_evidence import audit_evidence

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "validation" / "captures"

QUESTIONS = {
    "repos": "Comment fonctionne le repos ?",
    "boutique": "Comment fonctionne la boutique ?",
    "combat": "Comment fonctionne le combat ?",
}


def get_source_version():
    """
    Vérifie les empreintes existantes et retourne
    la version documentaire utilisée.
    """
    links_path = ROOT / "data/stair/cross_page_links.json"

    links = json.loads(
        links_path.read_text(encoding="utf-8")
    )

    version = links["source"]

    result = {}

    for name in ("corpus", "structure"):
        relative_path = version[name]
        expected = version[f"{name}_sha256"]

        file_path = (ROOT / relative_path).resolve()

        if not file_path.is_relative_to(ROOT.resolve()):
            raise ValueError(
                f"Chemin hors projet : {name}"
            )

        actual = hashlib.sha256(
            file_path.read_bytes()
        ).hexdigest()

        if actual != expected:
            raise ValueError(
                f"Empreinte incohérente : {name}"
            )

        result[name] = relative_path
        result[f"{name}_sha256"] = actual

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Capturer une réponse STAIR + Ollama."
    )
    parser.add_argument(
        "scenario",
        choices=QUESTIONS,
    )
    args = parser.parse_args()

    question = QUESTIONS[args.scenario]

    # Vérifier la version documentaire avant génération.
    source_version = get_source_version()

    data = prepare_evidence(question)

    if data is None:
        raise SystemExit("Aucune section STAIR trouvée.")

    evidence = data["evidence"]

    if not evidence:
        raise SystemExit("Aucun extrait documentaire.")

    context = format_context(evidence)
    answer = call_ollama(question, context)

    # Contrôle existant.
    validate_answer(answer, evidence)

    # Contrôle générique.
    audit = audit_evidence(answer, evidence)

    if not audit["valid"]:
        print("Erreurs documentaires :", audit["errors"])
        raise SystemExit(1)

    capture = {
        "scenario": args.scenario,
        "question": question,
        "model": "qwen3:8b",
        "captured_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "selected_section": data["selected"]["id"],
        "source_version": source_version,
        "answer": answer,
        "evidence": evidence,
        "citation_audit": audit,
        "semantic_validation_completed": False,
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = OUTPUT_DIR / f"{args.scenario}_latest.json"

    output.write_text(
        json.dumps(
            capture,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print("=== CAPTURE STAIR + OLLAMA ===")
    print("Scénario :", args.scenario)
    print("Section :", data["selected"]["id"])
    print("Extraits :", len(evidence))
    print("Points :", audit["point_count"])
    print("Citations valides :", audit["valid"])
    print("Fichier :", output)
    print("Validation sémantique : non effectuée")
    print("Corpus V3 inchangé.")


if __name__ == "__main__":
    main()

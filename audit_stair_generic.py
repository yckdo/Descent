
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from validate_stair_evidence import audit_evidence
from resolve_stair_docling_refs import resolve_docling_refs

ROOT = Path(__file__).resolve().parent


def normalize(text):
    text = unicodedata.normalize(
        "NFKD", text.casefold()
    )
    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", text)


def load_json(path):
    if not path.is_file():
        raise ValueError(f"Fichier absent : {path}")

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def verify_source_version(reference):
    """
    Vérifie que le référentiel correspond aux
    fichiers documentaires présents sur disque.
    """
    version = reference.get("source_version")

    if not isinstance(version, dict):
        raise ValueError(
            "Empreintes documentaires absentes."
        )

    for name in ("corpus", "structure"):
        relative_path = version.get(name)
        expected = version.get(f"{name}_sha256")

        if not isinstance(relative_path, str):
            raise ValueError(
                f"Chemin documentaire invalide : {name}"
            )

        if (
            not isinstance(expected, str)
            or len(expected) != 64
        ):
            raise ValueError(
                f"Empreinte invalide : {name}"
            )

        file_path = (ROOT / relative_path).resolve()

        if not file_path.is_relative_to(ROOT.resolve()):
            raise ValueError(
                f"Chemin hors projet : {name}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Fichier documentaire absent : {name}"
            )

        actual = hashlib.sha256(
            file_path.read_bytes()
        ).hexdigest()

        if actual != expected:
            raise ValueError(
                f"Empreinte SHA-256 différente : {name}"
            )


def audit_capture(capture, reference):
    verify_source_version(reference)

    if capture["scenario"] != reference["scenario"]:
        raise ValueError("Scénarios différents.")

    if (
        capture["selected_section"]
        != reference["section_id"]
    ):
        raise ValueError("Section STAIR différente.")

    answer = capture["answer"]
    evidence = capture["evidence"]

    citation_audit = audit_evidence(
        answer, evidence
    )

    if not citation_audit["valid"]:
        raise ValueError(
            "Citations invalides : "
            + str(citation_audit["errors"])
        )

    evidence_by_id = {
        item["id"]: item
        for item in evidence
    }

    answer_text = normalize(
        " ".join(
            point["text"]
            for point in answer["points"]
        )
    )

    results = []

    for rule in reference["rules"]:
        patterns = rule["required_patterns"]

        if rule.get("docling_refs"):
            resolved = resolve_docling_refs(
                rule["docling_refs"],
                evidence,
                expected_section=reference["section_id"],
            )

            source_ids = [
                item["source_id"]
                for item in resolved
            ]

        else:
            # Compatibilité avec les anciens référentiels.
            source_ids = rule["source_ids"]

            unknown_sources = [
                source_id
                for source_id in source_ids
                if source_id not in evidence_by_id
            ]

            if unknown_sources:
                raise ValueError(
                    f"Sources absentes pour {rule['id']}: "
                    + ", ".join(unknown_sources)
                )

        signals = [
            bool(re.search(pattern, answer_text))
            for pattern in patterns
        ]

        detected = all(signals)

        results.append({
            "rule_id": rule["id"],
            "name": rule["name"],
            "source_ids": source_ids,
            "signals_present": detected,
            "individual_signals": signals,
        })

    flagged = sum(
        not item["signals_present"]
        for item in results
    )

    return {
        "scenario": capture["scenario"],
        "selected_section": capture["selected_section"],
        "citation_audit_valid": True,
        "rules_checked": len(results),
        "rules_flagged": flagged,
        "checks": results,
        "semantic_validation_completed": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Audit documentaire STAIR générique."
    )

    parser.add_argument(
        "--reference",
        required=True,
        help="Fichier JSON des règles de référence.",
    )

    parser.add_argument(
        "--capture",
        required=True,
        help="Capture JSON à examiner.",
    )

    args = parser.parse_args()

    reference = load_json(Path(args.reference))
    capture = load_json(Path(args.capture))

    report = audit_capture(capture, reference)

    print("=== AUDIT GÉNÉRIQUE STAIR ===")
    print("Scénario :", report["scenario"])
    print("Section :", report["selected_section"])
    print("Citations valides : oui")
    print()

    for rule in report["checks"]:
        status = (
            "INDICES PRÉSENTS"
            if rule["signals_present"]
            else "À EXAMINER"
        )

        print(
            f"{rule['rule_id']} | {status} "
            f"| {rule['name']}"
        )

    print()
    print("=== BILAN ===")
    print("Règles examinées :", report["rules_checked"])
    print("Règles signalées :", report["rules_flagged"])
    print("Aucun appel Ollama.")
    print("Validation sémantique : non effectuée.")


if __name__ == "__main__":
    main()

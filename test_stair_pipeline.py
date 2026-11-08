
from answer_stair_ollama import prepare_evidence

TEST_CASES = [
    {
        "name": "Repos",
        "question": "Comment fonctionne le repos ?",
        "section_id": "sec_0055",
        "sections": 1,
        "elements": 1,
        "pages": {9},
    },
    {
        "name": "Boutique",
        "question": "Comment fonctionne la boutique ?",
        "section_id": "sec_0126",
        "sections": 1,
        "elements": 6,
        "pages": {20, 21},
    },
    {
        "name": "Combat",
        "question": "Comment fonctionne le combat ?",
        "section_id": "sec_0069",
        "sections": 6,
        "elements": 22,
        "pages": {12, 13},
    },
]


def main():
    print("=== TESTS DE NON-RÉGRESSION STAIR ===")

    errors = []

    for case in TEST_CASES:
        data = prepare_evidence(case["question"])

        if data is None:
            errors.append(
                f"{case['name']} : aucune section trouvée"
            )
            continue

        selected = data["selected"]["id"]
        sections = len(data["sections"])
        elements = len(data["evidence"])

        pages = {
            item["page"]
            for item in data["evidence"]
        }

        checks = {
            "section principale": (
                selected == case["section_id"]
            ),
            "nombre de sections": (
                sections == case["sections"]
            ),
            "nombre d'éléments": (
                elements == case["elements"]
            ),
            "pages PDF": (
                pages == case["pages"]
            ),
        }

        # Vérifier les références et les éléments vides.
        ids = [e["id"] for e in data["evidence"]]

        checks["identifiants uniques"] = (
            len(ids) == len(set(ids))
        )

        checks["provenance complète"] = all(
            item["source_refs"]
            and item["text"].strip()
            for item in data["evidence"]
        )

        checks["aucune pagination"] = all(
            item["text"].strip()
            not in {"9", "12", "13", "20", "21"}
            for item in data["evidence"]
        )

        passed = all(checks.values())

        print()
        print(f"{case['name']} : {'OK' if passed else 'ÉCHEC'}")
        print("  Section :", selected)
        print("  Sections récupérées :", sections)
        print("  Éléments :", elements)
        print("  Pages PDF :", sorted(pages))

        for name, ok in checks.items():
            if not ok:
                errors.append(f"{case['name']} : {name}")
                print("  ERREUR :", name)

    print()
    print("=== BILAN ===")
    print("Scénarios :", len(TEST_CASES))
    print("Erreurs :", len(errors))
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()


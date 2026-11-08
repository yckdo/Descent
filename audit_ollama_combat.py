
from answer_stair_ollama import (
    prepare_evidence,
    format_context,
    call_ollama,
    validate_answer,
)

QUESTION = "Comment fonctionne le combat ?"

data = prepare_evidence(QUESTION)

if data is None:
    raise SystemExit("Aucune section trouvée.")

context = format_context(data["evidence"])
answer = call_ollama(QUESTION, context)
sources = validate_answer(answer, data["evidence"])

expected_sections = [
    "sec_0070",
    "sec_0073",
    "sec_0074",
    "sec_0076",
    "sec_0077",
]

print("=== AUDIT PROCÉDURAL COMBAT ===")
print("Étapes générées :", len(answer["points"]))

for index, expected_section in enumerate(
    expected_sections, start=1
):
    if index > len(answer["points"]):
        print(f"Étape {index} : ABSENTE")
        continue

    point = answer["points"][index - 1]
    cited_sections = {
        sources[source_id]["section_id"]
        for source_id in point["source_ids"]
    }

    status = (
        "OK"
        if expected_section in cited_sections
        else "À EXAMINER"
    )

    print(
        f"Étape {index} : {status} "
        f"| Section attendue : {expected_section}"
    )

print()
print("Contrôle : correspondance des étapes et des sources.")
print("La fidélité complète du texte reste à examiner.")

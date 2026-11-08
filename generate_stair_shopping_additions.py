
import json
import urllib.request
from pathlib import Path

from validate_stair_evidence import audit_evidence

ROOT = Path(__file__).resolve().parent

INPUT = ROOT / "validation/captures/boutique_revision_input.json"
OUTPUT = ROOT / "validation/captures/boutique_additions.json"

MODEL = "qwen3:8b"
URL = "http://127.0.0.1:11434/api/chat"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def call_ollama(rule, question):
    system_prompt = """
Tu es un assistant documentaire spécialisé dans
Descent: Journeys in the Dark, Second Edition.

Tu dois rédiger un seul complément de règle en français.

CONSIGNES :
- Utilise exclusivement le passage documentaire fourni.
- Explique précisément la règle demandée.
- Préserve les quantités, les conditions et les exceptions.
- Ne complète pas les sources avec tes connaissances.
- N'ajoute aucun autre mécanisme de jeu.
- N'invente aucune citation.
- Ne mentionne pas la page PDF dans le texte.
- Rédige une ou deux phrases courtes.
- N'utilise pas de numérotation.

Réponds uniquement avec cet objet JSON :

{
  "text": "Explication précise de la règle.",
  "source_ids": ["S001"]
}

L'identifiant dans cet exemple est illustratif.
Utilise l'identifiant réellement fourni.
""".strip()

    user_prompt = f"""
Question initiale :
{question}

Règle à compléter :
{rule['rule_name']}

Source autorisée : {rule['source_id']}
Page du PDF original : {rule['pdf_page']}

Passage documentaire original :
{rule['source_text']}

Rédige uniquement le complément correspondant
à cette règle.
""".strip()

    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 450,
        },
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request, timeout=180
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    require(
        result.get("done_reason") != "length",
        "Génération tronquée par Ollama."
    )

    content = result.get("message", {}).get("content", "")

    require(content.strip(), "Réponse Ollama vide.")

    return json.loads(content)


def main():
    data = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    require(
        data.get("scenario") == "boutique",
        "Scénario inattendu."
    )

    rules = data["rules_to_review"]

    require(
        len(rules) == 3,
        "Trois règles attendues pour ce test."
    )

    additions = []

    for rule in rules:
        print(
            "Génération :",
            rule["rule_id"],
            f"({rule['source_id']})",
            flush=True,
        )

        generated = call_ollama(
            rule, data["question"]
        )

        require(
            isinstance(generated, dict),
            "Réponse JSON invalide."
        )

        text = generated.get("text")
        source_ids = generated.get("source_ids")

        require(
            isinstance(text, str) and text.strip(),
            "Complément vide."
        )

        require(
            isinstance(source_ids, list)
            and source_ids == [rule["source_id"]],
            "Citation différente de la source autorisée."
        )

        # Contrôle indépendant des références.
        evidence = [{
            "id": rule["source_id"],
            "page": rule["pdf_page"],
            "section_id": rule["section_id"],
            "text": rule["source_text"],
            "source_refs": rule["source_refs"],
        }]

        audit = audit_evidence(
            {
                "points": [{
                    "text": text,
                    "source_ids": source_ids,
                }]
            },
            evidence,
        )

        require(
            audit["valid"],
            "Échec de la validation documentaire."
        )

        additions.append({
            "rule_id": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "text": text.strip(),
            "source_ids": source_ids,
            "pdf_page": rule["pdf_page"],
            "citation_audit": audit,
            "semantic_validation_completed": False,
        })

    output = {
        "scenario": "boutique",
        "question": data["question"],
        "model": MODEL,
        "revision_mode": "independent_additions",
        "original_answer_unchanged": True,
        "additions": additions,
        "semantic_validation_completed": False,
    }

    OUTPUT.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("=== COMPLÉMENTS STAIR + OLLAMA ===")
    print("Compléments générés :", len(additions))
    print("Citations contrôlées : oui")
    print("Fichier :", OUTPUT)
    print("Réponse initiale inchangée.")
    print("Corpus V3 inchangé.")
    print("Validation sémantique : non effectuée.")


if __name__ == "__main__":
    main()

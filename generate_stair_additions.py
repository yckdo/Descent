
import json
import urllib.request
from pathlib import Path

from audit_stair_generic import audit_capture
from prepare_stair_additions import prepare_additions
from validate_stair_evidence import audit_evidence

ROOT = Path(__file__).resolve().parent

REFERENCE = ROOT / "validation/rule_checks/boutique.json"
CAPTURE = ROOT / "validation/captures/boutique_latest.json"
OUTPUT = ROOT / "validation/captures/boutique_web_additions.json"

MODEL = "qwen3:8b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def generate_one(rule, question):
    sources = rule["sources"]

    context = "\n\n".join(
        (
            f"[{item['source_id']}]\n"
            f"PDF original : page {item['pdf_page']}\n"
            f"Texte : {item['text']}"
        )
        for item in sources
    )

    system_prompt = """
Tu es un assistant documentaire des règles de
Descent: Journeys in the Dark, deuxième édition.

Rédige uniquement le complément demandé, en français.

Règles impératives :
- Utilise exclusivement les extraits fournis.
- N'invente aucune règle.
- Préserve les conditions, limites et exceptions.
- Rédige une ou deux phrases concises.
- N'ajoute pas de numérotation.
- Ne répète pas les règles sans rapport avec
  le complément demandé.
- Ne mentionne aucune page PDF dans le texte.
- Cite uniquement les identifiants autorisés.
- Réponds exclusivement avec un objet JSON valide.

Format :
{
  "text": "Explication du complément.",
  "source_ids": ["S001"]
}

L'identifiant S001 est un exemple : utilise uniquement
les identifiants figurant dans les extraits.
""".strip()

    user_prompt = f"""
Question initiale :
{question}

Règle à compléter :
{rule['rule_name']}

Extraits documentaires autorisés :
{context}
""".strip()

    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 500,
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
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=180,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    require(
        result.get("done_reason") != "length",
        "Génération tronquée par Ollama.",
    )

    content = result.get("message", {}).get(
        "content", ""
    )

    require(
        isinstance(content, str) and content.strip(),
        "Réponse Ollama vide.",
    )

    return json.loads(content)


def main():
    reference = json.loads(
        REFERENCE.read_text(encoding="utf-8")
    )
    capture = json.loads(
        CAPTURE.read_text(encoding="utf-8")
    )

    coverage = audit_capture(capture, reference)

    pending = prepare_additions(
        coverage,
        reference,
        capture["evidence"],
    )

    require(
        len(pending) == 3,
        "Trois compléments attendus pour ce pilote.",
    )

    additions = []

    for rule in pending:
        print(
            "Génération :",
            rule["rule_id"],
            flush=True,
        )

        generated = generate_one(
            rule,
            capture["question"],
        )

        require(
            isinstance(generated, dict),
            "Format JSON incorrect.",
        )

        text = generated.get("text")
        source_ids = generated.get("source_ids")

        require(
            isinstance(text, str) and text.strip(),
            "Complément vide.",
        )

        require(
            isinstance(source_ids, list)
            and bool(source_ids)
            and all(
                isinstance(sid, str)
                for sid in source_ids
            ),
            "Liste de citations incorrecte.",
        )

        allowed_ids = {
            item["source_id"]
            for item in rule["sources"]
        }

        require(
            set(source_ids).issubset(allowed_ids),
            "Citation hors des sources autorisées.",
        )

        rule_evidence = [
            item
            for item in capture["evidence"]
            if item["id"] in allowed_ids
        ]

        citation_audit = audit_evidence(
            {
                "points": [{
                    "text": text,
                    "source_ids": source_ids,
                }]
            },
            rule_evidence,
        )

        require(
            citation_audit["valid"],
            "Validation des citations échouée.",
        )

        additions.append({
            "rule_id": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "text": text.strip(),
            "source_ids": source_ids,
            "citation_audit": citation_audit,
        })

    output = {
        "scenario": "boutique",
        "question": capture["question"],
        "original_answer": capture["answer"],
        "additions": additions,
        "semantic_validation_completed": False,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("=== GÉNÉRATION DES COMPLÉMENTS STAIR ===")
    print("Compléments générés :", len(additions))
    print("Citations contrôlées : oui")
    print("Réponse initiale conservée : oui")
    print("Rapport :", OUTPUT)
    print("Corpus V3 inchangé.")
    print("Validation sémantique : non effectuée.")


if __name__ == "__main__":
    main()

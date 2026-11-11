from validate_stair_evidence import audit_evidence

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

from route_stair_sections import rank
from retrieve_stair_section import (
    build_source_lookup,
    retrieve,
)
from retrieve_stair_hierarchy import (
    build_index_children,
    ordered_sections,
)

ROOT = Path(__file__).resolve().parent

CORPUS_PATH = ROOT / "data/normalized/descent_rulebook.json"
STRUCTURE_PATH = ROOT / "data/stair/document_structure.json"
LINKS_PATH = ROOT / "data/stair/cross_page_links.json"

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5-coder:14b"

MAX_CONTEXT_CHARS = 30000


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare_evidence(question):
    corpus = load(CORPUS_PATH)
    structure = load(STRUCTURE_PATH)
    links = load(LINKS_PATH)

    require(
        links["source"]["corpus_sha256"]
        == sha256(CORPUS_PATH),
        "Le corpus a changé depuis l'audit."
    )

    require(
        links["source"]["structure_sha256"]
        == sha256(STRUCTURE_PATH),
        "La structure a changé depuis l'audit."
    )

    candidates = rank(
        question,
        structure["sections"]
    )

    if not candidates:
        return None

    root_id = candidates[0]["id"]

    children = build_index_children(structure)
    section_ids = ordered_sections(root_id, children)

    lookup = build_source_lookup(corpus)

    evidence = []
    retrieved_sections = []
    seen_elements = set()

    for section_id in section_ids:
        section, blocks, _ = retrieve(
            section_id,
            structure,
            links,
            lookup
        )

        retrieved_sections.append({
            "id": section["id"],
            "title": section["title"],
            "pdf_page": section["pdf_page"],
        })

        for block in blocks:
            identity = tuple(block["source_refs"])

            require(
                identity not in seen_elements,
                f"Élément récupéré en double : {identity}"
            )

            seen_elements.add(identity)

            evidence.append({
                "id": f"S{len(evidence) + 1:03d}",
                "page": block["page"],
                "section_id": section_id,
                "section_title": section["title"],
                "text": block["text"].strip(),
                "source_refs": block["source_refs"],
            })

    return {
        "selected": candidates[0],
        "sections": retrieved_sections,
        "evidence": evidence,
    }


def format_context(evidence):
    parts = []

    for item in evidence:
        parts.append(
            f"[{item['id']}]\n"
            f"Section : {item['section_title']}\n"
            f"PDF original : page {item['page']}\n"
            f"Texte : {item['text']}"
        )

    context = "\n\n".join(parts)

    require(
        len(context) <= MAX_CONTEXT_CHARS,
        "Contexte trop volumineux pour ce test pilote. "
        "Il faut sélectionner moins de passages."
    )

    return context


def call_ollama(question, context):
    from descent_terminology import format_terminology

    system_prompt = """
Tu es un assistant documentaire spécialisé dans les règles
de Descent: Journeys in the Dark, Second Edition.

Réponds exclusivement en français, à partir des extraits fournis.

PRIORITÉ ABSOLUE : FIDÉLITÉ AUX SOURCES

1. N'utilise que les informations présentes dans les extraits.
2. N'invente ni règle, ni condition, ni exception.
3. Préserve les restrictions, les quantités et les moments
   d'application des règles.
4. Si une information manque, ne la complète pas de mémoire.
5. Utilise un vocabulaire français clair et précis.

CONDITIONS D'APPLICATION DES RÈGLES

Avant de rédiger chaque affirmation, vérifie :
- À quel personnage, objet ou acteur la règle s'applique.
- Dans quelle situation la règle est applicable.
- S'il s'agit d'une règle générale ou d'une exception.
- Si les restrictions citées concernent réellement la question.

N'étends jamais une restriction particulière à une règle générale.
Ne transpose jamais une restriction d'un type de personnage
ou d'objet à un autre sans justification explicite.

Réponds directement à la question posée.
Présente séparément les exceptions utiles en précisant
leurs conditions d'application.
N'ajoute pas de procédure détaillée si elle n'est pas demandée.

PRIORITÉ AUX CONDITIONS ESSENTIELLES

Avant de finaliser la réponse :
- Identifie la conclusion qui répond directement à la question.
- Identifie les conditions nécessaires pour que cette
  conclusion soit vraie : cible autorisée, équipement,
  portée, position, visibilité, quantité, moment ou
  restriction, uniquement si elles sont documentées
  et applicables à la question.
- Mentionne explicitement ces conditions lorsqu'elles
  sont indispensables à la validité de la réponse.
- Vérifie que chaque condition importante présente
  dans les sources pertinentes figure dans la réponse.
- Écarte les mécanismes secondaires non demandés.

Pour une question demandant si une action est possible,
privilégie la réponse et ses conditions d'application
plutôt que les étapes de résolution de cette action.

Ne déduis aucune condition absente des sources.
Ne transpose aucune restriction entre acteurs.

PERTINENCE DE LA RÉPONSE

Réponds directement à la question posée.

Avant d'inclure un point, vérifie :
- Qu'il répond directement à la question ou qu'il est
  indispensable pour comprendre la réponse.
- Que sa source justifie précisément l'affirmation.
- Que le lien avec la situation décrite est établi.

N'ajoute pas de règles simplement liées au même thème.
Ne présente pas un mécanisme indépendant comme une
conséquence de la situation décrite.

Pour une question simple, privilégie une réponse concise.
Pour une demande de procédure, conserve toutes les étapes
officielles nécessaires, dans leur ordre.

EXPLICATION DES PROCÉDURES

Si la question demande comment fonctionne une procédure :
- Identifie les étapes explicitement numérotées dans les sources.
- Présente toutes ces étapes dans leur ordre officiel.
- Consacre un point distinct à chaque étape numérotée.
- Ne fusionne pas deux étapes différentes.
- Ne crée pas d'étapes supplémentaires.
- Dans chaque étape, explique les conditions importantes,
  les échecs possibles et les exceptions documentées.
- Ne transforme pas une procédure en simple résumé général.

Si les sources ne contiennent pas d'étapes numérotées,
organise la réponse suivant les mécanismes documentés.

CITATIONS

- Chaque point doit citer les extraits qui le justifient.
- Les citations utilisent uniquement les identifiants fournis.
- Ne cite aucun numéro de page dans tes phrases.
- N'invente aucun identifiant de source.
- Ne cite pas un exemple comme seule preuve d'une règle
  générale si un passage normatif est disponible.

FORMAT OBLIGATOIRE

Réponds uniquement avec un objet JSON valide :

{
  "points": [
    {
      "text": "1. Première étape et ses règles importantes.",
      "source_ids": ["S001"]
    }
  ]
}

Pour une procédure à cinq étapes documentées,
produis cinq points dans l'ordre officiel.

Si les sources ne permettent pas de répondre :
{"points": []}
""".strip()

    system_prompt += (
        "\n\nTERMINOLOGIE FRANÇAISE CONTRÔLÉE\n"
        "Utilise ces traductions lorsque les termes apparaissent "
        "dans les sources, sans inventer de règles.\n"
        + format_terminology()
    )

    user_prompt = (
        f"QUESTION :\n{question}\n\n"
        f"EXTRAITS DOCUMENTAIRES :\n{context}"
    )

    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 1600,
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
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=180
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Impossible de contacter Ollama : {exc}"
        ) from exc

    require(
        result.get("done_reason") != "length",
        "Réponse tronquée par la limite de génération."
    )

    content = result.get("message", {}).get("content", "")

    require(
        content.strip(),
        "Ollama a retourné une réponse vide."
    )

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Ollama n'a pas renvoyé un JSON valide."
        ) from exc


def validate_answer(answer, evidence):
    require(
        isinstance(answer, dict),
        "La réponse doit être un objet JSON."
    )

    points = answer.get("points")

    require(
        isinstance(points, list),
        "Champ 'points' absent ou invalide."
    )

    require(
        len(points) <= 12,
        "Trop d'affirmations générées."
    )

    sources = {
        item["id"]: item
        for item in evidence
    }

    for point in points:
        require(
            isinstance(point, dict),
            "Affirmation invalide."
        )

        text = point.get("text")
        source_ids = point.get("source_ids")

        require(
            isinstance(text, str) and text.strip(),
            "Affirmation vide."
        )

        require(
            isinstance(source_ids, list)
            and len(source_ids) > 0,
            "Affirmation sans citation."
        )

        require(
            all(isinstance(sid, str) for sid in source_ids),
            "Identifiant de citation invalide."
        )

        require(
            len(source_ids) == len(set(source_ids)),
            "Citation répétée dans une affirmation."
        )

        for source_id in source_ids:
            require(
                source_id in sources,
                f"Source inventée : {source_id}"
            )

    return sources


def show_answer(question, answer, sources):
    print()
    print("=== RÉPONSE DESCENT V2 ===")
    print("Question :", question)
    print()

    points = answer["points"]

    if not points:
        print(
            "Les passages récupérés ne permettent pas "
            "de répondre avec suffisamment de certitude."
        )
        return

    for point in points:
        references = [
            sources[sid]
            for sid in point["source_ids"]
        ]

        pages = sorted({
            item["page"] for item in references
        })

        print(point["text"].strip())
        print(
            "Source : PDF p. "
            + ", ".join(map(str, pages))
            + " | Extraits : "
            + ", ".join(point["source_ids"])
        )
        print()

    print(
        "Note : les références sont contrôlées, "
        "mais la fidélité de chaque affirmation "
        "doit encore être évaluée."
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Assistant Descent V2 : "
            "STAIR + Ollama avec citations PDF."
        )
    )

    parser.add_argument(
        "question",
        help="Question sur les règles de Descent"
    )

    args = parser.parse_args()

    print("=== DESCENT V2 : STAIR + OLLAMA ===")
    print("Modèle :", MODEL)

    data = prepare_evidence(args.question)

    if data is None:
        print("Aucune section trouvée par STAIR.")
        print("Aucune réponse générée.")
        return

    evidence = data["evidence"]

    require(
        evidence,
        "Aucun passage documentaire récupéré."
    )

    print(
        "Section principale :",
        data["selected"]["id"],
        "-",
        data["selected"]["title"]
    )
    print("Sections récupérées :", len(data["sections"]))
    print("Extraits documentaires :", len(evidence))
    print(
        "Pages PDF disponibles :",
        ", ".join(
            map(str, sorted({
                item["page"] for item in evidence
            }))
        )
    )

    context = format_context(evidence)
    answer = call_ollama(args.question, context)
    sources = validate_answer(answer, evidence)

    audit = audit_evidence(answer, evidence)

    if not audit["valid"]:
        print()
        print("=== ERREUR DE VALIDATION DOCUMENTAIRE ===")

        for error in audit["errors"]:
            print("-", error)

        raise SystemExit(1)

    print()
    print("=== AUDIT DOCUMENTAIRE STAIR ===")
    print("Points contrôlés :", audit["point_count"])
    print(
        "Extraits cités :",
        audit["cited_evidence_count"]
    )
    print("Citations valides : oui")
    print("Validation sémantique : non effectuée")

    show_answer(args.question, answer, sources)


if __name__ == "__main__":
    main()

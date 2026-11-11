
import argparse
import json
import urllib.error
import urllib.request

MODEL = "qwen2.5-coder:14b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

SYSTEM_PROMPT = """
Tu es un reformulateur de recherche documentaire
pour le jeu Descent: Journeys in the Dark,
deuxième édition.

Le manuel de référence est en anglais.

Ta tâche :
- Comprendre la question du joueur en français
  ou en anglais.
- Produire 3 à 5 requêtes de recherche en anglais.
- Utiliser des termes de règles susceptibles
  d'apparaître dans un manuel anglais.
- Conserver les concepts, restrictions et conditions
  présents dans la question.
- Ne pas inventer une règle ou une réponse.
- Ne pas supposer qu'une exception existe.
- Ne pas inventer de titre de section.
- Ne pas écrire d'explication.

Réponds uniquement avec ce JSON :

{
  "queries": [
    "first search query",
    "second search query",
    "third search query"
  ]
}
""".strip()


def rewrite_question(question):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question vide.")

    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 300,
        },
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": question.strip(),
            },
        ],
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Service Ollama indisponible : {exc}"
        ) from exc

    if result.get("done_reason") == "length":
        raise ValueError("Reformulation tronquée.")

    content = result.get("message", {}).get("content", "")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Reformulation vide.")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Reformulation JSON invalide."
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError("Objet JSON attendu.")

    queries = parsed.get("queries")

    if not isinstance(queries, list):
        raise ValueError("Liste de requêtes absente.")

    clean = []

    for item in queries:
        if not isinstance(item, str):
            continue

        item = " ".join(item.strip().split())

        if not item or len(item) > 120:
            continue

        if item.casefold() not in {
            existing.casefold() for existing in clean
        }:
            clean.append(item)

    if not 1 <= len(clean) <= 5:
        raise ValueError(
            "Nombre de requêtes exploitables incorrect."
        )

    return clean


def main():
    parser = argparse.ArgumentParser(
        description="Reformulation bilingue pour STAIR."
    )
    parser.add_argument("question")
    args = parser.parse_args()

    queries = rewrite_question(args.question)

    print("=== REFORMULATION STAIR ===")
    print("Question :", args.question)

    for index, query in enumerate(queries, 1):
        print(f"{index}. {query}")


if __name__ == "__main__":
    main()


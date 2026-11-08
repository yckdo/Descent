
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from answer_stair_ollama import (
    prepare_evidence,
    format_context,
    call_ollama,
    validate_answer,
)
from validate_stair_evidence import audit_evidence
from reviewed_stair_answers import get_reviewed_answer
from audit_stair_generic import audit_capture, load_json


ROOT = Path(__file__).resolve().parent
INDEX_HTML = ROOT / "web" / "index.html"

app = FastAPI(
    title="Descent V2",
    description="Assistant local des règles de Descent",
    version="0.2.0",
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@app.get("/")
def home():
    return FileResponse(
        INDEX_HTML,
        media_type="text/html",
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "application": "Descent V2",
        "backend": "FastAPI",
    }


@app.post("/api/ask")
def ask(request: QuestionRequest):
    question = request.question.strip()

    if len(question) < 3:
        raise HTTPException(
            status_code=400,
            detail="Question trop courte.",
        )

    try:
        data = prepare_evidence(question)

        if data is None or not data["evidence"]:
            return {
                "question": question,
                "status": "no_sources",
                "points": [],
                "message": (
                    "Aucun passage documentaire "
                    "pertinent n'a été trouvé."
                ),
            }

        evidence = data["evidence"]

        reviewed_answer = get_reviewed_answer(
            question,
            data["selected"],
            evidence,
        )

        if reviewed_answer is not None:
            answer = reviewed_answer
            answer_origin = "reviewed"
        else:
            context = format_context(evidence)
            answer = call_ollama(question, context)
            answer_origin = "generated"

        # Validation existante des identifiants.
        try:
            sources = validate_answer(answer, evidence)
        except ValueError as validation_error:
            if answer_origin == "generated":
                print(
                    "[Descent V2] Nouvelle tentative Qwen3 :",
                    str(validation_error),
                    flush=True,
                )

                retry_question = (
                    question
                    + "\n\nCONSIGNE DE CORRECTION : "
                    "La réponse précédente contenait des "
                    "citations invalides. Chaque point doit "
                    "contenir au moins un identifiant dans "
                    "source_ids, choisi exclusivement parmi "
                    "les extraits documentaires fournis. "
                    "Ne crée aucune citation et ne déduis "
                    "aucune règle absente des sources. "
                    "Si les extraits ne permettent pas de "
                    "répondre, retourne {\\\"points\\\": []}."
                )

                try:
                    answer = call_ollama(
                        retry_question,
                        format_context(evidence),
                    )
                    sources = validate_answer(
                        answer,
                        evidence,
                    )
                except ValueError as retry_error:
                    validation_error = retry_error
                else:
                    validation_error = None

            if validation_error is not None:
                print(
                    "[Descent V2] Réponse non validée :",
                    str(validation_error),
                    flush=True,
                )
                return {
                    "question": question,
                    "status": "invalid_citations",
                    "answer_origin": answer_origin,
                    "points": [],
                    "message": (
                        "La réponse générée n'a pas passé "
                        "le contrôle des citations. "
                        "Reformule ta question et réessaie."
                    ),
                    "semantic_validation_completed": False,
                }

        # Validation documentaire générique.
        audit = audit_evidence(answer, evidence)

        if not audit["valid"]:
            raise ValueError(
                "Citations documentaires invalides : "
                + ", ".join(audit["errors"])
            )

        # Audit de couverture sur la réponse réelle.
        # Pour cette première intégration, seul le
        # scénario Boutique dispose d'un référentiel.
        coverage = None

        if data["selected"]["id"] == "sec_0126":
            reference_path = (
                ROOT / "validation/rule_checks/boutique.json"
            )

            reference = load_json(reference_path)

            current_capture = {
                "scenario": "boutique",
                "selected_section": data["selected"]["id"],
                "answer": answer,
                "evidence": evidence,
            }

            coverage = audit_capture(
                current_capture,
                reference,
            )

        points = []

        for point in answer["points"]:
            references = [
                sources[sid]
                for sid in point["source_ids"]
            ]

            pages = sorted({
                source["page"]
                for source in references
            })

            points.append({
                "text": point["text"].strip(),
                "source_ids": point["source_ids"],
                "pdf_pages": pages,
            })

        return {
            "question": question,
            "status": "ok" if points else "no_answer",
            "answer_origin": answer_origin,
            "section": {
                "id": data["selected"]["id"],
                "title": data["selected"]["title"],
            },
            "points": points,
            "citation_audit": {
                "valid": audit["valid"],
                "point_count": audit["point_count"],
                "cited_evidence_count": (
                    audit["cited_evidence_count"]
                ),
            },
            "semantic_validation_completed": False,
            "coverage_audit": coverage,
        }

    except Exception as exc:
        print(
            "[Descent V2] Erreur API :",
            repr(exc),
            flush=True,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Impossible de produire une réponse. "
                "Consulte le terminal du serveur."
            ),
        ) from exc

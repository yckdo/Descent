# STAIR V2 — raisonnement vérifiable (branche expérimentale)

## Objectif

Ajouter un moteur de raisonnement **en mode observation** à l'architecture STAIR existante. La réponse RAG produite par l'application reste la référence : le moteur parallèle ne la modifie jamais, ne l'approuve pas et ne la rejette pas.

## État et périmètre

- Branche de travail : `feature/stair-reasoning`, créée depuis `main`.
- Prototype local testé : `stair_reasoner.py` (déductions à partir de règles déjà structurées), `stair_shadow.py` (adaptateur désactivé par défaut), tests unitaires et exemples JSON.
- Vérification locale effectuée sur le prototype : 13 tests réussis.
- **Pas encore intégré à FastAPI** ; aucune confirmation qu'un serveur utilise ce moteur.
- L'extraction automatique de règles à partir des textes du manuel reste à développer et à évaluer.
- Le statut « supported » signifie uniquement « déductible à partir des règles structurées fournies », et non « vérifié contre le PDF original ».

## Contrat de raccordement proposé

Point d'insertion : après la génération de la réponse RAG, avant la sérialisation HTTP, dans le handler réel à identifier.

```python
# Exemple conceptuel uniquement : ne pas coller sans identifier le handler réel.
result = compare_observation(
    rag_response=existing_answer,
    reasoning_spec=normalized_spec_or_none,
    shadow_enabled=False,  # activation explicite seulement
)
assert result["rag_response"] == existing_answer
```

Ne pas injecter automatiquement une spécification synthétisée par Qwen tant que ses sources, les exceptions et les priorités ne sont pas contrôlées.

## Sécurité de déploiement

1. Aucun secret, PDF ni extraction de texte intégral dans le dépôt public.
2. Par défaut `STAIR_SHADOW_ENABLED=0`.
3. Observer dans un journal séparé (sans texte brut ni données sensibles).
4. En cas d'erreur de l'analyse parallèle, conserver la réponse existante.
5. Tester un jeu de questions de référence, puis effectuer la revue des traces.
6. N'envisager l'intégration au Semantic Gate qu'après mesure des faux positifs et des faux négatifs.

## Étapes suivantes

1. Aligner la branche sur les modules FastAPI réellement présents et identifier la fonction qui construit la réponse.
2. Ajouter les prototypes `stair_reasoner.py`, `stair_shadow.py`, leurs tests et leurs exemples **après inspection du code source local**.
3. Tester hors production le raccordement en mode observation.
4. Comparer la conformité aux sources, l'exactitude des déductions et les abstentions.

Voir aussi `docs/STAIR_ARCHITECTURE_DESCENT.md` pour les choix initiaux de routage structurel et de provenance des sources.

# STAIR V2 — Contrôle de fidélité des règles candidates

## But

Le fichier `stair_fidelity_gate.py` inspecte les règles proposées par Qwen **avant toute utilisation éventuelle dans un moteur d'inférence**.

Une citation exacte ne suffit pas à prouver une déduction logique. Le contrôle est donc volontairement **bloquant** pour toute promotion automatique de règle.

## Pipeline expérimental

1. STAIR extrait des passages avec `id`, `page`, `source_refs`, `text`.
2. `stair_rule_extractor.py` demande à Ollama local de proposer des règles.
3. Les propositions passent un contrôle de structure et de citation exacte.
4. `stair_fidelity_gate.py` contrôle à nouveau l'identité de la source, la page, les références et la présence du passage cité dans le texte d'origine.
5. Des alertes conservatrices indiquent les risques d'omission d'exception, de portée temporelle, de quantité ou de contexte adjacent.
6. **Résultat : `needs_review` ou `blocked`, jamais `verified`.** Les propositions ne sont pas envoyées à `stair_reasoner.py`.

## Limitations connues

- Les contrôles lexicaux signalent un risque, ils ne prouvent ni n'infirment l'implication sémantique.
- Les faux positifs et faux négatifs restent possibles, notamment pour les règles anglaises complexes.
- Aucune validation humaine ou modèle NLI indépendant n'est encore branchée.
- La signature SHA-256 sert seulement à identifier un texte, pas à prouver que le PDF d'origine était authentique.
- Le graphe d'inférence n'a pas encore de règles fiables issues des documents.
- Une vérification de citation ne remplace pas la vérification de toutes les conditions applicables, des errata ou des exceptions situées dans une autre section.

## Configuration

```bash
# Par défaut, aucune extraction ne tourne.
export STAIR_RULE_EXTRACTION_ENABLED=0
export STAIR_SHADOW_ENABLED=0

# Pour expérimenter uniquement dans un environnement local de test :
export STAIR_RULE_EXTRACTION_ENABLED=1
```

Lorsque l'extraction est activée, `web_app.py` effectue un appel local Ollama en mode observation. Le rapport console affiche un statut et des comptes, **sans exposer le contenu des passages**. Les réponses HTTP et leur validation existante ne changent pas.

## Tests

```bash
python -m unittest -v test_stair_reasoning test_stair_rule_extractor test_stair_fidelity_gate
python -m py_compile stair_reasoner.py stair_shadow.py stair_rule_extractor.py stair_fidelity_gate.py web_app.py
```

Le jeu complet comporte 34 cas de tests dans ces trois fichiers, sous réserve de leur exécution sur la branche.

## Avant une promotion de règle

Il faudra au minimum un schéma métier couvrant acteur, action, condition, exception, type de règle et portée ; une revue de fidélité par cas ; un protocole de comparaison avec le texte source complet et les sections connexes ; un suivi de versions et de signatures des documents ; des mesures d'erreurs sur les questions de référence.

La règle doit rester `proposed` tant que ces validations ne sont pas passées. Aucune décision de production ne doit dépendre des candidats actuels.

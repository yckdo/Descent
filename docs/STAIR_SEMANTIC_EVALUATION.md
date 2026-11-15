# STAIR — Évaluation sémantique des règles (phase de référence)

## Ce qui est mesuré

Le module `stair_semantic_benchmark.py` compare des règles candidates à un ensemble d'annotations de référence, par correspondance **exacte** des prémisses, de la conclusion et de l'identifiant de passage.

Il calcule, sur les candidats ancrés au texte :
- vrais positifs (règles identiques aux annotations),
- faux positifs (règles candidates différentes),
- faux négatifs (règles de référence manquantes),
- précision, rappel, cas intégralement concordants,
- propositions écartées par le contrôle de citation.

Il n'effectue **aucune preuve d'implication** du sens d'une phrase anglaise. Les métriques d'accord ne mesurent donc pas directement la vérité d'une règle extraite.

## Types de données de référence

- `synthetic_reference` : exemples fictifs, utiles uniquement pour tester le programme.
- `human_reviewed` : annotations validées par un humain, avec identifiant de relecteur et empreintes SHA-256 des extraits.

**Les fichiers ajoutés dans cette phase ne comportent que des tests synthétiques.** Aucun score de qualité sur le véritable manuel Descent ne peut être revendiqué.

## Format d'un cas

```json
{
  "case_id": "case_unique",
  "annotation_status": "human_reviewed",
  "reviewer": "reviewer-id",
  "evidence_hashes": {"S001": "<sha256 exact du passage>"},
  "evidence": [{
    "id": "S001",
    "text": "<passage source>",
    "page": 7,
    "source_refs": ["#/texts/40"]
  }],
  "proposals": {"rules": [{
    "id": "r1",
    "if": ["condition_atom"],
    "then": "consequence_atom",
    "evidence_id": "S001",
    "quote": "<citation exacte>"
  }]},
  "gold_rules": [{
    "if": ["condition_atom"],
    "then": "consequence_atom",
    "source": "S001"
  }]
}
```

Le `reviewer` est une déclaration dans le fichier et non une authentification cryptographique de la personne ; des contrôles de processus externes demeurent nécessaires.

## Guide d'annotation humaine

Pour chaque cas réel : vérifier l'extrait complet et les passages connexes ; écrire les conditions dans l'ordre logique attendu ; contrôler la polarité de la conclusion ; ajouter les exceptions, limites de portée et priorité des errata ; référencer les pages et éléments Docling ; déclarer les cas ambigus sans forcer une règle. Effectuer une double revue indépendante pour les règles critiques.

## Critères pour la phase suivante

1. Construire un jeu d'évaluation réel, représentatif, comprenant contradictions, exceptions et règles multi-sections.
2. Faire annoter les règles **indépendamment** des propositions de Qwen.
3. Réconcilier les divergences entre annotateurs, figer la référence et les empreintes.
4. Mesurer précision/rappel sur des questions non vues, et signaler les règles rejetées par provenance.
5. Ne pas mettre de `verified` automatique à partir du score de benchmark, même parfait.

## Commande

```bash
python -m unittest -v test_stair_reasoning test_stair_rule_extractor test_stair_fidelity_gate test_stair_semantic_benchmark
```

La PR reste en brouillon ; cette étape ne change pas les réponses FastAPI.

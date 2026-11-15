# Jeu de référence STAIR — préparation locale, corpus non publié

Le nouvel outil `prepare_stair_gold_drafts.py` utilise directement la récupération documentaire de `retrieve_stair_section.py` : `build_source_lookup()` puis `retrieve()`. Il ne reconstruit aucun index, ne lance aucune autre recherche, et préserve les pages PDF et les `source_refs` Docling.

## Sur le PC contenant le corpus privé

Depuis le répertoire `descent-stair` et la branche d'intégration, choisir des identifiants de sections **existants** dans `data/stair/document_structure.json`. Par exemple, pour afficher des identifiants sans reproduire le contenu protégé :

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path("data/stair/document_structure.json")
for s in json.loads(p.read_text(encoding="utf-8"))["sections"][:20]:
    print(s["id"], s["title"])
PY
```

Créer des brouillons à partir des IDs choisis :

```bash
python prepare_stair_gold_drafts.py sec_0001 --max-blocks 6
```

Remplacer `sec_0001` par un identifiant figurant dans la structure réelle. Les fichiers sont créés exclusivement dans `validation/semantic_gold_drafts/`, ignoré par Git.

Chaque brouillon conserve : texte de passage, page originale, identifiants Docling, empreinte SHA-256, et champs `proposals`/`gold_rules` vides. Son statut est `pending_review`. **Aucun label `human_reviewed` n'est attribué automatiquement**.

## Revue de référence

1. Un annotateur interprète les passages complets et les sections connexes **sans voir les propositions Qwen**.
2. Il ajoute une règle de référence par déduction applicable, en précisant toutes les prémisses et la conclusion ; si ambigu, ne pas inventer de règle.
3. Une seconde personne revoit indépendamment les règles critiques et réconcilie les divergences.
4. Le statut `human_reviewed` est attribué seulement après contrôle réel, avec identité de l'annotateur. La présence de cette chaîne dans un JSON n'authentifie pas en elle-même la revue.
5. Les `proposals` de Qwen sont ensuite conservées séparément ou insérées dans une copie du cas, puis évaluées par `stair_semantic_benchmark.py` hors production.

## Limites

- Le test automatisé de ce raccordement utilise une petite structure STAIR **synthétique**, afin de ne pas exposer le manuel dans GitHub.
- Les cas réels ne peuvent pas être créés sur GitHub : ils demandent le corpus privé installé sur le PC.
- Un maximum de 6 passages par défaut ne garantit pas le contexte intégral ; valider les renvois, exceptions et errata avant de figer les annotations.
- Le pipeline utilisateur `/api/ask` reste inchangé. Les candidats ne sont pas automatiquement promus dans `stair_reasoner.py`.

## Tests

```bash
python -m unittest -v test_prepare_stair_gold_drafts test_stair_semantic_benchmark
```

# Premier scénario réel STAIR : S002 / déplacement entre héros

## Source et provenance

Ce pilote lit **uniquement** le fichier privé `validation/semantic_gold_drafts/descent_sec_0047.json` créé sur le PC à partir de la section STAIR `sec_0047`. Il vérifie que l'élément `S002` correspond à la page 8 et au document Docling `#/texts/263` et contrôle son empreinte SHA-256.

Le texte complet du manuel n'est **pas** publié dans GitHub.

## Déduction cible provisoire

Question : un héros peut-il traverser la case d'un autre héros, puis terminer son mouvement dans cette même case ?

Deux propositions de règles distinctes :

1. Autre héros = figurine alliée, passage pendant le déplacement : permis.
2. Case déjà occupée par une autre figurine, fin du déplacement : interdite.

Ces deux propositions sont des **annotations provisoires de conception** d'après S002, pas des annotations de référence indépendamment revues. Les cas réels devront être contrôlés avec les restrictions de terrain, notamment le renvoi vers la page 18.

## Exécution

```bash
cd ~/projects/descent-stair
source .venv/bin/activate
git fetch origin
git switch feature/stair-reasoning-integration
git pull --ff-only origin feature/stair-reasoning-integration

python evaluate_stair_s002.py validation/semantic_gold_drafts/descent_sec_0047.json
```

Cette commande ne sollicite **pas** Qwen. Elle teste deux conclusions séparées dans `stair_reasoner.py`, en utilisant les règles provisoires de référence : traverser = `supported`, finir sur une autre figurine = `refuted`. Elle ne mesure pas la fidélité de Qwen.

Pour demander une extraction expérimentale via Ollama **local** :

```bash
python evaluate_stair_s002.py validation/semantic_gold_drafts/descent_sec_0047.json --extract
```

Attention, le vocabulaire des atomes logiques utilisé par Qwen peut différer du référentiel ; une divergence de noms ne démontre donc pas une erreur de compréhension. L'évaluation demeure une première comparaison stricte, pas un score scientifique définitif.

Les réponses API de STAIR ne sont pas modifiées ; aucun candidat Qwen n'est promu comme règle vérifiée.

## Critères d'acceptation à venir

- Confirmer la cohérence du contenu S002 réel avec les deux règles provisoires.
- Examiner la page 18 avant toute généralisation aux terrains et obstacles.
- Produire des annotations de référence indépendantes, avec relecteur et traçabilité.
- Ajouter des tests de portée, exceptions et cas multi-sections.

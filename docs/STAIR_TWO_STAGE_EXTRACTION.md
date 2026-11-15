# Diagnostic S002 — extraction Qwen en deux étapes

## Pourquoi ce pilote ?

Sur la source STAIR `S002` (section `sec_0047`, page 8, référence Docling `#/texts/263`), le premier extracteur Qwen a retourné un JSON correct mais vide (`{"rules": []}`). Cela ne prouve pas une incompréhension du manuel : l'identification des règles et leur formalisation en atomes avaient été demandées simultanément.

Le fichier `stair_two_stage_extractor.py` effectue deux appels à Ollama local :

1. **Compréhension** : identifier permissions, interdictions, conditions et exceptions en anglais, avec un extrait cité mot pour mot.
2. **Formalisation** : convertir exclusivement les propositions ancrées dans une citation réelle en atomes logiques `if` / `then`.

Chaque sortie est contrainte par un schéma JSON distinct. Aucune proposition n'est marquée vérifiée ou automatiquement envoyée dans STAIR Reasoner.

## Sur le PC où STAIR est installé

```bash
cd ~/projects/descent-stair
source .venv/bin/activate
git pull --ff-only origin feature/stair-reasoning-integration

python -m unittest -v test_stair_two_stage_extractor

python stair_two_stage_extractor.py \
  validation/semantic_gold_drafts/descent_sec_0047.json \
  --source S002
```

La commande imprime :
- `stage1_returned` : propositions en langage naturel trouvées par Qwen ;
- `stage1_anchored` : propositions conservées grâce à une citation textuelle exacte ;
- `stage2_returned` : règles logiques proposées ;
- `stage2_accepted` : propositions conformes à la structure et aux citations ;
- `stage2_rejected` : propositions exclues.

La sortie montre les noms d'atomes, pas les passages du manuel. Les noms d'atomes constituent toujours des hypothèses de Qwen, **pas** des règles prouvées. Les tests GitHub utilisent des passages fictifs ; seule l'exécution locale interroge le véritable corpus STAIR et Qwen.

## Périmètre

Cet outil est indépendant du chemin `/api/ask`, qu'il ne modifie pas. Il ne résout pas les exceptions multi-sections, ne valide pas l'inférence sémantique et ne remplace pas une annotation de référence indépendante.

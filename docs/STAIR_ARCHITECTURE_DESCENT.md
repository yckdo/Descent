# Descent V2 — Architecture STAIR et plan d'implémentation

**Statut : conception proposée — 5 novembre 2026**  
**Projet :** `yckdo/Descent`  
**Périmètre initial :** manuel anglais de *Descent: Journeys in the Dark, Second Edition*, questions et réponses en français, traitement **textuel uniquement**.  
**Référence scientifique :** Vineet Kumar et al., *STAIR (STructure Aware Information Retriever): A novel dataset and LLM based retriever for document structure augmentation*, arXiv:2609.03874v2 (13 octobre 2026), https://arxiv.org/abs/2609.03874.

## 1. Qu'est-ce que STAIR ?

**STAIR = STructure Aware Information Retriever**, c'est-à-dire un système de **récupération d'information sensible à la structure du document**.

Son idée est de ne pas découper aveuglément un livre en blocs de taille fixe. À la place, STAIR utilise une représentation hiérarchique du document, notamment sa **table des matières** (ToC), pour retrouver la **section** susceptible de répondre à une question.

Dans l'article, le processus comprend :

1. **Préparation du document :** extraction de la table des matières et association des paragraphes à leurs sections ; génération de questions d'entraînement associées aux bonnes sections.
2. **Apprentissage du routeur :** fine-tuning d'un LLM sur des paires `(question + table des matières) → section feuille`.
3. **Inférence contrainte :** le modèle ne peut sélectionner que des sections valides de la table des matières ; le contenu de la section sélectionnée est ensuite récupéré.

**Distinction fondamentale :** le STAIR du papier est un *retriever génératif de sections*, pas un extracteur de triplets ni un moteur de règles JSON. Notre projet ajoutera des unités de règles structurées *après* le routage documentaire, comme une extension spécifique à Descent. Le premier prototype non entraîné sera **inspiré de STAIR**, et non une reproduction expérimentale exacte de l'article.

Les résultats expérimentaux publiés (par exemple Recall@1 sur SearchTome) **ne prédisent pas** les performances de notre corpus Descent. Nous mesurerons les nôtres.

## 2. Objectif fonctionnel

Répondre localement à des questions telles que :

- « Puis-je traverser une figurine alliée ? »
- « Quand peut-on dépenser une montée de puissance ([SURGE]) ? »
- « Une figurine dans une fosse peut-elle utiliser ses points de mouvement ? »
- « Qu'arrive-t-il à un familier traité comme une figurine ? »

La réponse doit :

- être **en français** et distinguer règle, condition et exception ;
- être fondée sur les **phrases imprimées du manuel**, conservées en anglais dans le corpus ;
- citer les **numéros de pages du PDF original** et, pour le débogage, les références `#/texts/N` ;
- indiquer une incertitude ou une absence de couverture lorsque la règle ne suffit pas ;
- ne jamais inventer une règle, un lien d'index ou une information figurant uniquement dans une illustration non traitée.

## 3. État documentaire disponible

Le prétraitement Docling est terminé et le corpus V3 est **validé structurellement** (la validation humaine exhaustive de tous les passages n'est pas revendiquée).

| Mesure | Valeur |
|---|---:|
| Éléments Docling d'origine | 919 |
| Références exclues après audit | 180 |
| Références textuelles conservées | 739 |
| Éléments textuels normalisés | 658 |
| Fusions de segments | 42 |
| Reclassements d'étiquettes | 6 |
| Corrections textuelles | 3 |
| Occurrences de pictogrammes vérifiées | 77 |
| Pages contenant du texte normalisé | 23 |
| Entrées d'index reconstruites (page PDF 23) | 71, sur 3 colonnes |

**Fichiers locaux d'entrée** :

- `data/normalized/descent_rulebook.json` — texte normalisé, pages, labels, `source_refs` ;
- `data/reference/index_page23.json` — index alphabétique reconstitué ;
- `validation/text_corrections.json` — registre de transformations ;
- `validation/corpus_validation_v3.json` — manifeste et empreintes SHA-256 ;
- `data/raw/descent_rulebook_en.pdf` — preuve visuelle primaire, non publiée.

**Important :** l'index alphabétique page 23 n'est **pas** une table des matières hiérarchique. Il sert de signal conceptuel et de renvoi vérifiable, mais les relations parent/enfant entre sections doivent être reconstruites à partir des titres et de la succession des contenus ; aucune arête ne sera déduite de la simple proximité de deux entrées d'index.

## 4. Architecture cible

```text
PDF original (local, non publié)
  └── Docling déjà exécuté
        └── Corpus V3 validé : pages + textes + références
              ├── Constructeur de hiérarchie documentaire (ToC interne)
              │     ├── sections et sous-sections
              │     ├── identifiants stables
              │     └── passages sources avec pages PDF
              ├── Index alphabétique p.23 (signal complémentaire)
              └── Registre de règles (extension Descent)
                    ├── acteur / action / condition / conséquence
                    ├── exceptions si explicitement attestées
                    └── provenance exacte

Question en français
  └── Routeur STAIR-inspiré (Ollama)
        └── sélection parmi des identifiants de sections AUTORISÉS
              └── récupération locale du contenu de section
                    └── sélection de passages/règles justificatifs
                          └── réponse française Ollama + pages sources
```

**Aucune base vectorielle, aucun embedding et aucune recherche hybride** dans le MVP. Le routeur travaille sur l'arborescence documentaire ; la sélection des IDs doit être validée par le programme. Les passages sources sont récupérés directement par identifiant.

## 5. La structure des données

### 5.1 Section documentaire — unité de récupération principale

Exemple **illustratif** de schéma, pas encore un fichier généré :

```json
{
  "section_id": "sec-p08-move",
  "title": "Move",
  "parent_id": "sec-p08-hero-turn-detail",
  "path": ["Hero Turn in Detail", "Move"],
  "pdf_pages": [8],
  "element_ids": ["#/texts/261", "#/texts/262", "#/texts/263", "#/texts/264", "#/texts/265"],
  "status": "proposed"
}
```

Les `section_id` sont des clés techniques stables ; les pages, titres et références proviennent du corpus réel. On contrôlera l'appartenance de chaque élément à une **et une seule** section principale, avec liens transversaux explicites quand nécessaire. Les légendes et exemples seront conservés et distingués.

### 5.2 Règle structurée — extension métier facultative mais utile

Exemple construit à partir des formulations de la page 8 ; les champs expriment une **interprétation contrôlée**, jamais une nouvelle vérité indépendante :

```json
{
  "rule_id": "rule-movement-friendly-figures",
  "section_id": "sec-p08-move",
  "actor": "figure",
  "action": "move_through_friendly_figure",
  "condition": "the other figure is friendly",
  "effect": "permitted",
  "exception": "the moving figure cannot end movement in an occupied space",
  "source": {"pdf_page": 8, "source_refs": ["#/texts/263"]},
  "review_status": "proposed"
}
```

Les règles extraites automatiquement devront passer un contrôle humain ou une vérification de fidélité avant d'être marquées `verified`. Une règle pourra référencer plusieurs passages et pages. Un simple titre de section ne doit pas produire de règle fictive.

### 5.3 Provenance et preuve

Chaque réponse devra permettre de remonter : `answer → source_refs → éléments normalisés → page PDF`. Ne jamais afficher une page inventée. Les labels `section_header`, `list_item`, `caption` et `text` servent à préserver les frontières sémantiques.

## 6. Comment utiliser Ollama

**Deux fonctions distinctes :**

1. **Routage** : à partir de la question française et d'une hiérarchie documentaire contrôlée, proposer un ou plusieurs identifiants de sections. Le code rejette tout identifiant inconnu et peut demander une deuxième sélection. Pour le pilote, pas de fine-tuning obligatoire : c'est un *prototype STAIR-inspiré*.
2. **Rédaction** : après récupération locale du texte anglais, produire une réponse française courte, exacte, avec citations et mention des exceptions importantes. La rédaction n'a pas le droit de compléter les règles avec des souvenirs externes.

**Étape ultérieure facultative pour une fidélité accrue au papier :** fabriquer des questions synthétiques contrôlées, créer des partitions entraînement/validation/test sans fuite, fine-tuner un modèle de routage vers les sections feuilles, puis contraindre sa sortie aux identifiants autorisés. La faisabilité dépendra de la mémoire GPU et du modèle disponibles ; on ne supposera pas que l'installation actuelle permet un fine-tuning lourd.

## 7. Plan de développement incrémental

| Phase | Livrable principal | Critère d'acceptation |
|---|---|---|
| 10.01 Inventaire | Audit du schéma JSON réel et des titres | Types, labels, provenance et ruptures de pages compris |
| 10.02 Hiérarchie | `build_sections.py`, `sections.json` locaux | IDs uniques, sections couvertes, relations parent/enfant contrôlées |
| 10.03 Ancrage conceptuel | Liaison prudente index alphabétique ↔ sections | Aucun lien créé sans preuve vérifiable |
| 10.04 Pilote | Sections déplacement, combat, dés, fatigue | Passages complets et références de pages conservés |
| 10.05 Routage | Routeur local par sections valides via Ollama | Jamais d'ID de section hors catalogue ; refus explicite possible |
| 10.06 Réponses | Générateur français avec citations PDF | Réponses fondées sur le contenu sélectionné, sans invention |
| 10.07 Évaluation | Jeu de questions humaines couvrant cas et exceptions | Exactitude, Recall@1/@3 des sections, citation et abstention mesurés |
| 10.08 Extension | Toutes les sections textuelles du manuel | Couverture documentée, y compris renvois et cas multi-sections |
| 10.09 Distribution | README, instructions d'installation et commits GitHub | Code publiable sans PDF ni extraction propriétaire |

Chaque phase est validée avant de passer à la suivante. **On ne commence pas par entraîner un modèle** : le premier risque est d'obtenir une hiérarchie ou des citations incorrectes.

## 8. Politique de réponses et de tests

Le jeu d'évaluation devra couvrir au minimum :

- **faits directs** (ex. coût d'entrée dans l'eau, page 18) ;
- **exceptions** (ex. familiers ordinaires vs familiers traités comme figurines, pages 17–18) ;
- **règles à plusieurs sections** (ex. attaque, ligne de vue, portée, dégâts, pages 9 et 12–13) ;
- **ambiguïtés** qui imposent une demande de précision ;
- **questions hors manuel**, devant entraîner une abstention ;
- **renvois** entre page de résumé et règle détaillée, sans les confondre.

Mesures proposées : précision des pages citées ; couverture des conditions et exceptions ; taux de réponses non sourcées ; Recall@1 et Recall@3 des sections attendues ; abstention correcte. Une réponse fluide mais non justifiée est un échec.

## 9. Périmètre et limites assumées

- **MVP textuel uniquement** : ne pas interpréter les images, cartes ou figures. Conserver les **légendes et exemples rédigés** du manuel.
- **Source anglaise, réponses françaises** : ne pas introduire de traduction officielle non justifiée ; conserver au besoin les noms anglais du manuel.
- **Héros / Seigneur du Mal** : séparation des profils, spoilers et rôles prévue pour une version ultérieure, non activée dans le MVP.
- **Coquille `quite` page 19** : conservée car imprimée dans la source.
- **Ponctuation résiduelle** : certains tirets et espaces restent à contrôler ; ne pas annoncer une fidélité absolue.
- **Pas de comparaison avec un système RAG vectoriel/hybride** dans ce projet.
- **Pas de nouveau moteur d'extraction PDF** : Docling reste la source d'extraction existante.

## 10. GitHub et droits de diffusion

Dépôt de code : https://github.com/yckdo/Descent

À publier : code Python, tests sur exemples synthétiques, schémas, README, documentation d'architecture et résultats agrégés non reconstructifs. 

À garder **hors du dépôt public** : PDF du manuel, JSON/Markdown du texte intégral, registres contenant de longs extraits du manuel, et secrets d'authentification. Les fichiers `data/` et `validation/` sont actuellement ignorés par Git ; la documentation publique peut vivre sous `docs/`.

Les scripts publiés à ce stade nécessitent encore les fichiers locaux. Le README devra le signaler clairement, sans prétendre que le dépôt fonctionne immédiatement après un simple clonage.

## 11. Première action technique prévue

Avant d'écrire `build_sections.py`, inspecter le **schéma réel** de `data/normalized/descent_rulebook.json`, vérifier l'ordre des labels et les titres de niveau supérieur, puis produire un inventaire des sections candidates. Aucun code ne doit supposer une hiérarchie qui n'est pas attestée par le JSON ni par les pages du manuel.

---

**Source principale :** Kumar et al., arXiv:2609.03874v2, sections 1 et 4. Les données chiffrées du corpus Descent proviennent des validations locales déjà exécutées dans le projet. L'architecture Descent présentée ici est une **adaptation proposée**, pas l'implémentation officielle de STAIR.

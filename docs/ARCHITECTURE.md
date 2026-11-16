# Architecture — Descent STAIR V2

**Version documentaire :** projet en cours  
**Dernière revue :** 16 novembre 2026

## 1. Objectif de l'architecture

Descent STAIR V2 doit répondre aux questions des joueurs en utilisant les règles contenues dans les documents du jeu.

Le système doit garantir autant que possible :
- La traçabilité entre chaque réponse et les documents sources.
- La prise en compte des conditions, interdictions et exceptions.
- La distinction entre une règle attestée et une interprétation proposée par l'IA.
- Le fonctionnement local du modèle d'intelligence artificielle.
- La possibilité future d'ajouter des documents sans modifier le code.

Une réponse doit pouvoir être vérifiée à partir des passages qui la justifient.

## 2. Composants principaux

| Composant | Responsabilité |
|---|---|
| **Interface web** | Permettre aux joueurs de poser des questions et consulter les réponses |
| **FastAPI** | Recevoir les requêtes et coordonner les traitements |
| **STAIR** | Identifier les sections pertinentes et récupérer les passages sources |
| **Qwen / Ollama** | Interpréter les textes et formuler des réponses en français |
| **Contrôle documentaire** | Vérifier les références et citations produites |
| **Moteur de raisonnement** | Vérifier des conclusions à partir de règles structurées |
| **Bibliothèque documentaire** | Conserver les documents, versions, sections et règles |

Les cinq premiers composants sont présents, avec des niveaux de maturité différents. Le moteur de raisonnement est expérimental. La bibliothèque multi-documents reste à développer.

## 3. Architecture actuelle

### 3.1 Parcours d'une question

```text
JOUEUR
  |
Interface web
  |
FastAPI — /api/ask
  |
Recherche STAIR
  |
Sélection des sections du manuel
  |
Récupération des passages et références
  |
Qwen local avec Ollama
  |
Réponse structurée en français
  |
Contrôle des citations
  |
Réponse affichée au joueur
```

Le serveur utilise notamment `web_app.py`. La recherche s'appuie sur les structures locales produites à partir du manuel. Les références permettent de retrouver les pages et passages employés.

**Limite actuelle :** le contrôle des citations ne suffit pas à garantir la justesse du raisonnement.

### 3.2 Rôle exact de STAIR

STAIR est une approche de recherche documentaire sensible à la structure. Elle utilise sections, titres, références et relations documentaires plutôt qu'un découpage arbitraire.

Dans Descent STAIR V2, son rôle est d'identifier les sections, de récupérer les passages, de préserver leurs références et de fournir un contexte contrôlé à Qwen.

Ce projet constitue une **adaptation inspirée de STAIR**, non une reproduction complète du routeur entraîné décrit par Kumar et al., *STAIR (STructure Aware Information Retriever)*, [arXiv:2609.03874v2](https://arxiv.org/abs/2609.03874).

### 3.3 Corpus initial

Le corpus provient du manuel anglais de *Descent: Journeys in the Dark — Second Edition*, extrait avec Docling puis normalisé et audité. Il comprend notamment :
- 143 sections documentaires identifiées ;
- 71 entrées d'index associées aux sections ;
- des références aux pages PDF et éléments Docling ;
- des corrections et contrôles du texte extrait.

Les données du manuel restent locales. PDF, extraits intégraux et registres privés ne sont pas publiés sur GitHub.

La structure initiale est contrôlée, mais chaque règle et interprétation n'a pas été intégralement validée.

## 4. Raisonnement sur les règles

### 4.1 Pourquoi un moteur complémentaire ?

Qwen peut produire une réponse plausible en omettant une condition ou une exception. Le raisonnement vise donc à séparer récupération, interprétation, formalisation et vérification des conclusions.

### 4.2 Extraction expérimentale

```text
Passage documentaire
  |
Qwen : permissions, interdictions, conditions et exceptions
  |
Validation de citation
  |
Qwen : formalisation conditions → conséquence
  |
Validation structurelle
  |
Propositions à examiner (jamais approuvées automatiquement)
```

Modules : `stair_two_stage_extractor.py`, `stair_rule_extractor.py`, `stair_fidelity_gate.py`, `stair_reasoner.py` et `stair_semantic_benchmark.py`.

Ce pipeline **ne valide pas encore le sens** des règles extraites. Les propositions Qwen restent expérimentales.

### 4.3 Exemple : déplacement entre figurines

Le manuel distingue le passage à travers une figurine alliée, les espaces bloqués et l'interdiction de terminer un déplacement sur une case occupée. Une interdiction générale ne doit pas effacer une permission particulière.

Le test S002 (section `sec_0047`, page 8, référence Docling `#/texts/263`) a montré qu'une proposition de permission pouvait être perdue lors de la formalisation, parce que sa citation avait changé. Le diagnostic identifie désormais ce rejet ; l'association par identifiants stables reste à développer.

### 4.4 Limites actuelles

Le moteur logique expérimental traite des implications simples et fournit des éléments de preuve. Il ne garantit pas encore la bonne interprétation sémantique, les exceptions/priorités, la couverture des règles, les conflits multi-sections ou les errata.

Les règles proposées par Qwen ne sont **pas** automatiquement promues dans le parcours de réponse des joueurs.

## 5. Architecture cible : plusieurs documents

```text
ADMINISTRATEUR
  |
Interface web d'administration
  |
Importation / mise à jour des PDF
  |
Extraction, normalisation et contrôle
  |
Bibliothèque documentaire versionnée
  +-- Documents et versions
  +-- Sections et passages
  +-- Références et citations
  +-- Règles et exceptions
  +-- Statuts de validation
  |
Index STAIR multi-documents
  |
Recherche et réponses aux joueurs
```

Cette architecture est **prévue, non entièrement implémentée**.

### 5.1 Versions

Chaque document aura un identifiant stable et un historique. Une mise à jour conservera l'ancienne version, identifiera les différences, signalera les validations obsolètes, exigera les revues nécessaires puis permettra une publication contrôlée et un retour arrière.

### 5.2 Sources et priorités

Les documents seront distingués en manuel officiel, extension officielle, FAQ/errata et règles personnalisées.

Le type ou la date ne déterminent **pas** automatiquement les priorités. Remplacement, exception, complément ou conflit devront être explicitement attestés. Les règles personnalisées ne modifieront pas silencieusement les règles officielles.

## 6. Sécurité et confidentialité

- Qwen fonctionne en local via Ollama.
- Les documents privés restent hors du dépôt public.
- L'administration exige authentification et autorisations spécifiques.
- Les imports doivent être contrôlés et isolés.
- Les textes documentaires ne doivent pas être traités comme des instructions système.
- Chaque publication et modification devra être traçable.
- Aucune règle non validée ne sera activée automatiquement.

Un modèle local n'est pas, à lui seul, une preuve d'isolation réseau. Les procédures techniques sont dans [Exploitation](EXPLOITATION.md).

## 7. Principes techniques

**Responsabilités séparées :** STAIR recherche ; Qwen interprète ; les validateurs contrôlent ; le moteur logique déduit.

**Provenance conservée :** relier chaque conclusion à la version, aux pages et aux passages.

**Citation ≠ vérité :** une citation exacte peut accompagner une erreur de raisonnement.

**Échec prudent :** signaler une information insuffisante ou contradictoire plutôt qu'inventer.

**Données préservées :** aucune mise à jour ne détruit sans contrôle le corpus et ses validations.

**Qualité mesurée :** tests humains indépendants des propositions de Qwen.

## 8. Périmètre

- [Administration](ADMINISTRATION.md) : opérations documentaires et validation.
- [Exploitation](EXPLOITATION.md) : installation, configuration, maintenance.
- [Roadmap](ROADMAP.md) : travaux restants et priorités.

---

**Principe central : chaque réponse doit pouvoir être expliquée et retracée jusqu'aux règles documentaires qui la justifient.**

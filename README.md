# Descent STAIR V2

**Assistant intelligent pour les règles de Descent: Journeys in the Dark — Second Edition**

## 1. Présentation

Descent STAIR V2 est un assistant conçu pour répondre en français aux questions sur les règles du jeu de société *Descent: Journeys in the Dark — Second Edition*.

Son objectif est de fournir des réponses précises, compréhensibles et justifiées par les documents du jeu.

Le système associe trois éléments :

- **STAIR** : retrouve les passages pertinents dans les documents en respectant leur structure.
- **Qwen** : interprète les passages retrouvés et rédige des réponses en français.
- **Moteur de vérification** : contrôle les citations et développe progressivement des mécanismes de vérification du raisonnement.

Le projet privilégie la fidélité aux règles plutôt que la production d'une réponse à tout prix.

## 2. Objectifs

L'application doit permettre de :

- Poser des questions sur les règles en langage naturel.
- Obtenir des réponses accompagnées de leurs sources.
- Prendre en compte les conditions, restrictions et exceptions.
- Signaler lorsqu'une réponse ne peut pas être suffisamment justifiée.
- Consulter plusieurs documents : manuel de base, extensions, FAQ et errata.
- Administrer les documents et les règles depuis une interface web.

Les deux derniers objectifs nécessitent encore des développements.

## 3. Fonctionnement général

**Question du joueur → Recherche STAIR → Interprétation Qwen → Vérification → Réponse sourcée**

STAIR sélectionne les sections pertinentes et récupère leurs passages avec leurs références documentaires. Qwen utilise ces informations pour répondre à la question.

Les contrôles documentaires existants vérifient notamment les citations. Un moteur de raisonnement plus avancé est en cours de développement pour traiter les déductions et les exceptions.

Une citation valide ne garantit pas, à elle seule, que l'interprétation d'une règle est correcte.

## 4. État du projet

| Fonctionnalité | État |
|---|---|
| Extraction et structuration du manuel initial | Opérationnelle |
| Recherche documentaire STAIR | Opérationnelle |
| Réponses en français avec Qwen local | Opérationnelle, qualité à consolider |
| Vérification des citations | Intégrée |
| Extraction automatique de règles logiques | Expérimentale |
| Vérification du raisonnement | Expérimentale |
| Importation de plusieurs documents | À développer |
| Administration web des documents et règles | À développer |

**Le projet est en développement.** Les tests des composants sont encourageants, mais la fiabilité du raisonnement sur l'ensemble des règles n'est pas encore démontrée.

## 5. Technologies principales

- **Python** : traitement documentaire et logique applicative.
- **FastAPI** : serveur de l'application.
- **Docling** : extraction et structuration des PDF.
- **STAIR** : recherche documentaire fondée sur les sections et leurs références.
- **Ollama et Qwen** : traitement local par intelligence artificielle.
- **GitHub** : gestion du code, des évolutions et des tests automatisés.

Les documents du jeu et les données privées restent stockés localement ; ils ne doivent pas être publiés dans ce dépôt public.

## 6. Documentation

| Document | Utilité |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Comprendre le fonctionnement technique du système |
| [Administration](docs/ADMINISTRATION.md) | Ajouter et gérer les documents, règles et mises à jour |
| [Exploitation](docs/EXPLOITATION.md) | Installer, démarrer, tester et maintenir l'application |
| [Roadmap](docs/ROADMAP.md) | Connaître l'avancement, les problèmes et les prochaines actions |

Ces cinq documents constituent la référence du projet.

## 7. Développement et contributions

Le dépôt GitHub contient le code source, les tests et la documentation. Les évolutions sont développées sur des branches dédiées et vérifiées avant leur intégration.

Les modifications touchant aux règles du jeu doivent conserver leur provenance et faire l'objet d'une validation adaptée. Le processus de développement et les travaux restants sont suivis dans la [Roadmap](docs/ROADMAP.md).

---

**Objectif final : rendre les règles de Descent accessibles grâce à un assistant documentaire fiable, explicable et administrable depuis le web.**

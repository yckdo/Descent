# Administration — Descent STAIR V2

**Dernière revue :** 16 novembre 2026  
**Statut :** interface d'administration documentaire à développer

## 1. Objectif

Permettre à un utilisateur autorisé de gérer les documents et règles depuis un navigateur, **sans commande Linux ni modification de code** : ajouter, consulter, modifier, valider, publier, archiver et restaurer.

Ce document décrit le **fonctionnement cible**, pas une interface déjà disponible.

## 2. Accès

| Rôle | Autorisations |
|---|---|
| **Administrateur** | Documents, règles, versions, validations et publications |
| **Joueur** | Questions et réponses autorisées |

L'authentification d'administration sera distincte de l'accès au chat, avec contrôle des droits et journal d'audit.

## 3. Documents

### Ajouter un PDF

Dans **Documents → Ajouter un document**, renseigner titre, type (manuel, extension, FAQ, errata…), langue, version/date et PDF.

Le traitement prévu :
1. Contrôler le fichier.
2. Extraire le contenu avec Docling.
3. Détecter titres, sections et passages.
4. Conserver pages, références et identifiants.
5. Présenter les résultats et anomalies pour contrôle.
6. Laisser le document en brouillon jusqu'à validation.

### Consulter

La liste présentera titre, type, version, statut et dernière modification. Chaque document donnera accès aux sections, passages et règles associées.

### Mettre à jour

Importer une nouvelle version **sans écraser** l'ancienne. STAIR comparera les différences, signalera les règles/validations concernées et soumettra les changements à revue. Un passage inchangé ne conserve sa validation que si son identité **et son contexte** sont vérifiés.

### Désactiver ou archiver

Un document désactivé ne sert plus aux nouvelles réponses, sauf sélection explicite et autorisée d'une version. Son historique reste accessible. Une suppression définitive est exceptionnelle et confirmée.

## 4. Règles

### Ajouter une règle

Depuis un document et une section, choisir **Ajouter une règle**.

| Champ | Contenu |
|---|---|
| Identifiant et titre | Référence stable et nom lisible |
| Source | Document, version, page et passage |
| Acteur et action | Entité concernée et opération |
| Conditions | Situations d'application |
| Conséquence | Autorisation, interdiction, effet ou définition |
| Exceptions | Cas particuliers explicitement documentés |
| Statut | Niveau de validation |

Aucune règle sans source. Les règles maison restent distinctes des règles officielles.

### Modifier

Toute correction produit une nouvelle révision consultable ; une règle publiée modifiée repasse en validation avant activation.

### Propositions Qwen

Les propositions automatiques sont des **brouillons non vérifiés**. L'administrateur compare la phrase source et l'interprétation, corrige les conditions et exceptions, puis valide ou rejette. Une revue humaine ne remplace pas les contrôles de cohérence.

## 5. Validation et publication

| Statut | Signification |
|---|---|
| **Brouillon** | Créé, non vérifié |
| **À vérifier** | Prêt pour revue |
| **Validé** | Contrôles requis effectués |
| **Publié** | Disponible pour les réponses |

Les éléments peuvent aussi être rejetés ou archivés.

Cycle cible :
1. Examiner les éléments.
2. Vérifier références, structure et cohérence.
3. Examiner contradictions et omissions.
4. Confirmer explicitement la publication.
5. Activer une version cohérente de la bibliothèque.

Une publication échouée laisse la version antérieure active ; aucune règle proposée n'est publiée automatiquement.

## 6. Contradictions et priorités

Manuel, extension, errata et règle maison peuvent se compléter ou se contredire. Il faut enregistrer la relation vérifiée : **exception, remplacement, complément ou conflit non résolu**.

Ni la date ni le statut « officiel » ne suffisent à calculer toutes les priorités. Un conflit critique non résolu doit empêcher une conclusion trompeuse ou imposer un signalement d'incertitude.

## 7. Historique et retour arrière

Conserver les versions, révisions, acteurs, dates, changements et sources. La restauration d'une ancienne publication doit vérifier l'intégrité des références avant activation.

## 8. Sécurité

- Accès authentifié et autorisé.
- Contrôle des PDF (type, taille, contenu) et des chemins.
- Traitements isolés et résistance aux instructions injectées dans les documents.
- Validation explicite avant activation.
- Journalisation des opérations.
- Stockage privé des documents et versions ; jamais de secrets dans GitHub.

Les sauvegardes et interventions système sont traitées dans [Exploitation](EXPLOITATION.md).

## 9. État actuel

| Fonctionnalité | État |
|---|---|
| Extraction et structure du manuel initial | Existantes |
| Recherche et citations | Existantes |
| Propositions automatiques de règles | Expérimentales |
| Administration web, import PDF, versions et éditeur de règles | À développer |
| Publication contrôlée et restauration web | À développer |

## 10. Critères de réussite

Un administrateur doit pouvoir, **depuis le navigateur** : importer et contrôler un document, le publier, ajouter et valider une règle, comparer des versions, corriger/désactiver une règle et restaurer une publication. Un joueur ne doit jamais pouvoir accomplir ces actions.

Chaque scénario sera couvert par des tests avant mise en production.

---

**Principe central : aucun document ni aucune règle non validée ne devient actif automatiquement.**

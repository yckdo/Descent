# Roadmap — Descent STAIR V2

**Dernière revue :** 16 novembre 2026  
**Statut :** développement et validation  
**Objectif :** assistant de règles fiable, sourcé et administrable depuis le web.

## 1. État actuel

STAIR et Qwen local permettent d'interroger le manuel initial, avec des références documentaires contrôlées. Le raisonnement formel est expérimental et **n'approuve pas les réponses aux joueurs**. L'administration web et le multi-PDF restent à développer.

**La qualité globale des réponses et la mise en production définitive ne sont pas validées.**

## 2. Fonctionnalités

| Fonctionnalité | État |
|---|---|
| Extraction/normalisation du manuel initial | Réalisé |
| Structure et recherche STAIR | Réalisé |
| Réponses françaises Qwen local | Fonctionnel, à fiabiliser |
| Citations et contrôle documentaire | Intégrés |
| Signalements des testeurs | Intégrés |
| Extraction de règles et déduction logique | Expérimentales |
| Exceptions et priorités complètes | Non terminées |
| Bibliothèque multi-PDF | À développer |
| Administration web | À développer |
| Versions documentaires et restauration | À développer |

## 3. Lots de travail

### Lot 1 — Stabiliser l'extraction et le raisonnement (critique)

- [x] Moteur logique expérimental.
- [x] Extraction Qwen en deux étapes.
- [x] Contrôles de citations et diagnostic des pertes.
- [x] Donner un identifiant stable à chaque proposition et réattacher sa citation sans recopie (tests automatisés).
- [ ] Vérifier sur le corpus réel que permissions, interdictions et exceptions sont préservées.
- [ ] Détecter contradictions et omissions.
- [ ] Étendre les tests de non-régression.

**Réussite :** identité/provenance garanties dans le pipeline, pertes signalées et aucune approbation automatique.

### Lot 2 — Bibliothèque multi-documents (critique)

- [ ] Généraliser Docling et l'import au-delà du manuel initial.
- [ ] Identifiants et versions de documents.
- [ ] Pages, sections, références et empreintes conservées.
- [ ] Manuel, extensions, FAQ et errata.
- [ ] Recherche STAIR multi-documents.
- [ ] Comparaison des versions, invalidation des annotations affectées.
- [ ] Préserver le corpus initial.

**Réussite :** importer puis interroger un second PDF sans régression du premier.

### Lot 3 — Administration web (haute)

- [ ] Interface sécurisée et autorisations.
- [ ] Ajouter/consulter documents et passages.
- [ ] Ajouter/modifier règles et examiner les propositions Qwen.
- [ ] Valider et publier.
- [ ] Historique et restauration.

**Réussite :** opérations courantes depuis le navigateur, sans terminal.

### Lot 4 — Raisonnement vérifiable (critique)

- [ ] Schéma couvrant acteurs, actions, conditions, exceptions.
- [ ] Règles générales et cas particuliers.
- [ ] Relations entre règles de différents documents.
- [ ] Permissions, interdictions, information insuffisante.
- [ ] Priorités attestées, contradictions, preuves et abstention.

**Réussite :** conclusions sourcées et correctes sur les cas de référence, sans déductions non justifiées.

### Lot 5 — Validation réelle (critique)

- [x] Outils de préparation des références.
- [x] Neuf sections réelles préparées (29 passages).
- [x] Premier diagnostic de S002.
- [ ] Annotations revues indépendamment de Qwen.
- [ ] Questions représentatives du manuel.
- [ ] Déplacement, combat, états, monstres, capacités.
- [ ] Cas multi-sections, exceptions et contradictions.
- [ ] Mesures précision/rappel, omissions et refus.
- [ ] Seuils d'acceptation définis avant déploiement.

**Réussite :** mesures fiables sur des annotations humaines indépendantes.

### Lot 6 — Intégration (haute)

- [ ] Raccorder multi-documents et règles validées à `/api/ask`.
- [ ] Afficher preuves, limites et incertitudes.
- [ ] Séparer droits des joueurs et administrateurs.
- [ ] Isoler les imports longs des demandes de chat.
- [ ] Tester mises à jour et retours arrière.

**Réussite :** chat utilisant uniquement les documents publiés et les règles autorisées.

### Lot 7 — Déploiement (après validation)

- [ ] Installation reproductible et service.
- [ ] Authentification, accès réseau et isolation Ollama.
- [ ] Sauvegardes et restauration testée.
- [ ] Performances sur matériel cible.
- [ ] Recette finale des API et interfaces.
- [ ] Validation, fusion et déploiement explicites.

**Réussite :** application stable, contrôlée, sécurisée et restaurable.

## 4. Problèmes connus

| Sujet | Risque | Action |
|---|---|---|
| S002 | Permission perdue par changement de citation | Identifiants de propositions |
| Exceptions | Priorités mal représentées | Étendre schéma et vérifications |
| Sémantique | Citation exacte ≠ conclusion exacte | Références humaines indépendantes |
| Scripts initialement mono-manuel | Rejet ou corruption d'autres corpus | Généraliser sans écraser |
| Administration web | Absente | Bibliothèque et interface |
| Sauvegardes | Pas encore industrialisées | Automatiser et tester |
| Confidentialité | Corpus privé | Exclusion Git et contrôle d'accès |

## 5. Organisation GitHub

Dépôt : [yckdo/Descent](https://github.com/yckdo/Descent).

Branches relevées : `main`, `feature/chat-ouvert`, `feature/stair-reasoning`, `feature/stair-reasoning-integration`.

[PR n° 1](https://github.com/yckdo/Descent/pull/1) : **ouverte en brouillon**, de la branche d'intégration vers `feature/chat-ouvert`.

Aucune fusion ni aucun déploiement sans accord explicite. Données privées conservées hors GitHub.

## 6. Prochaine action

**Documentation :** validation des cinq documents, publication sur `feature/stair-reasoning-integration`, retrait des six anciennes fiches redondantes, vérification des liens. L'historique Git conserve les anciens documents.

**Développement suivant :** l'identité et la citation entre les deux étapes ont été corrigées dans `stair_two_stage_extractor.py` et couvertes par des tests unitaires. **À faire :** tester localement avec Qwen sur S002, examiner les omissions et exceptions, puis poursuivre les lots selon leurs dépendances.

## 7. Définition de « terminé »

- [ ] Documents ajoutés et mis à jour depuis le navigateur.
- [ ] Règles examinées, corrigées et publiées.
- [ ] Exceptions vérifiées sur les scénarios de référence.
- [ ] Réponses sourcées, preuves appropriées.
- [ ] Erreurs, contradictions et lacunes signalées.
- [ ] Critères de qualité atteints sur tests réels.
- [ ] Confidentialité et accès administratifs protégés.
- [ ] Sauvegardes/restaurations testées.
- [ ] Déploiement final validé.

---

**Suivi : chaque livraison actualise uniquement les tâches/problèmes concernés ; cocher après vérification.**

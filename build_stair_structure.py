
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

INVENTORY = ROOT / "data/stair/section_inventory.json"
INDEX_LINKS = ROOT / "data/stair/index_links.json"

OUTPUT = ROOT / "data/stair/document_structure.json"
REPORT = ROOT / "validation/stair_structure_review.txt"

EXPECTED_SECTIONS = 143
EXPECTED_INDEX_ENTRIES = 71
EXPECTED_RELATIONS = 24


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    inventory = load(INVENTORY)
    index_data = load(INDEX_LINKS)

    original_sections = inventory["sections"]
    index_nodes = index_data["index_nodes"]
    original_links = index_data["proposed_parent_child_links"]

    require(
        len(original_sections) == EXPECTED_SECTIONS,
        "Nombre de sections inattendu"
    )
    require(
        len(index_nodes) == EXPECTED_INDEX_ENTRIES,
        "Nombre d'entrées d'index inattendu"
    )
    require(
        len(original_links) == EXPECTED_RELATIONS,
        "Nombre de relations inattendu"
    )

    section_ids = [s["id"] for s in original_sections]

    require(
        len(section_ids) == len(set(section_ids)),
        "Identifiants de sections dupliqués"
    )

    by_id = {
        section["id"]: section
        for section in original_sections
    }

    # Associer chaque entrée d'index à une section précise.
    indexes_by_section = defaultdict(list)
    seen_index_ids = set()

    for node in index_nodes:
        sid = node["section_id"]
        iid = node["index_id"]

        require(sid in by_id, f"Section inconnue : {sid}")
        require(
            iid not in seen_index_ids,
            f"Entrée d'index dupliquée : {iid}"
        )
        require(
            node["index_page"] == by_id[sid]["page"],
            f"Page incohérente pour {iid}"
        )

        seen_index_ids.add(iid)

        indexes_by_section[sid].append({
            "index_id": iid,
            "title": node["index_title"],
            "level": node["index_level"],
            "match_method": node["match_method"],
            "evidence_pdf_page": 23,
        })

    require(
        len(indexes_by_section) == 71,
        "Les entrées ne pointent pas vers 71 sections distinctes"
    )

    # Une relation de l'index n'est pas une preuve
    # d'imbrication physique dans le texte.
    relations = []
    seen_relations = set()

    for link in original_links:
        parent = link["parent_section_id"]
        child = link["child_section_id"]
        key = (parent, child)

        require(
            parent in by_id and child in by_id,
            f"Relation avec une section inconnue : {key}"
        )
        require(
            parent != child,
            f"Relation réflexive : {key}"
        )
        require(
            key not in seen_relations,
            f"Relation dupliquée : {key}"
        )
        require(
            link["relation"] == "index_subentry",
            f"Type de relation inattendu : {key}"
        )

        evidence = link["evidence"]

        require(
            evidence["source_pdf_page"] == 23,
            f"Provenance de l'index incorrecte : {key}"
        )
        require(
            evidence["parent_index_id"] in seen_index_ids
            and evidence["child_index_id"] in seen_index_ids,
            f"Preuve d'index absente : {key}"
        )

        parent_levels = [
            entry["level"]
            for entry in indexes_by_section[parent]
            if entry["index_id"] == evidence["parent_index_id"]
        ]
        child_levels = [
            entry["level"]
            for entry in indexes_by_section[child]
            if entry["index_id"] == evidence["child_index_id"]
        ]

        require(
            parent_levels == [0] and child_levels == [1],
            f"Niveaux d'index incompatibles : {key}"
        )

        seen_relations.add(key)

        relations.append({
            "type": "index_subentry",
            "from_section_id": parent,
            "to_section_id": child,
            "evidence": {
                "document": "descent_rulebook_en.pdf",
                "pdf_page": 23,
                "parent_index_id": evidence["parent_index_id"],
                "child_index_id": evidence["child_index_id"],
            },
            "validation_status": "validated_as_index_relation",
            "physical_containment_inferred": False,
        })

    # Séparer explicitement les sections récapitulatives
    # de la page 24 des sections détaillées.
    sections = []

    for original in original_sections:
        sid = original["id"]
        page = original["page"]

        require(
            original["heading_refs"],
            f"Titre sans source : {sid}"
        )
        require(
            original["title"].strip(),
            f"Titre vide : {sid}"
        )

        kind = (
            "rules_summary"
            if page == 24
            else "document_section"
        )

        sections.append({
            "id": sid,
            "title": original["title"],
            "pdf_page": page,
            "kind": kind,
            "heading_refs": original["heading_refs"],
            "content_refs": original["content_refs"],
            "content_element_count": original["element_count"],
            "content_scope": "same_page_until_next_heading",
            "index_entries": indexes_by_section[sid],
            "physical_parent_id": None,
            "physical_hierarchy_status": "not_established",
        })

    # Vérifier le nombre de sections sans entrée d'index.
    unindexed = [
        section["id"]
        for section in sections
        if not section["index_entries"]
    ]

    require(
        len(unindexed) == 72,
        f"Sections hors index inattendues : {len(unindexed)}"
    )

    summary_sections = [
        section["id"]
        for section in sections
        if section["kind"] == "rules_summary"
    ]

    # Contrôle élémentaire de l'absence de cycles
    # dans les relations de navigation.
    children = defaultdict(list)

    for relation in relations:
        children[relation["from_section_id"]].append(
            relation["to_section_id"]
        )

    visiting = set()
    visited = set()

    def visit(node):
        if node in visiting:
            raise ValueError(
                f"Cycle dans les relations d'index : {node}"
            )
        if node in visited:
            return

        visiting.add(node)

        for child in children[node]:
            visit(child)

        visiting.remove(node)
        visited.add(node)

    for sid in section_ids:
        visit(sid)

    # Génération déterministe.
    result = {
        "schema_version": "descent-stair-structure-0.1",
        "source": {
            "corpus": "data/normalized/descent_rulebook.json",
            "inventory": "data/stair/section_inventory.json",
            "inventory_sha256": sha256(INVENTORY),
            "index_links": "data/stair/index_links.json",
            "index_links_sha256": sha256(INDEX_LINKS),
        },
        "validation": {
            "index_relations_validated": True,
            "physical_hierarchy_validated": False,
            "cross_page_continuity_validated": False,
            "full_semantic_review_completed": False,
        },
        "sections": sections,
        "relations": relations,
        "unindexed_section_ids": unindexed,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8",
    )

    counts = Counter(
        section["kind"] for section in sections
    )

    lines = [
        "=== STRUCTURE DOCUMENTAIRE STAIR V0.1 ===",
        "",
        f"Sections : {len(sections)}",
        f"Correspondances index : {len(index_nodes)}",
        f"Relations d'index : {len(relations)}",
        f"Sections hors index : {len(unindexed)}",
        f"Sections récapitulatives : {len(summary_sections)}",
        "",
        "=== TYPES DE SECTIONS ===",
    ]

    for kind, count in sorted(counts.items()):
        lines.append(f"{kind} : {count}")

    lines.extend([
        "",
        "=== RELATIONS D'INDEX VALIDÉES ===",
    ])

    for relation in relations:
        parent = by_id[relation["from_section_id"]]
        child = by_id[relation["to_section_id"]]

        lines.append(
            f"{parent['id']} [{parent['title']}] "
            f"=> {child['id']} [{child['title']}]"
        )

    lines.extend([
        "",
        "=== SECTIONS RÉCAPITULATIVES ===",
    ])

    for sid in summary_sections:
        section = by_id[sid]
        lines.append(f"{sid} | {section['title']}")

    lines.extend([
        "",
        "=== LIMITES ===",
        "- Pas de hiérarchie physique inventée.",
        "- Les relations proviennent de l'index page 23.",
        "- Les contenus sont délimités par page.",
        "- Les continuités entre pages restent à examiner.",
        "- Le texte complet reste dans le corpus local.",
        "",
        "Aucune modification du corpus V3.",
    ])

    REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("=== CONSTRUCTION STAIR V0.1 ===")
    print("Sections :", len(sections))
    print("Correspondances index :", len(index_nodes))
    print("Relations d'index :", len(relations))
    print("Sections hors index :", len(unindexed))
    print("Sections récapitulatives :", len(summary_sections))
    print("Cycles détectés : 0")
    print("Erreurs : 0")
    print("Structure :", OUTPUT)
    print("Rapport :", REPORT)
    print("Hiérarchie physique non encore validée")


if __name__ == "__main__":
    main()

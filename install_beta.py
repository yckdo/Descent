"""Installe le module de feedback dans web_app.py sans écraser l'interface existante."""
import ast
from pathlib import Path

path = Path("web_app.py")
if not path.exists():
    raise SystemExit("web_app.py absent : exécuter depuis ~/projects/descent-stair")
source = path.read_text(encoding="utf-8")
if "install_beta_feedback(app)" in source:
    print("Extension bêta déjà installée : aucune modification.")
    raise SystemExit(0)
tree = ast.parse(source)
assignments = [
    node for node in tree.body
    if isinstance(node, (ast.Assign, ast.AnnAssign))
    and ((isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "app" for t in node.targets))
         or (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "app"))
    and isinstance(node.value, ast.Call)
    and ((isinstance(node.value.func, ast.Name) and node.value.func.id == "FastAPI")
         or (isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "FastAPI"))
]
if len(assignments) != 1:
    raise SystemExit("Affectation app = FastAPI(...) non unique : aucune modification.")
lines = source.splitlines(keepends=True)
position = assignments[0].end_lineno
updated = "".join(lines[:position]) + "\nfrom beta_feedback import install_beta_feedback\ninstall_beta_feedback(app)\n" + "".join(lines[position:])
ast.parse(updated)
backup = Path("web_app.py.bak_before_beta_feedback")
if not backup.exists():
    backup.write_text(source, encoding="utf-8")
path.write_text(updated, encoding="utf-8")
print("Feedback API installé : POST /api/feedback")
print("Sauvegarde :", backup)

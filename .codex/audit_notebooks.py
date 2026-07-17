import ast
import json
import pathlib
import re

FILES = [
    "preprocess_original.ipynb",
    "precompute_original.ipynb",
    "training_original.ipynb",
    "baselines_original.ipynb",
]

BASE = pathlib.Path("notebooks/archive")
PATH_RE = re.compile(r"[A-Za-z]:\\[^\"']+|/(?:kaggle|content|home)/[^\"']+")
KEYWORDS = [
    "Lite",
    "Full",
    "PADA",
    "context",
    "Transformer",
    "CORAL",
    "MMD",
    "CDAN",
    "prototype",
    "pseudo",
    "CerebrA",
]


def names_from_targets(node):
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names = []
        for item in node.elts:
            names.extend(names_from_targets(item))
        return names
    return []


for filename in FILES:
    notebook = json.loads((BASE / filename).read_text(encoding="utf-8"))
    print(f"\n### {filename}")
    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            print(f"cell {index}: SYNTAX {exc}")
            continue

        classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
        funcs = [
            n.name
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assigns = []
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    assigns.extend(names_from_targets(target))
            elif isinstance(node, ast.AnnAssign):
                assigns.extend(names_from_targets(node.target))
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append((node.module or "") + ".*")

        paths = sorted(set(PATH_RE.findall(source)))
        keys = [kw for kw in KEYWORDS if kw.lower() in source.lower()]
        if classes or funcs or assigns or imports or paths or keys:
            print(
                f"cell {index}: classes={classes} funcs={funcs} "
                f"assigns={assigns[:20]} imports={imports[:20]} "
                f"paths={paths[:10]} keys={keys}"
            )

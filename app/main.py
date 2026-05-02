# main.py
from pathlib import Path
from app.parsers.python_parser import PythonParser
from app.parsers.parser_registry import ParserRegistry
from app.extractors.python_extractor import PythonExtractor
from app.extractors.resolver.resolver import resolve_edges

REPO_ID   = "test_repo"
REPO_PATH = "temp/test_project"

def main() -> None:
    repo_root = Path(REPO_PATH).resolve()
    registry  = ParserRegistry([PythonParser()])
    extractor = PythonExtractor(repo=REPO_ID)

    all_nodes, all_edges = [], []

    for file_path in repo_root.rglob("*.py"):
        relative = file_path.relative_to(repo_root).as_posix()
        parser   = registry.get_by_extension(relative)
        if not parser:
            continue
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree   = parser.parse(source, relative)
        if not tree:
            continue
        nodes, edges = extractor.extract(tree, source.encode(), relative)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    resolved, unresolved, edges = resolve_edges(all_nodes, all_edges)

    print(resolved, unresolved)

if __name__ == "__main__":
    main()
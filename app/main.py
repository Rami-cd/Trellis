# main.py
from pathlib import Path
from app.parsers.python_parser import PythonParser
from app.parsers.parser_registry import ParserRegistry
from app.extractors.python_extractor import PythonExtractor
from app.extractors.resolver.resolver import resolve_edges
from app.schemas.node import CodeNodeType
from app.llm.summarizer.gemini import GeminiSummarizer

REPO_ID   = "test_repo"
REPO_PATH = "temp/test_project"

def main() -> None:
    ...

if __name__ == "__main__":
    main()
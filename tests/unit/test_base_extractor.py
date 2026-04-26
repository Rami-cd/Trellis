import pytest

from extractors.base_extractor import BaseExtractor


def test_base_extractor_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseExtractor()  # type: ignore[abstract]


def test_concrete_subclass_must_implement_extract_and_language():
    class MissingExtractExtractor(BaseExtractor):
        @property
        def language(self) -> str:
            return "python"

    class MissingLanguageExtractor(BaseExtractor):
        def extract(self, tree, source: str, file_path: str) -> None:  # type: ignore[override]
            pass

    with pytest.raises(TypeError):
        MissingExtractExtractor()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        MissingLanguageExtractor()  # type: ignore[abstract]

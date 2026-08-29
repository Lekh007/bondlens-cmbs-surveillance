from pathlib import Path

from investrag.parser import parse_document


def test_json_provenance(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    path.write_text('{"company":{"name":"Acme","metrics":[{"revenue":42}]}}', encoding="utf-8")
    parsed = parse_document(path)
    assert parsed.parser == "native-json"
    assert any(element.json_path == "$.company.metrics[0].revenue" for element in parsed.elements)


def test_markdown_headings_and_lists(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("# Revenue\n\n- Growth was 12%.\n", encoding="utf-8")
    parsed = parse_document(path)
    assert [element.element_type for element in parsed.elements] == ["heading", "list"]

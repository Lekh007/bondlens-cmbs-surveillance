from investrag.chunking import chunk_elements
from investrag.domain import CanonicalElement


def test_structure_aware_chunks_preserve_element_ids() -> None:
    elements = [
        CanonicalElement(element_id="h1", element_type="heading", text="Risk"),
        CanonicalElement(element_id="p1", element_type="paragraph", text="Credit spreads widened."),
    ]
    chunks = chunk_elements(elements, "src_1")
    assert len(chunks) == 1
    assert set(chunks[0].element_ids) == {"h1", "p1"}
    assert chunks[0].parent_id == "h1"

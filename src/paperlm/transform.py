"""Turn GROBID TEI XML into clean reading text plus a quality row.

The TEI comes from an untrusted PDF, so parsing runs with entity resolution
and network/DTD loading disabled to avoid XXE and entity-expansion attacks.
"""

import re
import unicodedata

from lxml import etree

from paperlm.constants import (
    BLOCKED_HEADINGS,
    FORMULA_PLACEHOLDER,
    NS,
    SKIP_FIGURE_CHILDREN,
)
from paperlm.models import Block, Stats, TransformResult

# Compiled regexes are private implementation details of this module's
# normalization helpers, so they stay next to the code that uses them.
_LEADING_NUMBER = re.compile(r"^[\dIVXLC]+[.)\s]+", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def _localname(element: etree._Element) -> str:
    """Return an element's tag without its namespace (``""`` for comments)."""
    tag = element.tag
    if not isinstance(tag, str):  # comments / processing instructions
        return ""
    return etree.QName(tag).localname


def parse_tei(data: bytes) -> etree._Element:
    """Parse TEI ``data`` safely and return the root element.

    Entity resolution, DTD loading and network access are all disabled
    because the XML is derived from untrusted PDF input.
    """
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )
    return etree.fromstring(data, parser=parser)


def normalize(text: str) -> str:
    """Apply NFKC normalization and collapse all runs of whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    return _WHITESPACE.sub(" ", text).strip()


def _append_text(node: etree._Element, parts: list[str]) -> None:
    """Recursively collect a node's text, applying the formula/citation rules."""
    tag = _localname(node)

    if tag == "formula":
        parts.append(FORMULA_PLACEHOLDER)
    elif tag == "ref" and node.get("type") == "bibr":
        # Chosen citation rule: drop inline bibliographic references entirely
        # (and their text), keeping only the surrounding prose.
        pass
    else:
        if node.text:
            parts.append(node.text)
        for child in node:
            _append_text(child, parts)

    if node.tail:
        parts.append(node.tail)


def block_to_text(element: etree._Element) -> str:
    """Convert one block element to normalized text.

    Formulas become :data:`FORMULA_PLACEHOLDER` and bibliographic citations
    are removed. Works for paragraphs and for figure/table captions alike.
    """
    # A display formula (a block-level sibling of the paragraphs) is replaced
    # wholesale by the marker, exactly like an inline one.
    if _localname(element) == "formula":
        return FORMULA_PLACEHOLDER

    # Figure/table captions are a label plus a description with no text
    # between them; join their child parts with spaces so they stay readable.
    # The tabular grid and the bare label are dropped -- see above.
    if _localname(element) == "figure":
        pieces = [
            block_to_text(child)
            for child in element
            if _localname(child) not in SKIP_FIGURE_CHILDREN
        ]
        return normalize(" ".join(p for p in pieces if p))

    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        _append_text(child, parts)
    return normalize("".join(parts))


def is_blocked_heading(heading: str | None) -> bool:
    """True if ``heading`` names a section we drop (references, funding, ...)."""
    if not heading:
        return False
    normalized = _LEADING_NUMBER.sub("", normalize(heading).lower()).strip()
    return any(normalized.startswith(blocked) for blocked in BLOCKED_HEADINGS)


def get_title_and_abstract(
    tree: etree._Element,
) -> tuple[str | None, str | None]:
    """Read the title and abstract from the TEI header."""
    title_el = tree.find(".//tei:teiHeader//tei:titleStmt/tei:title", NS)
    title = normalize("".join(title_el.itertext())) if title_el is not None else ""

    abstract_el = tree.find(".//tei:teiHeader//tei:profileDesc/tei:abstract", NS)
    abstract = ""
    if abstract_el is not None:
        paragraphs = abstract_el.findall(".//tei:p", NS)
        if paragraphs:
            abstract = normalize(" ".join(block_to_text(p) for p in paragraphs))
        else:
            abstract = normalize("".join(abstract_el.itertext()))

    return (title or None, abstract or None)


def _walk_body(node: etree._Element, heading: str | None):
    """Yield blocks from a body subtree in document order."""
    current = heading
    for child in node:
        tag = _localname(child)
        if tag == "head":
            current = normalize("".join(child.itertext())) or None
        elif tag == "p":
            yield Block(current, "paragraph", child)
        elif tag == "formula":
            # Display equations are block-level siblings of the paragraphs,
            # not nested inside them, so they need their own branch here.
            yield Block(current, "formula", child)
        elif tag == "figure":
            kind = "table" if child.get("type") == "table" else "figure"
            yield Block(current, kind, child)
        elif tag in ("div", "body"):
            yield from _walk_body(child, current)


def iter_body_blocks(tree: etree._Element):
    """Walk ``<body>`` in order, yielding paragraph and figure/table blocks."""
    body = tree.find(".//tei:text/tei:body", NS)
    if body is None:
        return
    yield from _walk_body(body, None)


def compute_stats(
    title: str | None,
    abstract: str | None,
    blocks: list[str],
    headings: list[str],
    dropped_headings: list[str],
) -> Stats:
    """Build the quality row from the kept body blocks and metadata."""
    text = "\n".join(blocks)

    words = text.split()
    non_space = [c for c in text if not c.isspace()]
    alpha = sum(1 for c in non_space if c.isalpha())
    alpha_ratio = alpha / len(non_space) if non_space else 0.0

    # The repeated-line signal looks for duplicated prose (running headers and
    # the like from a bad extraction); identical formula markers are expected
    # and would otherwise swamp it, so they are excluded.
    content_lines = [b for b in blocks if b != FORMULA_PLACEHOLDER]
    total_lines = len(content_lines)
    unique_lines = len(set(content_lines))
    repeated_fraction = (
        (total_lines - unique_lines) / total_lines if total_lines else 0.0
    )

    return Stats(
        word_count=len(words),
        char_count=len(text),
        alpha_ratio=round(alpha_ratio, 4),
        section_count=len(headings),
        repeated_line_fraction=round(repeated_fraction, 4),
        dropped_headings=dropped_headings,
        missing_title=not bool(title),
        missing_abstract=not bool(abstract),
    )


def transform(tei_bytes: bytes) -> TransformResult:
    """Parse TEI bytes and return title, abstract, clean text, and stats."""
    tree = parse_tei(tei_bytes)
    title, abstract = get_title_and_abstract(tree)

    kept_blocks: list[str] = []
    kept_headings: list[str] = []
    seen_headings: set[str] = set()
    dropped_headings: list[str] = []
    seen_dropped: set[str] = set()

    for block in iter_body_blocks(tree):
        if is_blocked_heading(block.heading):
            if block.heading not in seen_dropped:
                seen_dropped.add(block.heading)
                dropped_headings.append(block.heading)
            continue

        text = block_to_text(block.element)
        if not text:
            continue

        # A multi-line display equation arrives as several adjacent formula
        # elements; collapse them into a single marker.
        if (
            text == FORMULA_PLACEHOLDER
            and kept_blocks
            and kept_blocks[-1] == FORMULA_PLACEHOLDER
        ):
            continue

        kept_blocks.append(text)
        if block.heading and block.heading not in seen_headings:
            seen_headings.add(block.heading)
            kept_headings.append(block.heading)

    text = "\n\n".join(kept_blocks)
    stats = compute_stats(
        title, abstract, kept_blocks, kept_headings, dropped_headings
    )
    return TransformResult(title=title, abstract=abstract, text=text, stats=stats)

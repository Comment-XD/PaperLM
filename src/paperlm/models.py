from dataclasses import dataclass, field
from lxml import etree

@dataclass
class Block:
    """One body unit in document order, tagged with its section heading."""

    heading: str | None
    kind: str  # "paragraph", "formula", "figure", or "table"
    element: etree._Element


@dataclass
class Stats:
    """Quality row describing one transformed paper."""

    word_count: int
    char_count: int
    alpha_ratio: float
    section_count: int
    repeated_line_fraction: float
    dropped_headings: list[str] = field(default_factory=list)
    missing_title: bool = False
    missing_abstract: bool = False


@dataclass
class TransformResult:
    """Everything transform() produces for a single paper."""

    title: str | None
    abstract: str | None
    text: str
    stats: Stats

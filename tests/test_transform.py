"""Tests for TEI -> clean text transformation."""

from paperlm import transform

TEI_NS = 'xmlns="http://www.tei-c.org/ns/1.0"'


def _doc(body: str, abstract: str = "<p>An abstract.</p>") -> bytes:
    """Wrap ``body`` (a ``<body>`` inner fragment) in a minimal TEI document."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI {TEI_NS}>
  <teiHeader>
    <fileDesc><titleStmt><title>A Title</title></titleStmt></fileDesc>
    <profileDesc><abstract>{abstract}</abstract></profileDesc>
  </teiHeader>
  <text><body>{body}</body></text>
</TEI>""".encode("utf-8")


def test_display_formula_becomes_marker():
    """A block-level <formula> (a div child, not nested in a <p>) is kept."""
    body = """
      <div>
        <head>Method</head>
        <p>The loss is defined as:</p>
        <formula>L = a + b</formula>
        <p>where a and b are terms.</p>
      </div>
    """
    result = transform.transform(_doc(body))
    blocks = result.text.split("\n\n")
    assert transform.FORMULA_PLACEHOLDER in blocks
    # The raw formula text must not leak into the output.
    assert "a + b" not in result.text


def test_consecutive_formulas_collapse():
    """A multi-line equation (adjacent <formula> siblings) yields one marker."""
    body = """
      <div>
        <p>Consider:</p>
        <formula>line one</formula>
        <formula>line two</formula>
        <formula>line three</formula>
        <p>Done.</p>
      </div>
    """
    result = transform.transform(_doc(body))
    assert result.text.count(transform.FORMULA_PLACEHOLDER) == 1


def test_formula_markers_excluded_from_repeated_line_stat():
    """Repeated formula markers must not inflate the duplicate-line signal."""
    body = """
      <div>
        <p>First paragraph.</p>
        <formula>x = 1</formula>
        <p>Second paragraph.</p>
        <formula>y = 2</formula>
        <p>Third paragraph.</p>
      </div>
    """
    result = transform.transform(_doc(body))
    # Two identical [FORMULA] blocks, but all prose is unique.
    assert result.stats.repeated_line_fraction == 0.0


def test_table_grid_dropped_caption_kept():
    """A <figure type="table"> keeps its caption but drops the numeric grid."""
    body = """
      <div>
        <figure type="table">
          <head>Table 1</head>
          <label>1</label>
          <figDesc>Accuracy by method.</figDesc>
          <table>
            <row><cell>Method</cell><cell>Acc</cell></row>
            <row><cell>Ours</cell><cell>99.9</cell></row>
          </table>
        </figure>
      </div>
    """
    result = transform.transform(_doc(body))
    assert "Accuracy by method." in result.text
    # Redundant label and the flattened grid cells are gone.
    assert "99.9" not in result.text
    assert "Table 1 1" not in result.text


def test_inline_citations_removed():
    """Inline <ref type="bibr"> and its text are dropped from prose."""
    body = """
      <div>
        <p>As shown earlier <ref type="bibr">[1]</ref> this holds.</p>
      </div>
    """
    result = transform.transform(_doc(body))
    assert "[1]" not in result.text
    assert "As shown earlier" in result.text

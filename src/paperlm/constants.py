"""Static domain constants for TEI parsing and transformation.

These are facts about the TEI format and fixed transformation policy -- they do
not vary by environment, so they live here rather than in ``config.Settings``
(which is for runtime/deployment configuration loaded from the environment).
"""

#: The TEI namespace GROBID emits, and the prefix map used for XPath queries.
TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}

#: Math (inline or display) is replaced with this marker so raw formula text
#: never pollutes the reading text. Part of the output contract.
FORMULA_PLACEHOLDER = "[FORMULA]"

#: Headings whose sections carry no body content worth keeping. Matched as a
#: prefix against the normalized (lower-cased, de-numbered) heading.
BLOCKED_HEADINGS = (
    "acknowledgement",  # also matches "acknowledgements"/"acknowledgment(s)"
    "acknowledgment",
    "funding",
    "references",
    "reference",
    "bibliography",
    "author contribution",
    "author information",
    "competing interest",
    "conflict of interest",
    "conflicts of interest",
    "declaration",
    "disclosure",
    "data availability",
    "code availability",
    "supplementary material",
    "supporting information",
    "appendix",
    "appendices",
    "ethics",
)

#: Figure children that carry no readable prose: the ``<table>`` grid flattens
#: into an unreadable run of cell values, and ``<label>`` just repeats the
#: number already in ``<head>`` ("Table 2" + "2").
SKIP_FIGURE_CHILDREN = ("table", "label")

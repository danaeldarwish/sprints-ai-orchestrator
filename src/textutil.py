"""Small text helpers shared by the embedder, retriever and offline reasoner."""
from __future__ import annotations

import re

STOPWORDS = frozenset(
    """a an the and or but if then else of to in on at by for with from as is are was were be been being do does did
    can could should would will shall may might must i me my we our you your he she it its they them their this that
    these those what which who whom whose how why when where there here about into over under again more most some any
    such no nor not only own same so than too very just also get got make makes made use used using need needs want
    wants like please tell explain show give me us""".split()
)
_WORD = re.compile(r"[a-z0-9]+")


def stem(token: str) -> str:
    """Very light suffix stripper (plural/gerund/past) so 'pauses' ~ 'pause'."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def content_terms(text: str) -> list[str]:
    """Lower-cased, stop-word-free, stemmed terms of ``text`` (order preserved)."""
    return [stem(t) for t in _WORD.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]

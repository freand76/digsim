# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The search of the netlist view: the signals, the types of cells and the source lines of a
netlist that match a query (kept free from Qt imports so that it can be tested without a
display)
"""

from __future__ import annotations

from digsim.utils import NetlistEntry

from ._ic_search import fuzzy_search


def entry_text(entry: NetlistEntry) -> str:
    """An entry in the list, like "regfile  (signal, 512 bits, 1 cell)" """
    count = len(entry.cells)
    return f"{entry.name}  ({entry.description()}, {count} cell{'s' if count != 1 else ''})"


def search_entries(query: str, entries: list[NetlistEntry]) -> list[NetlistEntry]:
    """
    The entries that match a query, the best match first (see fuzzy_search()): a word
    matches the name, or the kind ("signal", "cell type" or "source line"). An empty query
    matches them all, in their order.
    """
    if not query.strip():
        return list(entries)
    by_name: dict[str, list[NetlistEntry]] = {}
    for entry in entries:
        by_name.setdefault(entry.name, []).append(entry)
    items = {
        name: " ".join(entry.description() for entry in named) for name, named in by_name.items()
    }
    return [entry for name in fuzzy_search(query, items) for entry in by_name[name]]

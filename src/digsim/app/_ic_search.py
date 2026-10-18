# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Fuzzy search of the ICs in the IC selector of the settings dialog
(kept free from Qt imports so that it can be tested without a display)
"""

from __future__ import annotations


def _is_subsequence(query: str, text: str) -> bool:
    """Are the characters of the query in the text, in the same order (skipped ones too)"""
    position = 0
    for char in query:
        position = text.find(char, position) + 1
        if position == 0:
            return False
    return True


def _word_score(word: str, name: str, description: str) -> int | None:
    """How well a word of the query matches an IC, lower is better, None if it doesn't"""
    words = description.split()
    if name.startswith(word):
        return 0
    if word in name:
        return 1
    if any(text.startswith(word) for text in words):
        return 2
    if word in description:
        return 3
    if _is_subsequence(word, name):
        return 4
    # Typing errors, like skipped letters, within one word of the description
    if len(word) > 2 and any(_is_subsequence(word, text) for text in words):
        return 5
    return None


def search_ics(query: str, ics: dict[str, str]) -> list[str]:
    """
    The ICs (name: description) that match a query, the best match first. Each word of
    the query must match the name (like "741") or the description (like "counter"), also
    with skipped letters ("shft" for "shift"). An empty query matches all ICs.
    """
    words = query.lower().split()
    scored = []
    for name, description in ics.items():
        scores = [_word_score(word, name.lower(), description.lower()) for word in words]
        if any(score is None for score in scores):
            continue
        scored.append((sum(score for score in scores if score is not None), name))
    return [name for _, name in sorted(scored, key=lambda item: (item[0], _sort_key(item[1])))]


def _sort_key(name: str) -> tuple[int, str]:
    """IC names in number order: 7448 before 74138"""
    digits = "".join(char for char in name if char.isdigit())
    return (len(digits), name)

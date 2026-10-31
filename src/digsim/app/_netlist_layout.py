# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The layout of a netlist view: nodes (cells and module ports) in columns from left to right,
and the wires between their pins, drawn with horizontal and vertical segments.

The inputs are the first column and the outputs the last. A cell is in the column after
the cells that drive it (the longest path from the inputs). Feedback, like a flip-flop
whose output goes back to its input, goes back to the left. The wires from a pin share a
slot in each column that they pass, and the nodes and slots of a column are ordered to
cross few wires (the barycenter method). The vertical segments are in the gaps between the
columns, the wires from a pin on a track of their own.
"""

from __future__ import annotations

import dataclasses
import math
from collections import deque
from collections.abc import Iterable
from itertools import pairwise

from digsim.utils import Pin


Point = tuple[float, float]
Segment = tuple[Point, Point]

# The space between nodes in a column, between the slots of wires that pass a column,
# between the tracks in a gap, and between a column and the tracks next to it
NODE_SPACING = 20.0
SLOT_SPACING = 10.0
TRACK_SPACING = 8.0
GAP_MARGIN = 16.0
ORDER_SWEEPS = 4
# The priority of a wire through a column, before any node (see _priority_place())
SLOT_PRIORITY = 1_000_000
# The most items of a column whose nodes are swapped to be nearer their targets
SWAP_LIMIT = 60
STRAIGHTEN_ROUNDS = 3


@dataclasses.dataclass
class NodeShape:
    """
    The size of a node, and its pins: (x, y) from its top left corner. A pin in the left
    half of the node is on its left side, else on its right side.
    """

    width: float
    height: float
    pins: dict[str, Point]

    def on_left(self, port: str) -> bool:
        return self.pins[port][0] < self.width / 2


@dataclasses.dataclass
class Layout:
    """Where the nodes are (their top left corners), and the segments of each wire"""

    positions: dict[str, Point]
    wires: dict[tuple[Pin, Pin], list[Segment]]

    def trees(self) -> dict[Pin, list[Segment]]:
        """The segments of the wires from each pin, each segment once"""
        trees: dict[Pin, dict[Segment, None]] = {}
        for (source, _), segments in self.wires.items():
            trees.setdefault(source, {}).update(dict.fromkeys(segments))
        return {source: list(segments) for source, segments in trees.items()}


@dataclasses.dataclass(eq=False)
class _Item:
    """
    A node in a column, or the slot of the wires from a pin where they pass a column
    (going right, or back to the left)
    """

    column: int
    height: float
    node: str | None = None
    source: Pin | None = None
    back: bool = False
    y: float = 0.0
    neighbors: list[_Item] = dataclasses.field(default_factory=list)


# A step of a wire: the pin or slot it reaches, the gap it goes through, and if it goes back
_Step = tuple["_Item | Pin", int, bool]


def _columns(
    nodes: Iterable[str],
    inputs: list[str],
    outputs: list[str],
    connections: list[tuple[Pin, Pin]],
    pull_sources: bool = False,
) -> dict[str, int]:
    """
    The column of each node: the inputs in the first, then each cell after the cells that
    drive it (without feedback, which goes back), and the outputs in the last. With
    'pull_sources', a node that nothing drives (an input too) is in the column before the
    first node it drives: near where it is used.
    """
    ports = set(inputs) | set(outputs)
    cells = [node for node in nodes if node not in ports]
    drivers: dict[str, list[str]] = {cell: [] for cell in cells}
    driven: dict[str, list[str]] = {cell: [] for cell in cells}
    for source, sink in connections:
        if source.node in drivers and sink.node in drivers and source.node != sink.node:
            drivers[sink.node].append(source.node)
            driven[source.node].append(sink.node)
    # The connections that close a loop, by a depth-first search from the cells that the
    # inputs drive, in the order of the inputs, then from the others
    first = [sink.node for source, sink in connections if source.node in inputs]
    starts = [cell for cell in dict.fromkeys(first + cells) if cell in drivers]
    state: dict[str, int] = {}
    loops: set[tuple[str, str]] = set()
    for start in starts:
        if start in state:
            continue
        state[start] = 1
        stack = [(start, iter(driven[start]))]
        while stack:
            cell, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[cell] = 2
                stack.pop()
            elif child not in state:
                state[child] = 1
                stack.append((child, iter(driven[child])))
            elif state[child] == 1:
                loops.add((cell, child))
    # The longest path from the inputs, without the loops
    waiting = {
        cell: sum(1 for driver in drivers[cell] if (driver, cell) not in loops) for cell in cells
    }
    column = dict.fromkeys(cells, 1)
    ready = [cell for cell in cells if waiting[cell] == 0]
    while ready:
        cell = ready.pop()
        for child in driven[cell]:
            if (cell, child) in loops:
                continue
            column[child] = max(column[child], column[cell] + 1)
            waiting[child] -= 1
            if waiting[child] == 0:
                ready.append(child)
    last = max(column.values(), default=0) + 1
    column.update(dict.fromkeys(inputs, 0))
    column.update(dict.fromkeys(outputs, last))
    if pull_sources:
        driven_columns: dict[str, list[int]] = {}
        for source, sink in connections:
            if source.node != sink.node:
                driven_columns.setdefault(source.node, []).append(column[sink.node])
        undriven = [*inputs, *(cell for cell in cells if not drivers[cell])]
        for node in undriven:
            if node in driven_columns:
                column[node] = max(min(driven_columns[node]) - 1, 0)
    return column


def _spacing(item: _Item) -> float:
    """The space above an item in its column"""
    return NODE_SPACING if item.node is not None else SLOT_SPACING


def _balanced_place(items: list[_Item], targets: list[float | None]) -> list[float]:
    """
    The tops of the items of a column, in their order: stacked from the top, the items
    pushed down by the ones above them, and from the bottom, pushed up, and in between,
    as near to their targets as they can be
    """
    down: list[float] = []
    for index, (item, target) in enumerate(zip(items, targets, strict=True)):
        if index == 0:
            y = target if target is not None else 0.0
        else:
            y = down[-1] + items[index - 1].height + _spacing(item)
            if target is not None:
                y = max(y, target)
        down.append(y)
    up = list(down)
    for index in range(len(items) - 2, -1, -1):
        target = targets[index]
        y = target if target is not None else down[index]
        limit = up[index + 1] - items[index].height - _spacing(items[index + 1])
        up[index] = min(y, limit)
    return [(low + high) / 2 for low, high in zip(down, up, strict=True)]


def _priority_place(
    items: list[_Item], targets: list[float | None], priorities: list[int]
) -> list[float]:
    """
    The tops of the items of a column, in their order (the priority method of Sugiyama):
    the items with the highest priority first, each as near its target as the items placed
    before it allow, pushing the others out of its way
    """
    count = len(items)
    # The least distance from the top of the first item to the top of each item
    reach = [0.0] * count
    for index in range(1, count):
        reach[index] = reach[index - 1] + items[index - 1].height + _spacing(items[index])
    tops = list(reach)
    placed = [False] * count
    for index in sorted(range(count), key=lambda i: -priorities[i]):
        target = targets[index]
        if target is None:
            continue
        above = next((i for i in range(index - 1, -1, -1) if placed[i]), None)
        below = next((i for i in range(index + 1, count) if placed[i]), None)
        low = -math.inf if above is None else tops[above] + reach[index] - reach[above]
        high = math.inf if below is None else tops[below] - (reach[below] - reach[index])
        tops[index] = min(max(target, low), high)
        placed[index] = True
        for i in range(index - 1, -1, -1):
            limit = tops[i + 1] - (reach[i + 1] - reach[i])
            if placed[i] or tops[i] <= limit:
                break
            tops[i] = limit
        for i in range(index + 1, count):
            limit = tops[i - 1] + reach[i] - reach[i - 1]
            if placed[i] or tops[i] >= limit:
                break
            tops[i] = limit
    return tops


def _vertical(x: float, start: float, end: float, ys: list[float]) -> list[Segment]:
    """
    A vertical segment from start to end, split where the other wires of its run turn:
    the same segments for each wire of a run, where the dots are found
    """
    low, high = min(start, end), max(start, end)
    points = [y for y in ys if low <= y <= high]
    return [((x, a), (x, b)) for a, b in pairwise(points)]


class _Router:
    """Lays out the nodes and routes the wires, see netlist_layout()"""

    def __init__(
        self,
        nodes: dict[str, NodeShape],
        inputs: list[str],
        outputs: list[str],
        connections: list[tuple[Pin, Pin]],
        order_ports: bool = False,
        gap_margin: float = GAP_MARGIN,
        bundles: bool = False,
    ) -> None:
        self.nodes = nodes
        self.bundles = bundles
        self.order_ports = order_ports
        self.gap_margin = gap_margin
        self.inputs = inputs
        self.outputs = outputs
        self.connections = list(dict.fromkeys(connections))
        # The inputs of a circuit (not the ports of a module) go where they are used
        self.column = _columns(nodes, inputs, outputs, self.connections, order_ports)
        self.last = max(self.column.values(), default=0)
        self.items: list[list[_Item]] = [[] for _ in range(self.last + 1)]
        self.node_items: dict[str, _Item] = {}
        # The slots of the wires from each pin, by column, going right and going back
        self.forward: dict[Pin, dict[int, _Item]] = {}
        self.backward: dict[Pin, dict[int, _Item]] = {}
        self.sinks: dict[Pin, list[Pin]] = {}
        for source, sink in self.connections:
            self.sinks.setdefault(source, []).append(sink)

    def route(self) -> Layout:
        self._add_items()
        self._link()
        self._order()
        self._place_y()
        self._straighten()
        return self._route()

    def _goes_back(self, source: Pin, sink: Pin) -> bool:
        """
        A wire goes back to a column left of its pin, or of the same column. A pin on the
        left of a node (an inout port) sends all its wires back.
        """
        return self.nodes[source.node].on_left(source.port) or (
            self.column[sink.node] <= self.column[source.node]
        )

    def _add_items(self) -> None:
        for node in self._node_order():
            item = _Item(self.column[node], self.nodes[node].height, node=node)
            self.items[item.column].append(item)
            self.node_items[node] = item
        for source, sinks in self.sinks.items():
            start = self.column[source.node]
            ahead = [self.column[s.node] for s in sinks if not self._goes_back(source, s)]
            behind = [self.column[s.node] for s in sinks if self._goes_back(source, s)]
            if ahead:
                self.forward[source] = {
                    column: self._slot(column, source, False)
                    for column in range(start + 1, max(ahead))
                }
            if behind:
                top = start - 1 if self.nodes[source.node].on_left(source.port) else start
                self.backward[source] = {
                    column: self._slot(column, source, True)
                    for column in range(top, min(behind) - 1, -1)
                }

    def _slot(self, column: int, source: Pin, back: bool) -> _Item:
        item = _Item(column, 0.0, source=source, back=back)
        self.items[column].append(item)
        return item

    def _node_order(self) -> list[str]:
        """The nodes in the order of a search from the inputs, the first order of a column"""
        order: dict[str, None] = dict.fromkeys(self.inputs)
        driven: dict[str, list[str]] = {}
        for source, sink in self.connections:
            driven.setdefault(source.node, []).append(sink.node)
        queue = deque(self.inputs)
        while queue:
            for child in driven.get(queue.popleft(), []):
                if child not in order:
                    order[child] = None
                    queue.append(child)
        order.update(dict.fromkeys(self.nodes))
        outputs = set(self.outputs)
        return [node for node in order if node not in outputs] + self.outputs

    def _before(self, source: Pin, sink: Pin) -> _Item | None:
        """The node or slot that a wire comes from, into its sink"""
        column = self.column[sink.node]
        if self._goes_back(source, sink):
            return self.backward.get(source, {}).get(column)
        return self.forward.get(source, {}).get(column - 1, self.node_items[source.node])

    def _link(self) -> None:
        """The items in the next and previous columns that each item is wired to"""

        def link(first: _Item, second: _Item) -> None:
            first.neighbors.append(second)
            second.neighbors.append(first)

        for source, sinks in self.sinks.items():
            chain = [self.node_items[source.node], *self.forward.get(source, {}).values()]
            back = list(self.backward.get(source, {}).values())
            for slots in (chain, back):
                for first, second in pairwise(slots):
                    link(first, second)
            for sink in sinks:
                before = self._before(source, sink)
                if before is not None and before.column != self.column[sink.node]:
                    link(before, self.node_items[sink.node])

    def _order(self) -> None:
        """
        Order the columns of cells by the places of the items they are wired to, in the
        column on the left, then on the right. The ports keep their order, unless they are
        ordered too ('order_ports').
        """
        first, last = (0, self.last) if self.order_ports else (1, self.last - 1)
        for _ in range(ORDER_SWEEPS):
            for columns in (
                range(max(first, 1), last + 1),
                range(min(last, self.last - 1), first - 1, -1),
            ):
                for column in columns:
                    side = column - columns.step
                    place = {id(item): index for index, item in enumerate(self.items[side])}
                    items = self.items[column]
                    keys: list[float] = []
                    for index, item in enumerate(items):
                        near = [place[id(n)] for n in item.neighbors if id(n) in place]
                        keys.append(sum(near) / len(near) if near else float(index))
                    order = sorted(range(len(items)), key=lambda i: keys[i])
                    self.items[column] = [items[i] for i in order]

    def _pin_y(self, pin: Pin) -> float:
        return self.node_items[pin.node].y + self.nodes[pin.node].pins[pin.port][1]

    def _place_y(self) -> None:
        """
        Place the items of each column in their order, each as near as it can be to where
        it is wired from in the column on its left: those wires are straight when they can
        be. The inputs are stacked from the top.
        """
        # For each node, where its wires come from on the left (a pin or a slot), and the
        # y of their pins in the node
        wanted: dict[str, list[tuple[_Item | Pin, float]]] = {}
        for source, sinks in self.sinks.items():
            for sink in sinks:
                before = self._before(source, sink)
                if before is None or self._goes_back(source, sink):
                    continue
                offset = self.nodes[sink.node].pins[sink.port][1]
                start = source if before.node is not None else before
                wanted.setdefault(sink.node, []).append((start, offset))
        for column, items in enumerate(self.items):
            if column == 0:
                y = 0.0
                for item in items:
                    item.y = y
                    y += item.height + NODE_SPACING
                continue
            if self.bundles:
                items = self._swap_nodes(column, wanted)
            targets = [self._target(item, wanted) for item in items]
            if self.bundles:
                priorities = [self._priority(item, wanted) for item in items]
                tops = _priority_place(items, targets, priorities)
            else:
                tops = _balanced_place(items, targets)
            for item, top in zip(items, tops, strict=True):
                # In whole pixels, like the components of a circuit
                item.y = round(top)

    def _swap_nodes(
        self, column: int, wanted: dict[str, list[tuple[_Item | Pin, float]]]
    ) -> list[_Item]:
        """
        The order of a column, with neighboring nodes swapped where that brings the nodes
        nearer to their targets (weighed by their priorities): a big node between two
        others doesn't keep a bundle of wires from being straight. In a small column.
        """
        items = self.items[column]
        if len(items) > SWAP_LIMIT:
            return items
        targets = {id(item): self._target(item, wanted) for item in items}
        priorities = {id(item): self._priority(item, wanted) for item in items}

        def cost(order: list[_Item]) -> float:
            tops = _priority_place(
                order, [targets[id(i)] for i in order], [priorities[id(i)] for i in order]
            )
            return sum(
                priorities[id(item)] * abs(top - target)
                for item, top in zip(order, tops, strict=True)
                if (target := targets[id(item)]) is not None
            )

        best = cost(items)
        for _ in range(len(items)):
            improved = False
            for index in range(len(items) - 1):
                first, second = items[index], items[index + 1]
                if first.node is None or second.node is None:
                    continue
                order = [*items[:index], second, first, *items[index + 2 :]]
                order_cost = cost(order)
                if order_cost < best - 0.5:
                    items, best, improved = order, order_cost, True
            if not improved:
                break
        self.items[column] = items
        return items

    def _priority(self, item: _Item, wanted: dict[str, list[tuple[_Item | Pin, float]]]) -> int:
        """
        How much an item gets its place before the others of its column: a wire that
        passes the column is straight first, then the nodes with the most parallel wires
        from one place on the left (a node with a bundle of wires before one with single
        wires)
        """
        if item.node is None:
            return SLOT_PRIORITY
        bundles: dict[int, int] = {}
        for start, _ in wanted.get(item.node, []):
            key = id(self.node_items[start.node]) if isinstance(start, Pin) else id(start)
            if isinstance(start, _Item) and start.source is not None:
                # The slots of the wires from the pins of one node are one bundle
                key = id(self.node_items[start.source.node])
            bundles[key] = bundles.get(key, 0) + 1
        return max(bundles.values(), default=0)

    def _straighten(self) -> None:
        """
        Put the slots of the wires from a pin at one height, where the items around them
        leave room for that: the wires don't step up and down from column to column. A
        chain of slots steps only where there is no room.
        """
        index = {id(item): i for items in self.items for i, item in enumerate(items)}

        def room(slot: _Item) -> tuple[float, float]:
            items = self.items[slot.column]
            i = index[id(slot)]
            low = items[i - 1].y + items[i - 1].height + SLOT_SPACING if i > 0 else -math.inf
            high = items[i + 1].y - _spacing(items[i + 1]) if i + 1 < len(items) else math.inf
            return low, high

        # The slots of each chain in the order the wires go (to the right, or back to the
        # left), the longest first. Moving a chain makes room for others: a few rounds.
        chains = [
            (source, [chain[column] for column in sorted(chain, reverse=back)])
            for back, chains in ((False, self.forward), (True, self.backward))
            for source, chain in chains.items()
        ]
        chains.sort(key=lambda chain: -len(chain[1]))
        for _ in range(STRAIGHTEN_ROUNDS):
            for source, slots in chains:
                previous = self._pin_y(source)
                run: list[_Item] = []
                low, high = -math.inf, math.inf
                for slot in [*slots, None]:
                    if slot is not None:
                        slot_low, slot_high = room(slot)
                        if not run or (max(low, slot_low) <= min(high, slot_high)):
                            run.append(slot)
                            low, high = max(low, slot_low), min(high, slot_high)
                            continue
                    y = min(max(previous, low), high)
                    for item in run:
                        item.y = y
                    previous = y
                    if slot is not None:
                        run = [slot]
                        low, high = room(slot)

    def _target(
        self, item: _Item, wanted: dict[str, list[tuple[_Item | Pin, float]]]
    ) -> float | None:
        """Where an item wants to be: in line with what it is wired from on the left"""
        if item.node is None:
            assert item.source is not None
            if item.back:
                return None
            before = self.forward[item.source].get(item.column - 1)
            return before.y if before is not None else self._pin_y(item.source)
        ys = [self._y(start) - offset for start, offset in wanted.get(item.node, [])]
        return sum(ys) / len(ys) if ys else None

    def _path(self, source: Pin, sink: Pin) -> list[_Step]:
        """
        The way of a wire: its source pin, the slots it passes and its sink pin, each
        with the gap it is reached through (gap g is right of column g), and if it goes
        back
        """
        start = self.column[source.node]
        end = self.column[sink.node]
        path: list[_Step] = [(source, 0, False)]
        if not self._goes_back(source, sink):
            for column in range(start + 1, end):
                path.append((self.forward[source][column], column - 1, False))
            path.append((sink, end - 1, False))
            return path
        for column in sorted(self.backward[source], reverse=True):
            if column < end:
                break
            path.append((self.backward[source][column], column, True))
        path.append((sink, end - 1, True))
        return path

    def _y(self, element: _Item | Pin) -> float:
        return element.y if isinstance(element, _Item) else self._pin_y(element)

    def _route(self) -> Layout:
        # The places in the vertical run of the wires from each pin in each gap
        runs: dict[tuple[Pin, int, bool], set[float]] = {}
        paths: list[tuple[Pin, Pin, list[_Step]]] = []
        for source, sinks in self.sinks.items():
            for sink in sinks:
                path = self._path(source, sink)
                paths.append((source, sink, path))
                for (first, _, _), (second, gap, back) in pairwise(path):
                    run = runs.setdefault((source, gap, back), set())
                    run.update((self._y(first), self._y(second)))
        tracks, gap_tracks = self._tracks(runs)
        left, right, gap_left = self._place_x(gap_tracks)
        positions: dict[str, Point] = {}
        for node, item in self.node_items.items():
            x = right[0] - self.nodes[node].width if item.column == 0 else left[item.column]
            positions[node] = (x, item.y)

        def pin_point(pin: Pin) -> Point:
            x, y = positions[pin.node]
            px, py = self.nodes[pin.node].pins[pin.port]
            return (x + px, y + py)

        def edge(element: _Item | Pin, to_left: bool) -> Point:
            """Where a wire leaves or enters a pin or slot, on the left or right"""
            column = element.column if isinstance(element, _Item) else self.column[element.node]
            return (left[column] if to_left else right[column], self._y(element))

        wires: dict[tuple[Pin, Pin], list[Segment]] = {}
        sorted_runs = {key: sorted(ys) for key, ys in runs.items()}
        for source, sink, path in paths:
            exit_left = self.nodes[source.node].on_left(source.port)
            segments: list[Segment] = [(pin_point(source), edge(source, exit_left))]
            for (first, _, _), (second, gap, back) in pairwise(path):
                x = gap_left[gap] + self.gap_margin + tracks[(source, gap, back)] * TRACK_SPACING
                # A pin leaves on its side, a slot on the side it goes to, and the wire
                # enters a slot going back on its right, else on the left
                leaves_left = exit_left if isinstance(first, Pin) else back
                enters_left = not (isinstance(second, _Item) and back)
                start = edge(first, leaves_left)
                end = edge(second, enters_left)
                segments.append((start, (x, start[1])))
                segments += _vertical(x, start[1], end[1], sorted_runs[(source, gap, back)])
                segments.append(((x, end[1]), end))
                if isinstance(second, _Item):
                    # Through the column, to the side it goes to
                    segments.append((end, edge(second, back)))
            segments.append((edge(sink, True), pin_point(sink)))
            wires[(source, sink)] = [(a, b) for a, b in segments if a != b]
        return Layout(positions, wires)

    @staticmethod
    def _tracks(
        runs: dict[tuple[Pin, int, bool], set[float]],
    ) -> tuple[dict[tuple[Pin, int, bool], int], dict[int, int]]:
        """
        A track for each vertical run in a gap, runs that don't overlap share one, and
        the number of tracks of each gap
        """
        by_gap: dict[int, list[tuple[float, float, tuple[Pin, int, bool]]]] = {}
        for key, ys in runs.items():
            by_gap.setdefault(key[1], []).append((min(ys), max(ys), key))
        tracks: dict[tuple[Pin, int, bool], int] = {}
        counts: dict[int, int] = {}
        for gap, gap_runs in by_gap.items():
            ends: list[float] = []
            for top, bottom, key in sorted(gap_runs, key=lambda run: (run[0], run[1])):
                track = next(
                    (t for t, end in enumerate(ends) if end + TRACK_SPACING <= top), len(ends)
                )
                if track == len(ends):
                    ends.append(bottom)
                ends[track] = bottom
                tracks[key] = track
            counts[gap] = len(ends)
        return tracks, counts

    def _place_x(
        self, gap_tracks: dict[int, int]
    ) -> tuple[list[float], list[float], dict[int, float]]:
        """The left and right of each column, and the left of each gap"""
        left: list[float] = []
        right: list[float] = []
        gap_left: dict[int, float] = {}
        x = 0.0
        for column, items in enumerate(self.items):
            width = max(
                (self.nodes[item.node].width for item in items if item.node is not None),
                default=0.0,
            )
            left.append(x)
            right.append(x + width)
            gap_left[column] = x + width
            tracks = max(gap_tracks.get(column, 0) - 1, 0)
            x += width + 2 * self.gap_margin + tracks * TRACK_SPACING
        return left, right, gap_left


def netlist_layout(
    nodes: dict[str, NodeShape],
    inputs: Iterable[str],
    outputs: Iterable[str],
    connections: Iterable[tuple[Pin, Pin]],
    order_ports: bool = False,
    gap_margin: float = GAP_MARGIN,
    bundles: bool = False,
) -> Layout:
    """
    Lay out the nodes in columns, the 'inputs' (nodes) in the first and the 'outputs' in
    the last, and route the wires of the connections (source pin, sink pin). The inputs
    and outputs keep their order, unless 'order_ports' (they are ordered like the others,
    to cross few wires). The tracks of the wires between two columns are 'gap_margin' from
    the columns. With 'bundles', the wires that pass columns and the bundles of parallel
    wires are straight first (the priority method), which makes a big netlist much higher.
    """
    router = _Router(
        nodes, list(inputs), list(outputs), list(connections), order_ports, gap_margin, bundles
    )
    return router.route()

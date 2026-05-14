"""Cross-collection spatio-temporal matching.

Given items from N collections (already filtered by the normal STAC search),
group them into scene-sets where every collection contributes one item that is
spatially overlapping and temporally close to an anchor item from the first
collection.

Anchor-based greedy algorithm:
    - Sort items in each non-anchor collection by datetime.
    - For every anchor item, pick the temporally-closest item from each other
      collection whose geometry intersects the anchor geometry (and whose
      overlap ratio meets ``min_overlap_ratio``) within ``max_interval``.
    - Emit a MatchGroup only when every collection contributes.

Spatial overlap is computed via shapely from each item's GeoJSON ``geometry``
field, which captures the actual valid-data footprint more accurately than bbox.

Complexity is O(N_anchor * sum(N_other)) which is fine for typical per-AOI
result sizes (hundreds to low thousands).
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import timedelta

from shapely.geometry import shape as _shape

def _overlap_ratio(geom_a: dict, geom_b: dict) -> float:
    """Return intersection_area / min(area_a, area_b); 0 if no overlap.

    Accepts GeoJSON geometry dicts (as stored in Item.geometry).
    """
    try:
        a = _shape(geom_a)
        b = _shape(geom_b)
        inter = a.intersection(b).area
        denom = min(a.area, b.area)
        return inter / denom if denom > 0 else 0.0
    except Exception:
        return 0.0


@dataclass
class MatchGroup:
    """One matched scene across N collections."""
    anchor_collection: str
    items: dict[str, object] = field(default_factory=dict)  # {collection: Item}
    max_time_delta_seconds: float = 0.0


def match_across_collections(
    items_by_collection: dict[str, list],
    max_interval_days: float = 3.0,
    min_overlap_ratio: float = 0.1,
    anchor_collection: str | None = None,
) -> list[MatchGroup]:
    """Match items across collections by geometry overlap + time proximity.

    Args:
        items_by_collection: {collection_name: [Item, ...]}. Items must expose
            ``datetime`` (datetime object) and ``geometry`` (GeoJSON dict)
            attributes (as populated by Item.parse).
        max_interval_days: Max absolute time difference between any collection
            item and the anchor item, in days.
        min_overlap_ratio: Min geometry intersection ratio normalised by the
            smaller footprint area.
        anchor_collection: Which collection to anchor on. Defaults to the
            collection with the fewest items (minimises outer-loop work and
            typically yields the most complete matches).

    Returns:
        List of MatchGroup, one per anchor item that found a partner in every
        other collection. Stable: ordered by anchor datetime.
    """
    collections = [c for c, items in items_by_collection.items() if items]
    if len(collections) < 2:
        return []

    if anchor_collection is None or anchor_collection not in collections:
        anchor_collection = min(collections, key=lambda c: len(items_by_collection[c]))

    others = [c for c in collections if c != anchor_collection]

    # Pre-sort non-anchor collections by datetime for binary search.
    sorted_others: dict[str, tuple[list, list]] = {}
    for c in others:
        items = [it for it in items_by_collection[c] if getattr(it, "datetime", None)]
        items.sort(key=lambda it: it.datetime)
        times = [it.datetime for it in items]
        sorted_others[c] = (items, times)

    max_delta = timedelta(days=max_interval_days)
    groups: list[MatchGroup] = []

    anchor_items = [
        it for it in items_by_collection[anchor_collection]
        if getattr(it, "datetime", None) and getattr(it, "geometry", None)
    ]
    anchor_items.sort(key=lambda it: it.datetime)

    for anchor in anchor_items:
        group = MatchGroup(anchor_collection=anchor_collection)
        group.items[anchor_collection] = anchor
        max_dt = 0.0
        complete = True

        for c in others:
            items, times = sorted_others[c]
            if not items:
                complete = False
                break

            # Narrow to the time window via binary search, then pick the
            # temporally-closest candidate whose geometry overlap meets threshold.
            lo = bisect_left(times, anchor.datetime - max_delta)
            hi = bisect_left(times, anchor.datetime + max_delta)
            window = items[lo:hi]

            best = None
            best_dt = None
            for cand in window:
                if not getattr(cand, "geometry", None):
                    continue
                dt_sec = abs((cand.datetime - anchor.datetime).total_seconds())
                if _overlap_ratio(anchor.geometry, cand.geometry) < min_overlap_ratio:
                    continue
                if best_dt is None or dt_sec < best_dt:
                    best = cand
                    best_dt = dt_sec

            if best is None:
                complete = False
                break
            group.items[c] = best
            if best_dt > max_dt:
                max_dt = best_dt

        if complete:
            group.max_time_delta_seconds = max_dt
            groups.append(group)

    return groups

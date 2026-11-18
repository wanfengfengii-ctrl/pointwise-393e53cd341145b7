from dataclasses import dataclass
from typing import Iterable

from packages.contacts import ContactEndpoint, SegmentContact


@dataclass(frozen=True, slots=True)
class OverlapRun:
    start: ContactEndpoint
    end: ContactEndpoint


def merge_overlaps(contacts: Iterable[SegmentContact]) -> tuple[OverlapRun, ...]:
    """Prepare report spans from the positive-length contact records."""
    starts = set()
    ends = set()
    runs = []
    for contact in contacts:
        if contact.is_point:
            continue
        increasing_b = contact.end.b_station > contact.start.b_station
        start = (*contact.start.stations, increasing_b)
        end = (*contact.end.stations, increasing_b)
        if start in starts or end in ends:
            raise ValueError("ambiguous directed seam in contact evidence")
        starts.add(start)
        ends.add(end)
        runs.append(OverlapRun(contact.start, contact.end))
    return tuple(runs)

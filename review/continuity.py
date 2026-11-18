from dataclasses import dataclass
from typing import Iterable

from packages.contacts import ContactEndpoint, SegmentContact


@dataclass(frozen=True, slots=True)
class OverlapRun:
    # The original positive-length contacts that make up this run, in A order.
    pieces: tuple[SegmentContact, ...]

    @property
    def start(self) -> ContactEndpoint:
        return self.pieces[0].start

    @property
    def end(self) -> ContactEndpoint:
        return self.pieces[-1].end


def _direction(contact: SegmentContact) -> bool:
    """True when B mileage grows along the contact, False when it falls."""
    return contact.end.b_station > contact.start.b_station


def _chain(contacts: list[SegmentContact]) -> list[OverlapRun]:
    """Join contacts whose A and B mileages continue at the shared seam."""
    starts = {}
    ends = set()
    for contact in contacts:
        if contact.start.stations in starts or contact.end.stations in ends:
            raise ValueError('ambiguous directed seam in contact evidence')
        starts[contact.start.stations] = contact
        ends.add(contact.end.stations)

    runs = []
    for head in contacts:
        # A chain head is a contact that no other contact continues into.
        if head.start.stations in ends:
            continue
        pieces = [head]
        seen = {id(head)}
        while True:
            following = starts.get(pieces[-1].end.stations)
            if following is None or id(following) in seen:
                break
            seen.add(id(following))
            pieces.append(following)
        runs.append(OverlapRun(tuple(pieces)))
    return runs


def merge_overlaps(contacts: Iterable[SegmentContact]) -> tuple[OverlapRun, ...]:
    """Prepare report spans from the positive-length contact records.

    Contacts only become one run when both A and B mileage continue at the
    shared seam and B points the same way.  Separate passages over the same
    ground therefore stay separate, each with its own mileage span, and a run
    keeps its original pieces so clipping can interpolate inside the piece a
    window end falls on.
    """
    spans = [contact for contact in contacts if not contact.is_point]
    ordered = sorted(spans, key=lambda c: (c.start.a_station, c.start.b_station, c.a_segment,
                                           c.b_segment))
    increasing = [c for c in ordered if _direction(c)]
    decreasing = [c for c in ordered if not _direction(c)]
    return tuple(_chain(increasing) + _chain(decreasing))

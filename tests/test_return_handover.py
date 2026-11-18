"""Regression tests for the return-passage handover incident.

The old build dropped the return leg while sealing (an unordered coordinate
footprint deduplication) and never merged legal adjacent overlap pieces while
signing, so one passage was reported as several.
"""

from fractions import Fraction

from tests.support import DeskCase, RETURN_A, SPLIT_B, evidence_rows, report_rows


class ReturnPassageTests(DeskCase):
    def test_both_passages_survive_sealing(self):
        a, b, receipt = self.seal(RETURN_A, SPLIT_B)
        self.stop_sources(a, b)
        self.reopen()
        package = self.desk.get_package(receipt.package_id)
        self.assertEqual(evidence_rows(package), [
            (1, 1, (2, 1), (3, 0)), (1, 2, (1, 2), (2, 1)),
            (2, 1, (5, 0), (6, 1)), (2, 2, (6, 1), (7, 2)),
        ])
        # The two original A segments cross the same ground in opposite
        # directions and are still distinct evidence rows.
        self.assertEqual(package.contacts[0].start.xy, (2, 0))
        self.assertEqual(package.contacts[2].end.xy, (2, 0))
        self.assertEqual(report_rows(self.desk.issue(receipt.package_id, 0, 8)), [
            ('reverse', (1, 2), (3, 0)), ('same', (5, 0), (7, 2)),
        ])
        self.assertEqual(report_rows(self.desk.issue(receipt.package_id, 2, 6)), [
            ('reverse', (2, 1), (3, 0)), ('same', (5, 0), (6, 1)),
        ])

    def test_aligned_pieces_merge_into_one_run(self):
        a, b, receipt = self.seal([(0, 0, 0), (4, 0, 4)],
                                  [(0, 0, 0), (2, 0, 2), (4, 0, 4)])
        self.stop_sources(a, b)
        self.assertEqual(len(self.desk.get_package(receipt.package_id).contacts), 2)
        self.assertEqual(report_rows(self.desk.issue(receipt.package_id, 0, 4)),
                         [('same', (0, 0), (4, 4))])
        # A seam inside the merged run is not reported as a separate point.
        self.assertEqual(report_rows(self.desk.issue(receipt.package_id, 2, 2)),
                         [('point', (2, 2), (2, 2))])

    def test_window_end_uses_its_own_piece(self):
        a, b, receipt = self.seal(
            [(0, 0, 0), (4, 0, 4)],
            [(0, 0, 0), (1, 0, 1), (4, 0, 5)],
        )
        self.stop_sources(a, b)
        # At A station 2 and 3 the second piece (A 1..4, B 1..5) rules:
        # B = 1 + (A - 1) * 4/3.
        report = self.desk.issue(receipt.package_id, 2, 3)
        self.assertEqual(report_rows(report), [
            ('same', (2, Fraction(7, 3)), (3, Fraction(11, 3))),
        ])
        # Interpolating against the whole run would have produced 5/2 and 15/4.
        self.assertNotIn(Fraction(5, 2), report.contacts[0].start)

    def test_opposite_direction_pieces_do_not_merge(self):
        a, b, receipt = self.seal(RETURN_A, SPLIT_B)
        self.stop_sources(a, b)
        full = self.desk.issue(receipt.package_id, 0, 8)
        self.assertEqual([contact.kind for contact in full.contacts],
                         ['reverse', 'same'])

    def test_same_ground_different_passages_stay_separate(self):
        # B walks right over A's ground, steps away and walks back: two
        # increasing passages with the same coordinates but no shared seam.
        b_vertices = [(0, 0, 0), (2, 0, 1), (2, 1, 2), (1, 0, 3), (3, 0, 4)]
        a, b, receipt = self.seal([(0, 0, 0), (4, 0, 4)], b_vertices)
        self.stop_sources(a, b)
        report = self.desk.issue(receipt.package_id, 0, 4)
        self.assertEqual(report_rows(report), [
            ('same', (0, 0), (2, 1)), ('same', (1, 3), (3, 4)),
        ])

    def test_point_only_evidence_kept_once_per_mileage_pair(self):
        cross_a = [(-1, 0, 0), (0, 0, 1), (1, 0, 2)]
        cross_b = [(0, -1, 0), (0, 0, 1), (0, 1, 2)]
        a, b, receipt = self.seal(cross_a, cross_b)
        self.stop_sources(a, b)
        report = self.desk.issue(receipt.package_id, 0, 2)
        self.assertEqual(report_rows(report), [('point', (1, 1), (1, 1))])

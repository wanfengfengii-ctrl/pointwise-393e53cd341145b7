from dataclasses import replace
import json
from pathlib import Path

from handover.desk import HandoverDesk
from handover.receipts import insert_receipt
from handover.session import write_transaction
from jobs.lifecycle import complete_order
from packages.codec import decode_package
from packages.store import insert_package


def evidence_rows(package):
    return [[row.a_segment, row.b_segment, list(map(str, row.start.stations)),
             list(map(str, row.end.stations))] for row in package.contacts]


def report_rows(report):
    return [[row.kind, list(map(str, row.start)), list(map(str, row.end))]
            for row in report.contacts]


def main() -> int:
    samples = Path(__file__).resolve().parent / "samples"
    source = json.loads((samples / "return-survey.json").read_text(encoding="utf-8"))
    fixture = decode_package((samples / "manual-package.json").read_text(encoding="utf-8"))
    with HandoverDesk(":memory:") as desk:
        a = desk.register(source["a"]["line_code"], source["a"]["vertices"])
        b = desk.register(source["b"]["line_code"], source["b"]["vertices"])
        sealed = desk.publish(desk.order(a, b))
        order_id = desk.order(a, b)
        manual = replace(fixture, order_id=order_id, a_revision_id=a, b_revision_id=b)
        connection = desk._connection
        with write_transaction(connection):
            manual_id = insert_package(connection, manual)
            receipt = insert_receipt(connection, manual_id, order_id)
            complete_order(connection, order_id, receipt.receipt_id)
        desk.retire(a)
        desk.retire(b)
        actual = {"evidence": evidence_rows(desk.get_package(sealed.package_id))}
        for label, package_id in (("sealed", sealed.package_id), ("manual", manual_id)):
            actual[label] = {
                "full": report_rows(desk.issue(package_id, *source["full_window"])),
                "section": report_rows(desk.issue(package_id, *source["section_window"])),
            }
    expected = {"evidence": source["expected_evidence"],
                "sealed": source["expected_reports"], "manual": source["expected_reports"]}
    differences = {key: {"expected": expected[key], "actual": rows}
                   for key, rows in actual.items() if rows != expected[key]}
    if differences:
        print("SURVEY_HANDOVER_MISMATCH " + json.dumps(differences, sort_keys=True))
        return 1
    print(json.dumps(actual, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import os
import sys

# Ensure the backend root (parent of tests) is on sys.path for direct execution
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from repositories.db import QueryCleaner

# Simple console-based tests for QueryCleaner without external frameworks
# Prints PASS/FAIL and exits with status code accordingly

def assert_equal(actual, expected, msg):
    if actual != expected:
        print(f"FAIL: {msg}\n  expected: {expected}\n  actual:   {actual}")
        return False
    return True


def run_tests():
    qc = QueryCleaner()
    all_ok = True

    # 1) Driver full_name and acronym replacement with counters
    sql = "SELECT * FROM drivers WHERE full_name = 'Max Verstappen' OR name_acronym = 'HAM' OR full_name='Sergio Perez'"
    cleaned, data = qc.clean_query(sql)
    expected_cleaned = (
        "SELECT * FROM drivers WHERE full_name = :driver_1 OR name_acronym = :acronym_1 OR full_name = :driver_2"
    )
    all_ok &= assert_equal(cleaned, expected_cleaned, "driver name/acronym replacements")

    expected_keys = {"driver_1", "driver_2", "acronym_1"}
    actual_keys = {d.key for d in data if d.type in ("driver_full_name", "driver_acronym")}
    all_ok &= assert_equal(actual_keys, expected_keys, "extracted driver keys")

    # 2) Meeting info
    sql = "SELECT * FROM meetings WHERE meeting_official_name = 'Austrian Grand Prix' AND location='Spielberg'"
    cleaned, data = qc.clean_query(sql)
    expected_cleaned = (
        "SELECT * FROM meetings WHERE meeting_official_name = :meeting_1 AND location = :location_1"
    )
    all_ok &= assert_equal(cleaned, expected_cleaned, "meeting name/location replacements")

    # Validate extracted types order-insensitively
    types = sorted([(d.type, d.key, d.data) for d in data])
    expected_types = sorted([
        ("meeting_name", "meeting_1", "Austrian Grand Prix"),
        ("meeting_location", "location_1", "Spielberg"),
    ])
    all_ok &= assert_equal(types, expected_types, "meeting extracted data")

    # 3) Session info
    sql = "SELECT * FROM sessions WHERE session_name='Qualifying' AND session_type = 'Race'"
    cleaned, data = qc.clean_query(sql)
    expected_cleaned = (
        "SELECT * FROM sessions WHERE session_name = :session_1 AND session_type = :session_type_1"
    )
    all_ok &= assert_equal(cleaned, expected_cleaned, "session name/type replacements")

    types = sorted([(d.type, d.key, d.data) for d in data])
    expected_types = sorted([
        ("session_name", "session_1", "Qualifying"),
        ("session_type", "session_type_1", "Race"),
    ])
    all_ok &= assert_equal(types, expected_types, "session extracted data")

    # 4) Stint info (tyre compound) including the earlier bug path
    sql = "SELECT * FROM stints WHERE compound = 'SOFT' OR compound = 'MEDIUM'"
    cleaned, data = qc.clean_query(sql)
    expected_cleaned = (
        "SELECT * FROM stints WHERE compound = :compound_1 OR compound = :compound_2"
    )
    all_ok &= assert_equal(cleaned, expected_cleaned, "stint compound replacements")

    types = sorted([(d.type, d.key, d.data) for d in data])
    expected_types = sorted([
        ("tyre_compound", "compound_1", "SOFT"),
        ("tyre_compound", "compound_2", "MEDIUM"),
    ])
    all_ok &= assert_equal(types, expected_types, "stint extracted data")

    # 5) Mixed query
    sql = (
        "SELECT * FROM everything WHERE full_name='Lewis Hamilton' AND meeting_official_name='British GP' "
        "AND session_name = 'FP1' AND compound='HARD' AND name_acronym = 'LEC'"
    )
    cleaned, data = qc.clean_query(sql)
    expected_cleaned = (
        "SELECT * FROM everything WHERE full_name = :driver_1 AND meeting_official_name = :meeting_1 "
        "AND session_name = :session_1 AND compound = :compound_1 AND name_acronym = :acronym_1"
    )
    all_ok &= assert_equal(cleaned, expected_cleaned, "mixed replacements")

    # Ensure we captured all five extractions at least
    type_counts = {}
    for d in data:
        type_counts[d.type] = type_counts.get(d.type, 0) + 1
    # Expect 1 of each for this mixed example
    expected_counts = {
        "driver_full_name": 1,
        "meeting_name": 1,
        "session_name": 1,
        "tyre_compound": 1,
        "driver_acronym": 1,
    }
    all_ok &= assert_equal(type_counts, expected_counts, "mixed extracted counts")

    if all_ok:
        print("ALL TESTS PASSED")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())

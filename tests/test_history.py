from iran_shortages.db import connect, upsert, start_run, record_source, record_observation, finish_run
from iran_shortages.models import ShortageSignal


def test_run_history_preserves_raw_signal_and_review_label(tmp_path):
    con = connect(str(tmp_path / "history.sqlite3"))
    item = ShortageSignal(title="کمبود قرص الف", url="https://example.org/a", source="example")
    assert upsert(con, item)
    run_id = start_run(con)
    record_observation(con, run_id, item.fingerprint, "candidate")
    record_source(con, run_id, "example", "ok", 1)
    finish_run(con, run_id, 1, 1)
    con.execute(
        "INSERT INTO review_labels(fingerprint, label, corrected_drug_name) VALUES (?, ?, ?)",
        (item.fingerprint, "confirmed_shortage", "الف"),
    )
    con.commit()
    assert con.execute("SELECT category, analysis_version FROM signal_observations").fetchone() == ("candidate", "rules-v1")
    assert con.execute("SELECT signals_seen, new_signals FROM collection_runs").fetchone() == (1, 1)
    assert con.execute("SELECT corrected_drug_name FROM review_labels").fetchone() == ("الف",)
    con.close()

from iran_shortages.db import connect, upsert
from iran_shortages.models import ShortageSignal

def test_dedup(tmp_path):
    db = tmp_path / "x.sqlite3"
    con = connect(str(db))
    s = ShortageSignal(title="کمبود سوتالول", url="https://example.com/a", source="test")
    assert upsert(con, s) is True
    assert upsert(con, s) is False
    n = con.execute("select count(*) from signals").fetchone()[0]
    assert n == 1
    con.close()

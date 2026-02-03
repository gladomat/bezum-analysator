"""IO utilities tests."""

from tg_checkstats.io import write_csv


def test_csv_writer_deterministic(tmp_path):
    rows = [{"a": 1, "b": 2}, {"a": 2, "b": 3}]
    path = tmp_path / "out.csv"
    write_csv(path, rows, ["a", "b"])
    lines = path.read_text().splitlines()
    assert lines[0] == "a,b"
    assert lines[1] == "1,2"

"""Export integration tests."""

from tg_checkstats.export import build_export_command


def test_build_export_command():
    cmd = build_export_command("mychat", "/tmp/out.json", 3, 5)
    assert "telegram-download-chat" in cmd[0]
    assert "mychat" in cmd

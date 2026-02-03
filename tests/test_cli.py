"""CLI tests."""


def test_cli_help_shows_commands(runner, cli):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "export" in result.output
    assert "analyze" in result.output
    assert "run" in result.output

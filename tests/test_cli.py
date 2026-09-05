from ai_feature_flags.cli import main


def test_show_examples_prints_one_line_per_flag(capsys):
    rc = main(["show-examples"])
    out = capsys.readouterr().out.strip().splitlines()
    assert rc == 0
    assert len(out) == 5


def test_validate_accepts_a_well_formed_flag_file(tmp_path):
    path = tmp_path / "flag.json"
    path.write_text(
        '{"key": "x.y", "type": "boolean", "default_value": true, '
        '"description": "d", "owner": "team", '
        '"created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"}'
    )
    assert main(["validate", str(path)]) == 0


def test_validate_rejects_a_type_mismatched_flag_file(tmp_path, capsys):
    path = tmp_path / "flag.json"
    path.write_text(
        '{"key": "x.y", "type": "boolean", "default_value": "not-a-bool", '
        '"description": "d", "owner": "team", '
        '"created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"}'
    )
    rc = main(["validate", str(path)])
    assert rc == 1
    assert "invalid flag definition" in capsys.readouterr().err


def test_validate_reports_missing_file(capsys):
    rc = main(["validate", "does/not/exist.json"])
    assert rc == 2

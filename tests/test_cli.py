import json

import pytest

from ai_feature_flags.cli import main


def _create_args(tmp_path, **overrides):
    args = {
        "key": "rag.enabled",
        "type": "boolean",
        "default": "true",
        "description": "Toggle RAG",
        "owner": "platform-ai",
    }
    args.update(overrides)
    argv = ["flag", "create", "--file-dir", str(tmp_path)]
    for name, value in args.items():
        argv += [f"--{name}", value]
    return argv


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


def test_flag_create_persists_and_prints_table(tmp_path, capsys):
    rc = main(_create_args(tmp_path))
    out = capsys.readouterr().out
    assert rc == 0
    assert "rag.enabled" in out
    assert "true" in out

    rc = main(["flag", "list", "--file-dir", str(tmp_path), "--json"])
    flags = json.loads(capsys.readouterr().out)
    assert len(flags) == 1
    assert flags[0]["key"] == "rag.enabled"
    assert flags[0]["default_value"] is True


def test_flag_create_rejects_duplicate_key(tmp_path, capsys):
    main(_create_args(tmp_path))
    rc = main(_create_args(tmp_path))
    assert rc == 1
    assert "already exists" in capsys.readouterr().err


def test_flag_create_rejects_type_mismatched_default(tmp_path, capsys):
    rc = main(_create_args(tmp_path, default="not-a-bool"))
    assert rc == 1
    assert "invalid flag definition" in capsys.readouterr().err


def test_flag_create_rejects_unknown_type_with_actionable_message(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(_create_args(tmp_path, type="not-a-real-type"))
    assert "invalid choice" in capsys.readouterr().err


def test_flag_create_rejects_missing_owner_with_actionable_message(tmp_path, capsys):
    argv = _create_args(tmp_path)
    # drop --owner and its value
    owner_idx = argv.index("--owner")
    del argv[owner_idx : owner_idx + 2]
    with pytest.raises(SystemExit):
        main(argv)
    assert "--owner" in capsys.readouterr().err


def test_flag_create_rejects_bad_json_for_object_type(tmp_path, capsys):
    rc = main(
        _create_args(tmp_path, key="x.rules", type="object", default="{not json}")
    )
    assert rc == 1
    assert "invalid flag definition" in capsys.readouterr().err


def test_flag_list_empty_store_reports_no_flags(tmp_path, capsys):
    rc = main(["flag", "list", "--file-dir", str(tmp_path)])
    assert rc == 0
    assert "(no flags)" in capsys.readouterr().out


def test_flag_update_changes_default_and_bumps_timestamp(tmp_path, capsys):
    main(_create_args(tmp_path))
    capsys.readouterr()

    rc = main(
        ["flag", "update", "--key", "rag.enabled", "--default", "false",
         "--file-dir", str(tmp_path), "--json"]
    )
    assert rc == 0
    updated = json.loads(capsys.readouterr().out)[0]
    assert updated["default_value"] is False
    assert updated["updated_at"] >= updated["created_at"]


def test_flag_update_missing_key_is_an_error(tmp_path, capsys):
    rc = main(["flag", "update", "--key", "nope", "--default", "false", "--file-dir", str(tmp_path)])
    assert rc == 1
    assert "no such flag" in capsys.readouterr().err


def test_flag_delete_removes_flag(tmp_path, capsys):
    main(_create_args(tmp_path))
    capsys.readouterr()

    rc = main(["flag", "delete", "--key", "rag.enabled", "--file-dir", str(tmp_path)])
    assert rc == 0
    assert "deleted rag.enabled" in capsys.readouterr().out

    rc = main(["flag", "list", "--file-dir", str(tmp_path), "--json"])
    assert json.loads(capsys.readouterr().out) == []


def test_flag_delete_missing_key_is_an_error(tmp_path, capsys):
    rc = main(["flag", "delete", "--key", "nope", "--file-dir", str(tmp_path)])
    assert rc == 1
    assert "no such flag" in capsys.readouterr().err

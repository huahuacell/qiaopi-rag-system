from app import settings


def test_bool_from_env_parses_true_and_false_values():
    assert settings._bool_from_env("true") is True
    assert settings._bool_from_env("TRUE") is True
    assert settings._bool_from_env("1") is True
    assert settings._bool_from_env("yes") is True
    assert settings._bool_from_env("false") is False
    assert settings._bool_from_env("FALSE") is False
    assert settings._bool_from_env("0") is False
    assert settings._bool_from_env("no") is False
    assert settings._bool_from_env("unknown", default=True) is True


def test_backend_env_file_values_override_root_env_and_ignore_example(tmp_path):
    project_root = tmp_path / "project"
    backend_dir = project_root / "backend"
    backend_dir.mkdir(parents=True)

    (project_root / ".env").write_text(
        "\n".join(
            [
                "QWEN_ENABLED=false",
                "QWEN_MODEL=root-model",
                "QWEN_API_KEY=root-key",
            ]
        ),
        encoding="utf-8",
    )
    (backend_dir / ".env").write_text(
        "\n".join(
            [
                "QWEN_ENABLED=true",
                "QWEN_API_KEY=backend-key",
                "QWEN_BASE_URL=https://qwen.example.test/compatible-mode/v1",
                "QWEN_MODEL=qwen-plus",
                "QWEN_TIMEOUT_SECONDS=30",
            ]
        ),
        encoding="utf-8",
    )
    (backend_dir / ".env.example").write_text(
        "\n".join(
            [
                "QWEN_ENABLED=false",
                "QWEN_API_KEY=example-key-must-not-load",
                "QWEN_MODEL=example-model",
            ]
        ),
        encoding="utf-8",
    )

    values = settings._load_env_file_values(
        backend_dir=backend_dir,
        project_root=project_root,
    )

    assert values["QWEN_ENABLED"] == "true"
    assert values["QWEN_API_KEY"] == "backend-key"
    assert values["QWEN_BASE_URL"] == "https://qwen.example.test/compatible-mode/v1"
    assert values["QWEN_MODEL"] == "qwen-plus"
    assert values["QWEN_TIMEOUT_SECONDS"] == "30"
    assert "example-key-must-not-load" not in values.values()

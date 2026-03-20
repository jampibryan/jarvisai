from app.config import AppConfig


def test_config_loads_defaults() -> None:
    config = AppConfig.load()

    assert config.app_name
    assert config.input_mode in {"text", "voice"}
    assert "drive_d" in config.path_aliases

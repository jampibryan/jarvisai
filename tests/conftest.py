import os

import pytest


@pytest.fixture(autouse=True)
def isolate_personal_settings(monkeypatch):
    for key in tuple(os.environ):
        if key.startswith('JARVIS_'):
            monkeypatch.delenv(key)
    monkeypatch.setattr('app.config._load_dotenv', lambda root: None)

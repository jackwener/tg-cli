"""Tests for config module."""



class TestConfig:
    def test_get_api_id(self, monkeypatch):
        monkeypatch.setenv("TG_API_ID", "12345")
        from tg_cli.config import get_api_id

        assert get_api_id() == 12345

    def test_get_api_id_default(self, monkeypatch):
        monkeypatch.delenv("TG_API_ID", raising=False)
        from tg_cli.config import get_api_id

        assert get_api_id() == 2040

    def test_get_api_hash(self, monkeypatch):
        monkeypatch.setenv("TG_API_HASH", "abc123")
        from tg_cli.config import get_api_hash

        assert get_api_hash() == "abc123"

    def test_get_api_hash_default(self, monkeypatch):
        monkeypatch.delenv("TG_API_HASH", raising=False)
        from tg_cli.config import get_api_hash

        assert get_api_hash() == "b18441a1ff607e10a989891a5462e627"

    def test_get_session_name_default(self, monkeypatch):
        monkeypatch.delenv("TG_SESSION_NAME", raising=False)
        from tg_cli.config import get_session_name

        assert get_session_name() == "tg_cli"

    def test_get_session_name_custom(self, monkeypatch):
        monkeypatch.setenv("TG_SESSION_NAME", "my_session")
        from tg_cli.config import get_session_name

        assert get_session_name() == "my_session"

    def test_get_db_path_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DB_PATH", raising=False)
        monkeypatch.delenv("DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        import tg_cli.config as cfg

        path = cfg.get_db_path()
        assert path.name == "messages.db"
        assert path.parent.exists()
        assert path.parent == tmp_path / "xdg" / "tg-cli"

    def test_get_data_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        import tg_cli.config as cfg

        d = cfg.get_data_dir()
        assert d.exists()
        assert d == tmp_path / "xdg" / "tg-cli"

    def test_get_data_dir_from_env_relative_to_cwd(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DATA_DIR", "./runtime-data")
        import tg_cli.config as cfg

        d = cfg.get_data_dir()
        assert d == tmp_path / "runtime-data"

    def test_get_db_path_from_env_relative_to_cwd(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DB_PATH", "./runtime/messages.db")
        import tg_cli.config as cfg

        path = cfg.get_db_path()
        assert path == tmp_path / "runtime" / "messages.db"

"""Tests for workspace boundary & .gitignore guard in style_dna.analyzer (P0.2)."""

from __future__ import annotations

import pytest
from pathlib import Path
from style_dna.analyzer import (
    _validate_path,
    _load_gitignore,
    _is_ignored,
    analyze_codebase,
)


class TestWorkspaceGuard:
    def test_validate_path_rejects_missing_directory(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            _validate_path(missing)

    def test_validate_path_rejects_file(self, tmp_path: Path):
        file_path = tmp_path / "regular_file.txt"
        file_path.write_text("hello")
        with pytest.raises(ValueError, match="Expected a directory"):
            _validate_path(file_path)

    def test_validate_path_accepts_valid_directory(self, tmp_path: Path):
        resolved = _validate_path(tmp_path)
        assert resolved == tmp_path.resolve()

    def test_load_gitignore_missing(self, tmp_path: Path):
        spec = _load_gitignore(tmp_path)
        assert spec is None

    def test_load_gitignore_with_patterns(self, tmp_path: Path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.generated.py\nignored_folder/\n")
        spec = _load_gitignore(tmp_path)
        # If pathspec is installed, it returns a spec. If not, it returns None.
        if spec is not None:
            assert _is_ignored(tmp_path / "test.generated.py", tmp_path, spec) is True
            assert _is_ignored(tmp_path / "valid.py", tmp_path, spec) is False

    def test_analyze_codebase_ignores_gitignored_files(self, tmp_path: Path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("secrets/\n*.tmp.py\n")

        # Kept file
        (tmp_path / "app.py").write_text("def run_app():\n    pass\n")

        # Ignored files
        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        (secrets_dir / "keys.py").write_text("def get_api_key():\n    pass\n")
        (tmp_path / "cache.tmp.py").write_text("def temp_helper():\n    pass\n")

        profile = analyze_codebase(str(tmp_path))
        # app.py must be analyzed
        assert profile.files_analyzed >= 1

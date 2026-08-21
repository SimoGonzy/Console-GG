"""Public release contract checks for Console GG."""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_root_quickstart_scripts_exist(self) -> None:
        """Removing a root installer/start/stop script breaks the public quickstart."""
        expected_scripts = [
            "install-linux.sh",
            "install-windows.ps1",
            "start-linux.sh",
            "stop-linux.sh",
            "start-windows.ps1",
            "stop-windows.ps1",
        ]

        missing = [script for script in expected_scripts if not (PROJECT_ROOT / script).is_file()]

        self.assertEqual(missing, [])

    def test_readme_bash_commands_point_to_existing_scripts(self) -> None:
        """Documented bash deploy commands should be copy-pasteable from the repo root."""
        docs = [
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "deploy" / "linux" / "README.md",
        ]
        missing: list[str] = []
        for doc in docs:
            for match in re.finditer(r"\bbash\s+([^\s`]+\.sh)", doc.read_text(encoding="utf-8")):
                script_path = PROJECT_ROOT / match.group(1)
                if not script_path.is_file():
                    missing.append(f"{doc.relative_to(PROJECT_ROOT)} -> {match.group(1)}")

        self.assertEqual(missing, [])

    def test_deploy_root_compatibility_wrappers_exist(self) -> None:
        """Old deploy/*.sh commands should keep working after moving Linux scripts."""
        expected_wrappers = [
            "deploy/install-docker.sh",
            "deploy/docker-up.sh",
            "deploy/docker-down.sh",
            "deploy/diagnose-docker.sh",
            "deploy/install-linux.sh",
            "deploy/enable-linux-autostart.sh",
            "deploy/diagnose-linux.sh",
        ]

        missing = [wrapper for wrapper in expected_wrappers if not (PROJECT_ROOT / wrapper).is_file()]

        self.assertEqual(missing, [])

    def test_direct_game_launchers_live_under_launchers_directory(self) -> None:
        """Root play_*.py files clutter the public repo and should live under launchers/."""
        root_launchers = sorted(path.name for path in PROJECT_ROOT.glob("play_*.py"))
        expected_launchers = [
            "play_2048.py",
            "play_battleship.py",
            "play_blackjack.py",
            "play_block_dropper.py",
            "play_dungeon.py",
            "play_forza4.py",
            "play_minesweeper.py",
            "play_snake.py",
            "play_tris.py",
            "play_wordle.py",
        ]
        actual_launchers = sorted(path.name for path in (PROJECT_ROOT / "launchers").glob("play_*.py"))

        self.assertEqual(root_launchers, [])
        self.assertEqual(actual_launchers, expected_launchers)

    def test_readme_direct_launcher_commands_use_launchers_directory(self) -> None:
        """README launcher examples should match the public folder layout."""
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertNotRegex(readme, r"python\s+play_[a-z0-9_]+\.py")
        self.assertIn("python launchers/play_blackjack.py", readme)

    def test_shell_scripts_are_forced_to_lf_in_git(self) -> None:
        """Windows checkouts must not rewrite Linux shell installers to CRLF."""
        attributes_path = PROJECT_ROOT / ".gitattributes"

        self.assertTrue(attributes_path.is_file())

        attributes = attributes_path.read_text(encoding="utf-8")

        self.assertIn("*.sh text eol=lf", attributes.splitlines())

    def test_local_installers_skip_private_experiment_files(self) -> None:
        """Local VM installers should not copy private experiments into the runtime app dir."""
        linux_installer = (PROJECT_ROOT / "deploy" / "linux" / "install-linux.sh").read_text(encoding="utf-8")
        windows_installer = (PROJECT_ROOT / "deploy" / "windows" / "install-windows-ssh.ps1").read_text(
            encoding="utf-8"
        )

        for expected in ("winner_bot", "test_winner_bot_*.py", "docs/superpowers"):
            self.assertIn(expected, linux_installer)

        for expected in ("winner_bot", "test_winner_bot_*.py", "docs\\superpowers"):
            self.assertIn(expected, windows_installer)

    def test_private_experiments_are_not_tracked_for_public_release(self) -> None:
        """winner_bot and related experimental material must not be in the public git index."""
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked_paths = set(result.stdout.splitlines())
        private_paths = sorted(
            path
            for path in tracked_paths
            if path.startswith("winner_bot/")
            or path.startswith("tests/test_winner_bot_")
            or path.startswith("docs/superpowers/")
            or "winner-bot" in path
            or "blackjack-learning" in path
        )

        self.assertEqual(private_paths, [])


if __name__ == "__main__":
    unittest.main()

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASH = os.environ.get("TEST_BASH", "bash")


class DeploymentProcessTests(unittest.TestCase):
    def run_entrypoint(self, enabled=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "app"
            bin_dir = root / "bin"
            (app / ".venv" / "bin").mkdir(parents=True)
            (app / "deploy").mkdir()
            bin_dir.mkdir()
            shutil.copy(ROOT / "deploy" / "nginx.conf.template", app / "deploy")

            def shell_path(path):
                if os.name == "nt":
                    return subprocess.check_output(
                        [BASH, "-c", 'cygpath -u "$1"', "test", str(path)],
                        text=True,
                    ).strip()
                return str(path)

            app_path = shell_path(app)
            config_path = shell_path(root / "nginx.conf")
            log_path = shell_path(root / "started")
            script = (ROOT / "deploy" / "start.sh").read_text()
            script = script.replace("/app", app_path).replace(
                "/tmp/eitz-nginx.conf", config_path
            )
            (root / "start.sh").write_text(script, newline="\n")

            def stub(path, name, delay):
                path.write_text(
                    f'#!/usr/bin/env bash\nprintf "%s\\n" "{name}" >> "{log_path}"\nsleep {delay}\n',
                    newline="\n",
                )
                path.chmod(0o755)

            stub(app / ".venv" / "bin" / "streamlit", "streamlit", 3)
            stub(app / ".venv" / "bin" / "python", "mcp", 3)
            stub(bin_dir / "nginx", "nginx", 1)
            env = os.environ.copy()
            env.update({
                "DB_READ_ONLY_USERNAME": "test",
                "DB_READ_ONLY_PASSWORD": "test",
                "PORT": "8080",
                "PATH": str(bin_dir) + os.pathsep + env["PATH"],
            })
            env.pop("MCP_ENABLED", None)
            if enabled is not None:
                env["MCP_ENABLED"] = enabled
            result = subprocess.run(
                [BASH, shell_path(root / "start.sh")],
                env=env, capture_output=True, text=True, timeout=15,
            )
            started = (root / "started").read_text().splitlines() if (root / "started").exists() else []
            config = (root / "nginx.conf").read_text() if (root / "nginx.conf").exists() else ""
            return result, started, config

    def test_disabled_starts_only_website_and_nginx(self):
        result, started, config = self.run_entrypoint("false")
        self.assertNotEqual(result.returncode, 0)
        self.assertCountEqual(started, ["streamlit", "nginx"])
        self.assertIn("return 503;", config)
        self.assertIn("proxy_pass http://127.0.0.1:8501;", config)
        self.assertIn("MCP is disabled", result.stdout)

    def test_enabled_starts_mcp_and_preserves_routing(self):
        for enabled in (None, "true"):
            with self.subTest(enabled=enabled):
                result, started, config = self.run_entrypoint(enabled)
                self.assertNotEqual(result.returncode, 0)
                self.assertCountEqual(started, ["streamlit", "mcp", "nginx"])
                self.assertIn("proxy_pass http://127.0.0.1:8502;", config)
                self.assertIn("proxy_pass http://127.0.0.1:8501;", config)

    def test_invalid_setting_fails_before_starting_children(self):
        for enabled in ("no", ""):
            with self.subTest(enabled=enabled):
                result, started, _ = self.run_entrypoint(enabled)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("MCP_ENABLED must be true or false", result.stderr)
                self.assertEqual(started, [])


if __name__ == "__main__":
    unittest.main()

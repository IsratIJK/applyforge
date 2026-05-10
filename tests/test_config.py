import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import config as config_module


class ConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        config_module._config = None

    def test_validate_raises_for_missing_required_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                "os.environ",
                {
                    "OUTPUT_DIR": str(Path(temp_dir) / "output"),
                    "LOGS_DIR": str(Path(temp_dir) / "logs"),
                    "RESUMES_DIR": str(Path(temp_dir) / "resumes"),
                    "RAW_RESUMES_DIR": str(Path(temp_dir) / "raw_resumes"),
                },
                clear=True,
            ):
                cfg = config_module.Config()

        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY is required"):
            cfg.validate()

    def test_post_init_creates_expected_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "nested" / "output"
            logs_dir = Path(temp_dir) / "nested" / "logs"
            resumes_dir = Path(temp_dir) / "nested" / "resumes"
            raw_resumes_dir = Path(temp_dir) / "nested" / "raw_resumes"

            with patch.dict(
                "os.environ",
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SERVICE_ACCOUNT": '{"type":"service_account"}',
                    "OUTPUT_DIR": str(output_dir),
                    "LOGS_DIR": str(logs_dir),
                    "RESUMES_DIR": str(resumes_dir),
                    "RAW_RESUMES_DIR": str(raw_resumes_dir),
                },
                clear=True,
            ):
                config_module.Config()

            for directory in (output_dir, logs_dir, resumes_dir, raw_resumes_dir):
                self.assertTrue(directory.exists(), f"Expected directory to exist: {directory}")

    def test_get_config_returns_singleton_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                "os.environ",
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SERVICE_ACCOUNT": '{"type":"service_account"}',
                    "OUTPUT_DIR": str(Path(temp_dir) / "output"),
                    "LOGS_DIR": str(Path(temp_dir) / "logs"),
                    "RESUMES_DIR": str(Path(temp_dir) / "resumes"),
                    "RAW_RESUMES_DIR": str(Path(temp_dir) / "raw_resumes"),
                },
                clear=True,
            ):
                first = config_module.get_config()
                second = config_module.get_config()

        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()

import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.modules.setdefault("fitz", types.ModuleType("fitz"))

resume_optimizer = importlib.import_module("services.resume_optimizer")
_clean_extracted_text = resume_optimizer._clean_extracted_text
extract_pdf_text = resume_optimizer.extract_pdf_text
load_resume_profile = resume_optimizer.load_resume_profile


class ResumeOptimizerTests(unittest.TestCase):
    def test_clean_extracted_text_normalizes_symbols_spacing_and_blank_lines(self) -> None:
        raw_text = "Alpha  Beta\n\n\n• Bullet\nRésumé"

        cleaned = _clean_extracted_text(raw_text)

        self.assertEqual(cleaned, "Alpha Beta\n\n- Bullet\nR sum")

    def test_load_resume_profile_returns_type_specific_file_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resumes_dir = Path(temp_dir)
            (resumes_dir / "backend.txt").write_text("backend profile", encoding="utf-8")

            result = load_resume_profile(resumes_dir, "backend")

            self.assertEqual(result, "backend profile")

    def test_load_resume_profile_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resumes_dir = Path(temp_dir)
            (resumes_dir / "default.txt").write_text("default profile", encoding="utf-8")

            result = load_resume_profile(resumes_dir, "missing")

            self.assertEqual(result, "default profile")

    def test_load_resume_profile_raises_for_empty_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resumes_dir = Path(temp_dir)
            (resumes_dir / "default.txt").write_text("   ", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Resume profile is empty"):
                load_resume_profile(resumes_dir, "missing")

    def test_extract_pdf_text_raises_for_missing_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_pdf = Path(temp_dir) / "resume.pdf"

            with self.assertRaisesRegex(FileNotFoundError, "PDF not found"):
                extract_pdf_text(missing_pdf)

    def test_extract_pdf_text_skips_empty_pages_and_cleans_combined_text(self) -> None:
        class FakePage:
            def __init__(self, text: str) -> None:
                self._text = text

            def get_text(self) -> str:
                return self._text

        class FakeDoc:
            def __enter__(self) -> "FakeDoc":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def __iter__(self):
                return iter([FakePage("Alpha  Beta"), FakePage("   "), FakePage("• Bullet")])

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "resume.pdf"
            pdf_path.write_text("placeholder", encoding="utf-8")

            with patch("services.resume_optimizer.fitz.open", return_value=FakeDoc()):
                extracted = extract_pdf_text(pdf_path)

        self.assertEqual(extracted, "Alpha Beta\n- Bullet")


if __name__ == "__main__":
    unittest.main()

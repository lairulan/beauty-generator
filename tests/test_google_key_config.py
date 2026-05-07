import os
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_beauty


class GoogleKeyConfigTests(unittest.TestCase):
    def test_imagen_ultra_model_remains_primary_for_text_to_image(self):
        self.assertEqual(generate_beauty.GOOGLE_MODEL, "imagen-4.0-ultra-generate-001")
        self.assertIn("imagen-4.0-ultra-generate-001", generate_beauty.GOOGLE_IMAGEN_ENDPOINT)
        self.assertEqual(generate_beauty.GOOGLE_API_KEY_ENV, "GEMINI_API_KEY")

    def test_prefers_unified_gemini_key_over_legacy_google_key(self):
        env = {
            "GEMINI_API_KEY": "gemini-key",
            "GOOGLE_API_KEY": "legacy-key",
            "GOOGLE_API_KEY_BACKUP": "backup-key",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                generate_beauty._get_google_key_candidates(),
                [("GEMINI_API_KEY", "gemini-key")],
            )

    def test_legacy_google_key_is_only_local_compatibility_fallback(self):
        env = {
            "GOOGLE_API_KEY": "legacy-key",
            "GOOGLE_API_KEY_BACKUP": "backup-key",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                generate_beauty._get_google_key_candidates(),
                [("GOOGLE_API_KEY legacy", "legacy-key")],
            )

    def test_backup_key_is_no_longer_used(self):
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY_BACKUP": "backup-key"}, clear=True):
            self.assertEqual(generate_beauty._get_google_key_candidates(), [])


if __name__ == "__main__":
    unittest.main()

import json
import os
import unittest
from engine.security.vault import open_credential, VaultDecryptionError

class TestVaultCrossLanguage(unittest.TestCase):
    def setUp(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "..", "docs", "fixtures", "vault_vectors.json")
        with open(fixture_path, "r", encoding="utf-8") as f:
            self.fixtures = json.load(f)
        self.master_key = bytes.fromhex(self.fixtures["key_hex"])

    def test_vectors_decryption(self):
        for vec in self.fixtures["vectors"]:
            envelope = {
                "nonce": vec["nonce_base64"],
                "ct": vec["ct_base64"],
                "tag": vec["tag_base64"]
            }
            camera_id = vec["camera_id"]
            expected_pt = vec["plaintext"]

            decrypted = open_credential(camera_id, envelope, self.master_key)
            self.assertEqual(decrypted, expected_pt, f"Decryption mismatch for {vec['name']}")

    def test_tampered_ciphertext_fails(self):
        vec = self.fixtures["vectors"][0]
        # Modify the first character of ciphertext
        tampered_ct = ("A" if vec["ct_base64"][0] != "A" else "B") + vec["ct_base64"][1:]
        envelope = {
            "nonce": vec["nonce_base64"],
            "ct": tampered_ct,
            "tag": vec["tag_base64"]
        }
        with self.assertRaises(VaultDecryptionError):
            open_credential(vec["camera_id"], envelope, self.master_key)

    def test_wrong_camera_id_aad_mismatch_fails(self):
        vec = self.fixtures["vectors"][0]
        envelope = {
            "nonce": vec["nonce_base64"],
            "ct": vec["ct_base64"],
            "tag": vec["tag_base64"]
        }
        # Attempt to open credential belonging to cam-north-gate-01 using cam-other
        with self.assertRaises(VaultDecryptionError):
            open_credential("cam-other-02", envelope, self.master_key)

if __name__ == "__main__":
    unittest.main()

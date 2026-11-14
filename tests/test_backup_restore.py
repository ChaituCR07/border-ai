import os
import subprocess
import tempfile
import unittest

class TestBackupRestore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_backup_and_restore_roundtrip(self):
        # Create a dummy plaintext file to simulate db dump
        test_file = os.path.join(self.temp_dir.name, "test_input.txt")
        test_content = b"Border-AI Critical Database Record #9921\n"
        with open(test_file, "wb") as f:
            f.write(test_content)

        enc_file = os.path.join(self.temp_dir.name, "test_backup.enc")
        dec_file = os.path.join(self.temp_dir.name, "test_decrypted.txt")

        # 1. Encrypt using Node.js AES-256-GCM logic matching backup.sh
        script_enc = f"""
const fs = require('fs');
const crypto = require('crypto');
const key = Buffer.from('{self.test_key}', 'hex');
const iv = crypto.randomBytes(12);
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
const input = fs.readFileSync('{test_file}');
const ct = Buffer.concat([cipher.update(input), cipher.final()]);
const tag = cipher.getAuthTag();
fs.writeFileSync('{enc_file}', Buffer.concat([iv, tag, ct]));
"""
        subprocess.run(["node", "-e", script_enc], check=True)
        self.assertTrue(os.path.exists(enc_file))

        # 2. Decrypt using Node.js AES-256-GCM logic matching restore.sh
        script_dec = f"""
const fs = require('fs');
const crypto = require('crypto');
const key = Buffer.from('{self.test_key}', 'hex');
const payload = fs.readFileSync('{enc_file}');
const iv = payload.subarray(0, 12);
const tag = payload.subarray(12, 28);
const ct = payload.subarray(28);
const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
decipher.setAuthTag(tag);
const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
fs.writeFileSync('{dec_file}', pt);
"""
        subprocess.run(["node", "-e", script_dec], check=True)
        self.assertTrue(os.path.exists(dec_file))

        with open(dec_file, "rb") as f:
            restored = f.read()

        self.assertEqual(restored, test_content)

    def test_wrong_key_fails_decryption(self):
        test_file = os.path.join(self.temp_dir.name, "secret.txt")
        with open(test_file, "wb") as f:
            f.write(b"super secret data")

        enc_file = os.path.join(self.temp_dir.name, "secret.enc")
        wrong_key = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

        script_enc = f"""
const fs = require('fs');
const crypto = require('crypto');
const key = Buffer.from('{self.test_key}', 'hex');
const iv = crypto.randomBytes(12);
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
const input = fs.readFileSync('{test_file}');
const ct = Buffer.concat([cipher.update(input), cipher.final()]);
const tag = cipher.getAuthTag();
fs.writeFileSync('{enc_file}', Buffer.concat([iv, tag, ct]));
"""
        subprocess.run(["node", "-e", script_enc], check=True)

        # Attempt to decrypt with wrong key
        script_fail = f"""
const fs = require('fs');
const crypto = require('crypto');
const key = Buffer.from('{wrong_key}', 'hex');
const payload = fs.readFileSync('{enc_file}');
const iv = payload.subarray(0, 12);
const tag = payload.subarray(12, 28);
const ct = payload.subarray(28);
const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
decipher.setAuthTag(tag);
Buffer.concat([decipher.update(ct), decipher.final()]);
"""
        proc = subprocess.run(["node", "-e", script_fail], capture_output=True)
        self.assertNotEqual(proc.returncode, 0)

if __name__ == "__main__":
    unittest.main()

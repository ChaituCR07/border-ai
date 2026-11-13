import base64
import json
import time
import unittest
from engine.security.stream_auth import verify_stream_token, StreamAuthError

class TestStreamAuth(unittest.TestCase):
    def setUp(self):
        # Sample test JWK (Ed25519)
        self.jwks = {
            "keys": [
                {
                    "kty": "OKP",
                    "crv": "Ed25519",
                    "kid": "test-cam-key-01",
                    "x": "o8yq_xYJyvfgCPxVLcE-hjclXAKaTDQVrvVTSgZtxc0",
                    "use": "sig",
                    "alg": "EdDSA"
                }
            ]
        }

    def test_rejects_missing_segments(self):
        with self.assertRaises(StreamAuthError) as ctx:
            verify_stream_token("bad.token", "CAM-01", self.jwks)
        self.assertEqual(ctx.exception.code, "INVALID_TOKEN_FORMAT")

    def test_rejects_bad_algorithm(self):
        h = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "stream+jwt", "kid": "test-cam-key-01"}).encode()).decode().rstrip('=')
        p = base64.urlsafe_b64encode(json.dumps({"iss": "border-ai", "aud": "border-ai-stream", "cam": "CAM-01", "exp": int(time.time()) + 60}).encode()).decode().rstrip('=')
        token = f"{h}.{p}."
        with self.assertRaises(StreamAuthError) as ctx:
            verify_stream_token(token, "CAM-01", self.jwks)
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_ALGORITHM")

    def test_rejects_unknown_kid(self):
        h = base64.urlsafe_b64encode(json.dumps({"alg": "EdDSA", "typ": "stream+jwt", "kid": "unknown-kid"}).encode()).decode().rstrip('=')
        p = base64.urlsafe_b64encode(json.dumps({"iss": "border-ai", "aud": "border-ai-stream", "cam": "CAM-01", "exp": int(time.time()) + 60}).encode()).decode().rstrip('=')
        token = f"{h}.{p}.c2ln"
        with self.assertRaises(StreamAuthError) as ctx:
            verify_stream_token(token, "CAM-01", self.jwks)
        self.assertEqual(ctx.exception.code, "UNKNOWN_KEY")

if __name__ == '__main__':
    unittest.main()

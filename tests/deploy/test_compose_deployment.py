import os
import re
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class TestComposeDeploymentConfig(unittest.TestCase):
    def test_nginx_log_format_excludes_query_parameters(self):
        nginx_conf = os.path.join(ROOT_DIR, "docker", "nginx", "nginx.conf")
        with open(nginx_conf, "r", encoding="utf-8") as f:
            content = f.read()

        # Must log $uri and NOT $request_uri so access tokens in query strings are never logged
        self.assertIn("log_format main_noquery", content)
        self.assertIn("$uri", content)
        log_format_line = [l for l in content.splitlines() if "log_format main_noquery" in l][0]
        self.assertNotIn("$request_uri", log_format_line)

    def test_nginx_mjpeg_buffering_disabled(self):
        border_conf = os.path.join(ROOT_DIR, "docker", "nginx", "conf.d", "border-ai.conf")
        with open(border_conf, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("location /stream/ {", content)
        self.assertIn("proxy_buffering off;", content)
        self.assertIn("gzip off;", content)

    def test_nginx_blocks_internal_api_docs_in_production(self):
        border_conf = os.path.join(ROOT_DIR, "docker", "nginx", "conf.d", "border-ai.conf")
        with open(border_conf, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("location ~ ^/(docs|openapi\\.json) {", content)
        self.assertIn("return 404;", content)

    def test_redis_acl_uses_sha256_digests_only(self):
        acl_path = os.path.join(ROOT_DIR, "secrets", "users.acl")
        if not os.path.exists(acl_path):
            self.skipTest("secrets/users.acl not yet generated")

        with open(acl_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

        # user default off
        self.assertIn("user default off", lines)

        # Service users must have hashed passwords #<64-hex>
        for line in lines:
            if line.startswith("user ") and not line.startswith("user default"):
                match = re.search(r"on #([a-fA-F0-9]{64})", line)
                self.assertIsNotNone(
                    match,
                    f"Redis ACL user line must use SHA-256 hashed password: {line}"
                )

    def test_dockerfiles_enforce_unprivileged_user(self):
        dockerfiles = [
            os.path.join(ROOT_DIR, "docker", "backend", "Dockerfile"),
            os.path.join(ROOT_DIR, "docker", "ai-engine", "Dockerfile"),
        ]

        for df in dockerfiles:
            with open(df, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("USER 10001:10001", content, f"{df} must specify USER 10001:10001")

    def test_postgres_timezone_is_strictly_utc(self):
        pg_conf = os.path.join(ROOT_DIR, "docker", "postgres", "postgresql.conf")
        with open(pg_conf, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("timezone = 'UTC'", content)

if __name__ == "__main__":
    unittest.main()

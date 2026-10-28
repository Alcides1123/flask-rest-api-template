import base64
import json
import unittest

import manage
from app import create_app, db
from config import TestingConfig


class RateLimitedTestingConfig(TestingConfig):
    """TestingConfig normally disables rate limiting; this test needs it on."""

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_LOGIN = "3 per minute"
    RATELIMIT_REGISTER = "2 per minute"


class HardeningIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(settings_module=RateLimitedTestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            manage.init_db_user()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_is_rate_limited(self):
        bad = {"username": "admin", "password": "wrong"}
        codes = [self.client.post("/login", json=bad).status_code for _ in range(4)]
        self.assertEqual([401, 401, 401, 429], codes)

        response = self.client.post("/login", json=bad)
        self.assertEqual(429, response.status_code)
        self.assertIn("Retry-After", response.headers)
        self.assertEqual("application/json", response.mimetype)

        # Other endpoints are not affected by the login limit
        self.assertEqual(200, self.client.get("/openapi.json").status_code)

    def test_register_is_rate_limited(self):
        codes = [
            self.client.post(
                "/register", json={"username": f"u{i}", "password": "x"}
            ).status_code
            for i in range(3)
        ]
        self.assertEqual([200, 200, 429], codes)

    def test_jwt_subject_is_a_string(self):
        response = self.client.post(
            "/login", json={"username": "admin", "password": "123456"}
        )
        self.assertEqual(200, response.status_code)
        for token in response.get_json().values():
            payload = token.split(".")[1]
            payload = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            claims = json.loads(payload)
            self.assertIsInstance(claims["sub"], str)
            self.assertNotIn("is_admin", claims)

    def test_no_cors_headers_unless_configured(self):
        # TestingConfig inherits the default: CORS_ORIGINS empty
        self.assertEqual([], self.app.config["CORS_ORIGINS"])
        response = self.client.get(
            "/openapi.json", headers={"Origin": "https://evil.example"}
        )
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)


class ConfiguredCorsTests(unittest.TestCase):
    def test_only_configured_origin_is_allowed_without_credentials(self):
        class CorsConfig(TestingConfig):
            CORS_ORIGINS = ["https://app.example.com"]

        client = create_app(settings_module=CorsConfig).test_client()

        response = client.get(
            "/openapi.json", headers={"Origin": "https://app.example.com"}
        )
        self.assertEqual(
            "https://app.example.com",
            response.headers.get("Access-Control-Allow-Origin"),
        )
        self.assertNotIn("Access-Control-Allow-Credentials", response.headers)

        response = client.get(
            "/openapi.json", headers={"Origin": "https://evil.example"}
        )
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)


if __name__ == "__main__":
    unittest.main()

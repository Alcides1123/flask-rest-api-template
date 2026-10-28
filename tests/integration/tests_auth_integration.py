import os
import unittest

import manage
from app import create_app, db


class AuthIntegrationTests(unittest.TestCase):
    """
    HTTP-level tests for authentication / authorization behaviour.

    Each test gets a fresh schema seeded with the default permissions, roles
    and users from manage.init_db_user() (admin / user / guest, password 123456).
    """

    def setUp(self):
        self.app = create_app(
            settings_module=os.environ.get("APP_TEST_SETTINGS_MODULE")
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            manage.init_db_user()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # Helpers

    def login(self, username="admin", password="123456"):
        response = self.client.post(
            "/login", json={"username": username, "password": password}
        )
        self.assertEqual(200, response.status_code, response.get_json())
        return response.get_json()

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    # Tests

    def test_login_returns_token_pair(self):
        tokens = self.login()
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

    def test_login_with_wrong_password_is_rejected(self):
        response = self.client.post(
            "/login", json={"username": "admin", "password": "wrong"}
        )
        self.assertEqual(401, response.status_code)

    def test_password_hash_is_never_returned(self):
        tokens = self.login()
        headers = self.bearer(tokens["access_token"])

        response = self.client.get("/user", headers=headers)
        self.assertEqual(200, response.status_code)
        for user in response.get_json():
            self.assertNotIn("password", user)

        response = self.client.get("/user/1", headers=headers)
        self.assertEqual(200, response.status_code)
        self.assertNotIn("password", response.get_json())

    def test_logout_revokes_access_and_refresh_token(self):
        tokens = self.login()

        response = self.client.post(
            "/logout", headers=self.bearer(tokens["access_token"])
        )
        self.assertEqual(200, response.status_code)

        # The access token is revoked...
        response = self.client.get("/user", headers=self.bearer(tokens["access_token"]))
        self.assertEqual(401, response.status_code)
        self.assertEqual("token_revoked", response.get_json()["error"])

        # ...and so is the refresh token that was issued together with it.
        response = self.client.post(
            "/refresh", headers=self.bearer(tokens["refresh_token"])
        )
        self.assertEqual(401, response.status_code)
        self.assertEqual("token_revoked", response.get_json()["error"])

    def test_logout_twice_is_not_an_error(self):
        tokens = self.login()
        headers = self.bearer(tokens["access_token"])

        self.assertEqual(200, self.client.post("/logout", headers=headers).status_code)
        # Second call fails only because the token is already revoked, not with a 4xx/5xx from the blocklist insert.
        response = self.client.post("/logout", headers=headers)
        self.assertEqual(401, response.status_code)
        self.assertEqual("token_revoked", response.get_json()["error"])

    def test_refresh_token_is_single_use(self):
        tokens = self.login()
        refresh_headers = self.bearer(tokens["refresh_token"])

        response = self.client.post("/refresh", headers=refresh_headers)
        self.assertEqual(200, response.status_code)
        new_tokens = response.get_json()
        self.assertIn("access_token", new_tokens)
        self.assertIn("refresh_token", new_tokens)

        # Re-using the old refresh token must fail.
        response = self.client.post("/refresh", headers=refresh_headers)
        self.assertEqual(401, response.status_code)
        self.assertEqual("token_revoked", response.get_json()["error"])

        # The new pair works, and logging out with it revokes the new refresh token too.
        self.assertEqual(
            200,
            self.client.post(
                "/logout", headers=self.bearer(new_tokens["access_token"])
            ).status_code,
        )
        response = self.client.post(
            "/refresh", headers=self.bearer(new_tokens["refresh_token"])
        )
        self.assertEqual(401, response.status_code)

    def test_error_responses_do_not_leak_internal_details(self):
        tokens = self.login()
        headers = self.bearer(tokens["access_token"])

        # "Admin" already exists -> unique constraint violation in the database.
        response = self.client.post(
            "/role",
            headers=headers,
            json={"name": "Admin", "description": "dup", "permissions": [1]},
        )
        self.assertEqual(400, response.status_code)
        message = response.get_json()["message"].lower()
        for needle in (
            "sqlite",
            "psycopg",
            "sql",
            "integrityerror",
            "constraint",
            "traceback",
        ):
            self.assertNotIn(needle, message)

    def test_openapi_document_keeps_schemas_on_protected_endpoints(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(200, response.status_code)
        paths = response.get_json()["paths"]

        # @blp.response(...) behind @permission_required must still be documented
        self.assertIn("content", paths["/user"]["get"]["responses"]["200"])
        # @blp.arguments(...) behind @permission_required must still be documented
        self.assertIn("requestBody", paths["/role"]["post"])


if __name__ == "__main__":
    unittest.main()

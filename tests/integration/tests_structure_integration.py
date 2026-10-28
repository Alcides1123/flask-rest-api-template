import logging
import time
import unittest
from datetime import datetime, timedelta, timezone

import manage
from app import create_app, db
from app.models import BlocklistModel, UserModel
from config import TestingConfig


class StructureIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(settings_module=TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            manage.init_db_user()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def admin_headers(self):
        response = self.client.post(
            "/login", json={"username": "admin", "password": "123456"}
        )
        return {"Authorization": f"Bearer {response.get_json()['access_token']}"}

    def test_create_app_requires_a_settings_module(self):
        with self.assertRaises(RuntimeError):
            create_app(None)

    def test_importing_the_package_creates_no_app(self):
        import app as package

        self.assertFalse(hasattr(package, "app"))

    def test_logging_handlers_are_not_duplicated(self):
        for _ in range(3):
            create_app(settings_module=TestingConfig)
        handlers = logging.getLogger("app").handlers
        self.assertEqual(2, len(handlers), [type(h).__name__ for h in handlers])

    def test_read_endpoints_return_404_for_unknown_ids(self):
        headers = self.admin_headers()
        for url in ("/user/999", "/role/999", "/permission/999"):
            response = self.client.get(url, headers=headers)
            self.assertEqual(404, response.status_code, url)
            self.assertIn("message", response.get_json(), url)

    def test_time_created_is_set_per_row(self):
        headers = self.admin_headers()
        with self.app.app_context():
            admin_created = (
                UserModel.query.filter_by(username="admin").first().time_created
            )

        time.sleep(0.01)
        response = self.client.post(
            "/register", json={"username": "later", "password": "x"}
        )
        self.assertEqual(200, response.status_code)

        with self.app.app_context():
            later_created = (
                UserModel.query.filter_by(username="later").first().time_created
            )
        self.assertGreater(later_created, admin_created)

        # Serialised as an ISO-8601 timestamp
        with self.app.app_context():
            later_id = UserModel.query.filter_by(username="later").first().id
        body = self.client.get(f"/user/{later_id}", headers=headers).get_json()
        datetime.fromisoformat(body["time_created"])

    def test_blocklist_rows_carry_expiry_and_can_be_pruned(self):
        headers = self.admin_headers()
        self.assertEqual(200, self.client.post("/logout", headers=headers).status_code)

        with self.app.app_context():
            rows = BlocklistModel.query.all()
            self.assertEqual(2, len(rows))  # access + paired refresh token
            for row in rows:
                self.assertIsNotNone(row.expires_at)

            # Nothing has expired yet
            self.assertEqual(0, manage.prune_blocklist())
            self.assertEqual(2, BlocklistModel.query.count())

            # Expire one of them in the past -> pruned, the other stays
            rows[0].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.session.commit()
            self.assertEqual(1, manage.prune_blocklist())
            self.assertEqual(1, BlocklistModel.query.count())

    def test_unhandled_exception_is_a_generic_json_500_outside_testing(self):
        class ProductionLike(TestingConfig):
            TESTING = False
            DEBUG = False

        app = create_app(settings_module=ProductionLike)

        @app.route("/boom")
        def boom():
            raise RuntimeError("secret internal detail")

        response = app.test_client().get("/boom")
        self.assertEqual(500, response.status_code)
        self.assertEqual("application/json", response.mimetype)
        self.assertNotIn("secret internal detail", response.get_data(as_text=True))
        self.assertEqual(500, response.get_json()["code"])

    def test_wsgi_module_builds_app_from_environment(self):
        import importlib
        import os

        os.environ["APP_SETTINGS_MODULE"] = "config.TestingConfig"
        try:
            import wsgi

            wsgi = importlib.reload(wsgi)
            self.assertEqual("testing", wsgi.app.config["APP_ENV"])
        finally:
            os.environ.pop("APP_SETTINGS_MODULE", None)


if __name__ == "__main__":
    unittest.main()

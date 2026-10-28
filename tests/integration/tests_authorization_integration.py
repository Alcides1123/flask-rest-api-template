import os
import unittest

import manage
from app import create_app, db
from app.models import PermissionModel, RoleModel, UserModel


class AuthorizationIntegrationTests(unittest.TestCase):
    """
    HTTP-level tests for the role / permission model.

    Seeded accounts (manage.init_db_user):
        admin -> Admin role: read, write, delete, admin
        user  -> User role:  read, write
        guest -> Guest role: read
    """

    def setUp(self):
        self.app = create_app(
            settings_module=os.environ.get(
                "APP_TEST_SETTINGS_MODULE", "config.TestingConfig"
            )
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            manage.init_db_user()
            self.ids = {
                "users": {u.username: u.id for u in UserModel.query.all()},
                "roles": {r.name: r.id for r in RoleModel.query.all()},
                "permissions": {p.name: p.id for p in PermissionModel.query.all()},
            }

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # Helpers

    def headers_for(self, username, password="123456"):
        response = self.client.post(
            "/login", json={"username": username, "password": password}
        )
        self.assertEqual(200, response.status_code, response.get_json())
        return {"Authorization": f"Bearer {response.get_json()['access_token']}"}

    def user_id(self, username):
        return self.ids["users"][username]

    def role_id(self, name):
        return self.ids["roles"][name]

    def permission_id(self, name):
        return self.ids["permissions"][name]

    def roles_of(self, username, headers):
        response = self.client.get(f"/user/{self.user_id(username)}", headers=headers)
        self.assertEqual(200, response.status_code)
        return sorted(r["name"] for r in response.get_json()["roles"])

    # --- Privilege escalation (audit findings #1 / #2) ---

    def test_write_user_cannot_grant_itself_admin_role(self):
        headers = self.headers_for("user")

        response = self.client.put(
            f"/user/{self.user_id('user')}",
            headers=headers,
            json={"roles": [self.role_id("Admin")]},
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(["User"], self.roles_of("user", headers))

        # ...nor via the role-link endpoint
        response = self.client.post(
            f"/user/{self.user_id('user')}/role/{self.role_id('Admin')}",
            headers=headers,
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(["User"], self.roles_of("user", headers))

    def test_write_user_cannot_escalate_by_editing_roles_or_permissions(self):
        headers = self.headers_for("user")
        all_permissions = list(self.ids["permissions"].values())

        # Add every permission to the User role
        response = self.client.put(
            f"/role/{self.role_id('User')}",
            headers=headers,
            json={"name": "User", "description": "x", "permissions": all_permissions},
        )
        self.assertEqual(403, response.status_code)

        # Create a new all-powerful role
        response = self.client.post(
            "/role",
            headers=headers,
            json={"name": "Super", "description": "x", "permissions": all_permissions},
        )
        self.assertEqual(403, response.status_code)

        # Attach the User role to the admin permission
        response = self.client.put(
            "/permission-role-update",
            headers=headers,
            json={
                "data_update": {
                    str(self.permission_id("admin")): [self.role_id("User")]
                }
            },
        )
        self.assertEqual(403, response.status_code)

        # Delete a role
        response = self.client.delete(f"/role/{self.role_id('Guest')}", headers=headers)
        self.assertEqual(403, response.status_code)

        # Still cannot do something that needs "delete"
        response = self.client.delete(
            f"/role/{self.role_id('Guest')}", headers=self.headers_for("user")
        )
        self.assertEqual(403, response.status_code)

    def test_non_admin_cannot_update_other_users(self):
        headers = self.headers_for("user")

        response = self.client.put(
            f"/user/{self.user_id('admin')}",
            headers=headers,
            json={"password": "pwned"},
        )
        self.assertEqual(403, response.status_code)

        # Admin's password is unchanged
        response = self.client.post(
            "/login", json={"username": "admin", "password": "123456"}
        )
        self.assertEqual(200, response.status_code)

    def test_guest_cannot_do_anything_but_read(self):
        headers = self.headers_for("guest")

        self.assertEqual(200, self.client.get("/user", headers=headers).status_code)
        self.assertEqual(200, self.client.get("/role", headers=headers).status_code)

        response = self.client.post(
            "/role",
            headers=headers,
            json={"name": "x", "description": "x", "permissions": []},
        )
        self.assertEqual(403, response.status_code)
        response = self.client.put(
            f"/block-user/{self.user_id('user')}",
            headers=headers,
            json={"block": True},
        )
        self.assertEqual(403, response.status_code)

    # --- What users MAY do with their own account ---

    def test_any_user_can_change_own_password(self):
        headers = self.headers_for("guest")

        response = self.client.put(
            f"/user/{self.user_id('guest')}",
            headers=headers,
            json={"password": "new-password"},
        )
        self.assertEqual(200, response.status_code)

        self.assertEqual(
            200,
            self.client.post(
                "/login", json={"username": "guest", "password": "new-password"}
            ).status_code,
        )
        self.assertEqual(
            401,
            self.client.post(
                "/login", json={"username": "guest", "password": "123456"}
            ).status_code,
        )
        # Roles untouched
        self.assertEqual(["Guest"], self.roles_of("guest", headers))

    # --- What admins CAN do ---

    def test_admin_can_manage_roles_of_other_users(self):
        headers = self.headers_for("admin")

        response = self.client.post(
            f"/user/{self.user_id('guest')}/role/{self.role_id('User')}",
            headers=headers,
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual(["Guest", "User"], self.roles_of("guest", headers))

        # Takes effect on the next request, without a new token
        guest_headers = self.headers_for("guest")
        response = self.client.post(
            "/permission", headers=guest_headers, json={"name": "x"}
        )
        self.assertEqual(403, response.status_code)  # still needs admin
        response = self.client.put(
            f"/user/{self.user_id('guest')}",
            headers=guest_headers,
            json={"username": "guest2"},
        )
        self.assertEqual(200, response.status_code)

        response = self.client.delete(
            f"/user/{self.user_id('guest')}/role/{self.role_id('User')}",
            headers=headers,
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(["Guest"], self.roles_of("guest", headers))

    def test_admin_can_set_roles_via_user_update(self):
        headers = self.headers_for("admin")

        response = self.client.put(
            f"/user/{self.user_id('guest')}",
            headers=headers,
            json={"roles": [self.role_id("User"), self.role_id("Guest")]},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(["Guest", "User"], self.roles_of("guest", headers))

    def test_admin_can_block_and_unblock_user(self):
        headers = self.headers_for("admin")
        user_headers = self.headers_for("user")

        response = self.client.put(
            f"/block-user/{self.user_id('user')}",
            headers=headers,
            json={"block": True},
        )
        self.assertEqual(200, response.status_code)

        # Existing token is rejected immediately, and login is refused
        response = self.client.get("/user", headers=user_headers)
        self.assertEqual(401, response.status_code)
        self.assertEqual("user_blocked", response.get_json()["error"])

        response = self.client.put(
            f"/block-user/{self.user_id('user')}",
            headers=headers,
            json={"block": False},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            200, self.client.get("/user", headers=user_headers).status_code
        )

    def test_admin_can_create_role_and_permission(self):
        headers = self.headers_for("admin")

        response = self.client.post(
            "/permission",
            headers=headers,
            json={"name": "export", "description": "Export data"},
        )
        self.assertEqual(200, response.status_code, response.get_json())

        response = self.client.post(
            "/role",
            headers=headers,
            json={
                "name": "Exporter",
                "description": "x",
                "permissions": [self.permission_id("read")],
            },
        )
        self.assertEqual(200, response.status_code, response.get_json())

    # --- Lockout guards ---

    def test_admin_cannot_block_self(self):
        headers = self.headers_for("admin")
        response = self.client.put(
            f"/block-user/{self.user_id('admin')}",
            headers=headers,
            json={"block": True},
        )
        self.assertEqual(400, response.status_code)

    def test_admin_cannot_remove_own_admin_access(self):
        headers = self.headers_for("admin")
        admin_id = self.user_id("admin")
        admin_role = self.role_id("Admin")

        # via PUT /user roles
        response = self.client.put(
            f"/user/{admin_id}", headers=headers, json={"roles": [self.role_id("User")]}
        )
        self.assertEqual(400, response.status_code)

        # via DELETE /user/<id>/role/<id>
        response = self.client.delete(
            f"/user/{admin_id}/role/{admin_role}", headers=headers
        )
        self.assertEqual(400, response.status_code)

        # via removing the admin permission from the Admin role
        response = self.client.put(
            f"/role/{admin_role}",
            headers=headers,
            json={
                "name": "Admin",
                "description": "x",
                "permissions": [self.permission_id("read")],
            },
        )
        self.assertEqual(400, response.status_code)

        # via deleting the Admin role
        response = self.client.delete(f"/role/{admin_role}", headers=headers)
        self.assertEqual(400, response.status_code)

        # via detaching the Admin role from the admin permission
        response = self.client.put(
            "/permission-role-update",
            headers=headers,
            json={"data_update": {str(self.permission_id("admin")): []}},
        )
        self.assertEqual(400, response.status_code)

        # via renaming the admin permission
        response = self.client.put(
            f"/permission/{self.permission_id('admin')}",
            headers=headers,
            json={"name": "administrator"},
        )
        self.assertEqual(400, response.status_code)

        # Nothing was persisted: admin still has full access
        self.assertEqual(["Admin"], self.roles_of("admin", headers))
        response = self.client.delete(f"/role/{self.role_id('Guest')}", headers=headers)
        self.assertEqual(200, response.status_code)

    # --- Missing resources return JSON 404s instead of HTML 500s (#7) ---

    def test_unknown_ids_return_404(self):
        headers = self.headers_for("admin")

        for method, url, body in [
            ("put", "/user/999", {"username": "x"}),
            ("put", "/block-user/999", {"block": True}),
            ("post", f"/user/999/role/{self.role_id('User')}", None),
            ("post", f"/user/{self.user_id('user')}/role/999", None),
            ("delete", f"/user/{self.user_id('user')}/role/999", None),
            ("put", "/role/999", {"name": "x", "description": "x", "permissions": []}),
            ("delete", "/role/999", None),
            ("put", "/permission/999", {"name": "x"}),
            (
                "put",
                "/permission-role-update",
                {"data_update": {"999": [self.role_id("User")]}},
            ),
            ("put", f"/user/{self.user_id('user')}", {"roles": [999]}),
        ]:
            response = getattr(self.client, method)(url, headers=headers, json=body)
            self.assertEqual(404, response.status_code, f"{method.upper()} {url}")
            self.assertIn("message", response.get_json(), f"{method.upper()} {url}")

    def test_removing_role_user_does_not_have_is_a_400(self):
        headers = self.headers_for("admin")
        response = self.client.delete(
            f"/user/{self.user_id('guest')}/role/{self.role_id('Admin')}",
            headers=headers,
        )
        self.assertEqual(400, response.status_code)

    # --- Registration ---

    def test_register_assigns_guest_role_by_name(self):
        response = self.client.post(
            "/register", json={"username": "newbie", "password": "secret"}
        )
        self.assertEqual(200, response.status_code, response.get_json())

        headers = self.headers_for("newbie", "secret")
        with self.app.app_context():
            new_id = UserModel.query.filter_by(username="newbie").first().id
        response = self.client.get(f"/user/{new_id}", headers=headers)
        self.assertEqual(["Guest"], [r["name"] for r in response.get_json()["roles"]])

    # --- Upgrade path for existing databases ---

    def test_ensure_admin_permission_upgrades_old_seed_data(self):
        with self.app.app_context():
            # Simulate a database seeded before the admin permission existed
            permission = PermissionModel.query.filter_by(name="admin").first()
            db.session.delete(permission)
            db.session.commit()
            self.assertIsNone(PermissionModel.query.filter_by(name="admin").first())

            manage.create_user_admin()  # admin user exists -> upgrade path

            admin_role = RoleModel.query.filter_by(name="Admin").first()
            self.assertIn("admin", [p.name for p in admin_role.permissions])

        # ...and the admin is functional again
        headers = self.headers_for("admin")
        response = self.client.delete(f"/role/{self.role_id('Guest')}", headers=headers)
        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()

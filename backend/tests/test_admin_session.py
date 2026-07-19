import os
import unittest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import load_env
from app.routers.admin_session import router as admin_session_router
from app.services.admin_auth import verify_admin
from app.services.auth_service import create_access_token


class AdminSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_env = {
            "ADMIN_USERNAME": os.environ.get("ADMIN_USERNAME"),
            "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD"),
            "ADMIN_API_KEY": os.environ.get("ADMIN_API_KEY"),
        }

    def setUp(self):
        load_env.cache_clear()
        os.environ["ADMIN_USERNAME"] = "shadowgarden"
        os.environ["ADMIN_PASSWORD"] = "IloveIT"
        os.environ["ADMIN_API_KEY"] = "unit-test-api-key"
        load_env()

        app = FastAPI()
        app.include_router(admin_session_router)

        @app.get("/protected", dependencies=[Depends(verify_admin)])
        def protected():
            return {"success": True}

        self.client = TestClient(app)

    def tearDown(self):
        load_env.cache_clear()
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_login_requires_username_and_password(self):
        response = self.client.post("/api/admin/session/login", json={"username": "", "password": ""})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Username and password are required")

    def test_login_sets_cookie_and_authorizes_session(self):
        login = self.client.post(
            "/api/admin/session/login",
            json={"username": "shadowgarden", "password": "IloveIT"},
        )

        self.assertEqual(login.status_code, 200)
        self.assertIn("admin_session=", login.headers.get("set-cookie", ""))

        status = self.client.get("/api/admin/session/status")
        protected = self.client.get("/protected")

        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()["data"]["authenticated"])
        self.assertEqual(protected.status_code, 200)

    def test_api_key_still_authorizes_protected_route(self):
        response = self.client.get("/protected", headers={"X-Admin-Key": "unit-test-api-key"})

        self.assertEqual(response.status_code, 200)

    def test_student_jwt_does_not_authenticate_admin_session(self):
        token = create_access_token({"sub": "1", "name": "Student", "is_mentor": True})

        status = self.client.get(
            "/api/admin/session/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        protected = self.client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["data"]["authenticated"])
        self.assertEqual(protected.status_code, 403)

    def test_invalid_admin_cookie_is_rejected(self):
        status = self.client.get(
            "/api/admin/session/status",
            cookies={"admin_session": "forged-session"},
        )
        protected = self.client.get(
            "/protected",
            cookies={"admin_session": "forged-session"},
        )

        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["data"]["authenticated"])
        self.assertEqual(protected.status_code, 403)


if __name__ == "__main__":
    unittest.main()

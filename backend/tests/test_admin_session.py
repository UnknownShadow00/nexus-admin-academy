import os
import unittest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import load_env
from app.routers.admin_session import router as admin_session_router
from app.services.admin_auth import allow_admin_or_student, verify_admin
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

        @app.get("/mixed", dependencies=[Depends(allow_admin_or_student)])
        def mixed():
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

    def test_session_tokens_are_random_per_login(self):
        first = self.client.post(
            "/api/admin/session/login",
            json={"username": "shadowgarden", "password": "IloveIT"},
        )
        self.client.cookies.clear()
        second = self.client.post(
            "/api/admin/session/login",
            json={"username": "shadowgarden", "password": "IloveIT"},
        )

        token1 = first.cookies.get("admin_session")
        token2 = second.cookies.get("admin_session")
        self.assertTrue(token1 and token2)
        self.assertNotEqual(token1, token2)

    def test_logout_revokes_session_server_side(self):
        self.client.post(
            "/api/admin/session/login",
            json={"username": "shadowgarden", "password": "IloveIT"},
        )
        token = self.client.cookies.get("admin_session")
        self.client.post("/api/admin/session/logout")

        # Replay the old cookie after logout — must be rejected server-side
        response = self.client.get("/protected", cookies={"admin_session": token})
        self.assertEqual(response.status_code, 403)

    def test_forged_deterministic_cookie_is_rejected(self):
        from hashlib import sha256

        forged = sha256("IloveIT:nexus-admin-session:v1".encode()).hexdigest()
        response = self.client.get("/protected", cookies={"admin_session": forged})

        self.assertEqual(response.status_code, 403)

    def test_allow_admin_or_student_rejects_garbage_bearer_token(self):
        response = self.client.get("/mixed", headers={"Authorization": "Bearer not-a-real-jwt"})

        self.assertEqual(response.status_code, 401)

    def test_allow_admin_or_student_rejects_missing_auth(self):
        response = self.client.get("/mixed")

        self.assertEqual(response.status_code, 401)

    def test_allow_admin_or_student_accepts_valid_student_jwt(self):
        token = create_access_token({"sub": "1", "name": "Test", "email": "t@test.local", "is_mentor": False})
        response = self.client.get("/mixed", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 200)

    def test_allow_admin_or_student_accepts_admin_session(self):
        self.client.post(
            "/api/admin/session/login",
            json={"username": "shadowgarden", "password": "IloveIT"},
        )
        response = self.client.get("/mixed")

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

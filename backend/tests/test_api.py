from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from app.core.rate_limiter import user_rate_limiter
from app.main import app


class TestFastAPIEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        user_rate_limiter.reset_all()

    def _login(self, email: str, password: str) -> str:
        resp = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return str(resp.json()["access_token"])

    def test_health_endpoints(self) -> None:
        self.assertEqual(self.client.get("/health/live").status_code, 200)
        self.assertEqual(self.client.get("/health/ready").status_code, 200)
        db_resp = self.client.get("/health/db")
        self.assertEqual(db_resp.status_code, 200)
        self.assertEqual(db_resp.json()["status"], "healthy")

    def test_role_segregation_user_vs_admin_and_exports(self) -> None:
        user_token = self._login("empleado@techcorp.latam", "UserPixel2026!")
        admin_token = self._login("admin@techcorp.latam", "AdminPixel2026!")

        # 1. Rol Usuario envía mensaje -> NO debe recibir ningún campo técnico
        u_chat = self.client.post(
            "/api/v1/chat/message",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "session_id": "sess-user-100",
                "message": "¿Cómo solicito reembolso de gastos y viáticos?",
            },
        )
        self.assertEqual(u_chat.status_code, 200)
        u_data = u_chat.json()
        self.assertIn("reply", u_data)
        self.assertNotIn("technical_telemetry", u_data)
        self.assertNotIn("prompt_tokens", u_data)
        self.assertNotIn("estimated_cost_usd", u_data)

        # 2. Rol Usuario intenta acceder a dashboard o exportar auditoría -> HTTP 403 Forbidden
        self.assertEqual(
            self.client.get(
                "/api/v1/admin/dashboard",
                headers={"Authorization": f"Bearer {user_token}"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/admin/export/pdf",
                headers={"Authorization": f"Bearer {user_token}"},
            ).status_code,
            403,
        )

        # 3. Rol Admin envía mensaje -> Recibe technical_telemetry completa con ReAct y hash SHA-256
        a_chat = self.client.post(
            "/api/v1/chat/message",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "session_id": "sess-admin-100",
                "message": "Comparar acciones de MELI, GLOB y MSFT con indicadores técnicos",
                "preferred_tier": "pro",
            },
        )
        self.assertEqual(a_chat.status_code, 200)
        a_data = a_chat.json()
        self.assertIn("technical_telemetry", a_data)
        self.assertEqual(len(a_data["technical_telemetry"]["audit_record_hash"]), 64)

        # 4. Rol Admin consulta Dashboard E6 y descarga CSV + PDF
        dash = self.client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(dash.status_code, 200)
        dash_json = dash.json()
        self.assertIn("cost_analysis_e6", dash_json)
        self.assertEqual(
            len(dash_json["cost_analysis_e6"]["modalities_comparison"]), 3
        )

        csv_resp = self.client.get(
            "/api/v1/admin/export/csv",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("text/csv", csv_resp.headers["content-type"])
        self.assertIn("record_hash", csv_resp.text)

        pdf_resp = self.client.get(
            "/api/v1/admin/export/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp.headers["content-type"], "application/pdf")
        self.assertTrue(pdf_resp.content.startswith(b"%PDF"))

    def test_rate_limiting_10_requests_per_minute(self) -> None:
        user_token = self._login("empleado@techcorp.latam", "UserPixel2026!")

        for i in range(10):
            r = self.client.post(
                "/api/v1/chat/message",
                headers={"Authorization": f"Bearer {user_token}"},
                json={
                    "session_id": "sess-rl-test",
                    "message": f"Consulta de política número {i+1}",
                },
            )
            self.assertEqual(r.status_code, 200)

        # Solicitud #11 en el mismo minuto -> HTTP 429 Too Many Requests
        r_11 = self.client.post(
            "/api/v1/chat/message",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "session_id": "sess-rl-test",
                "message": "Consulta número 11 que excede el límite",
            },
        )
        self.assertEqual(r_11.status_code, 429)
        self.assertIn("Retry-After", r_11.headers)


if __name__ == "__main__":
    unittest.main()

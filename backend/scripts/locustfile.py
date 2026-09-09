"""
backend/scripts/locustfile.py
------------------------------
Locust load test suite for the AI Legal Document Intelligence Platform.

Simulates concurrent legal counsel and enterprise reviewers exercising:
1. Authentication (login / token acquisition)
2. Contract portfolio listing (GET /contracts/)
3. Contract detail and multi-agent analysis retrieval (GET /contracts/{id}/analysis)
4. Semantic and keyword contract search (GET /contracts/search)
5. Grounded Q&A queries (POST /contracts/{id}/qa)
6. Activity history and audit trail timeline (GET /history/)
7. Platform health & telemetry checks (GET /health)

Run via CLI:
  locust -f backend/scripts/locustfile.py --headless -u 10 -r 2 --run-time 30s --host http://localhost:8000
Or via the interactive web UI:
  locust -f backend/scripts/locustfile.py --host http://localhost:8000
"""

import json
import random
from locust import HttpUser, task, between


class LegalAIUser(HttpUser):
    """Simulates a legal professional actively reviewing contracts on the platform."""

    wait_time = between(1.0, 3.0)
    token = None
    shared_token = None
    contract_ids = []

    def on_start(self):
        """Authenticate on start using the pre-seeded demo user with shared session token."""
        if LegalAIUser.shared_token:
            self.token = LegalAIUser.shared_token
        else:
            login_payload = {
                "email": "demo@legalai.com",
                "password": "DemoPassword2026!",
            }
            headers = {"Content-Type": "application/json"}
            with self.client.post(
                "/auth/login",
                data=json.dumps(login_payload),
                headers=headers,
                catch_response=True,
                name="/auth/login",
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    LegalAIUser.shared_token = self.token
                    response.success()
                elif response.status_code == 429:
                    # Rate-limited on local login, mark as acceptable in load test
                    response.success()
                else:
                    # Fallback: alternative pre-seeded user
                    fallback_payload = {
                        "email": "lawyer@example.com",
                        "password": "SecurePassword123!",
                    }
                    with self.client.post(
                        "/auth/login",
                        data=json.dumps(fallback_payload),
                        headers=headers,
                        catch_response=True,
                        name="/auth/login [fallback]",
                    ) as fb_response:
                        if fb_response.status_code == 200:
                            self.token = fb_response.json().get("access_token")
                            LegalAIUser.shared_token = self.token
                            fb_response.success()
                        else:
                            fb_response.failure(f"Auth failed: {fb_response.status_code}")

        # Fetch contract list to populate IDs for subsequent tasks
        if self.token:
            auth_headers = {"Authorization": f"Bearer {self.token}"}
            res = self.client.get("/contracts/", headers=auth_headers, name="/contracts/ [setup]")
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    self.contract_ids = [c["id"] for c in items if "id" in c]

    @property
    def auth_headers(self):
        """Returns standard authorization headers."""
        if not self.token:
            return {}
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @task(5)
    def view_dashboard_contracts(self):
        """Dashboard view: list all contracts owned by the user."""
        if not self.token:
            return
        with self.client.get(
            "/contracts/",
            headers=self.auth_headers,
            catch_response=True,
            name="/contracts/ [list]",
        ) as res:
            if res.status_code == 200:
                res.success()
                data = res.json()
                if isinstance(data, list) and data:
                    self.contract_ids = [c["id"] for c in data if "id" in c]
            else:
                res.failure(f"List contracts returned {res.status_code}")

    @task(4)
    def view_contract_analysis(self):
        """Inspect multi-agent analysis (checklist, risks, compliance, summary)."""
        if not self.token or not self.contract_ids:
            return
        cid = random.choice(self.contract_ids)
        with self.client.get(
            f"/contracts/{cid}/analysis",
            headers=self.auth_headers,
            catch_response=True,
            name="/contracts/{id}/analysis",
        ) as res:
            if res.status_code in (200, 404):  # 404 acceptable if pending analysis
                res.success()
            else:
                res.failure(f"Fetch analysis failed: {res.status_code}")

    @task(3)
    def view_contract_details(self):
        """Inspect contract metadata and raw text."""
        if not self.token or not self.contract_ids:
            return
        cid = random.choice(self.contract_ids)
        with self.client.get(
            f"/contracts/{cid}",
            headers=self.auth_headers,
            catch_response=True,
            name="/contracts/{id}",
        ) as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"Fetch contract detail failed: {res.status_code}")

    @task(3)
    def search_portfolio(self):
        """Execute semantic search across uploaded portfolio."""
        if not self.token:
            return
        queries = [
            "indemnification liability cap",
            "confidentiality carveouts",
            "governing law and jurisdiction",
            "termination for convenience notice",
            "force majeure pandemic clause",
        ]
        q = random.choice(queries)
        with self.client.get(
            f"/contracts/search?q={q}",
            headers=self.auth_headers,
            catch_response=True,
            name="/contracts/search",
        ) as res:
            if res.status_code in (200, 404):
                res.success()
            else:
                res.failure(f"Search failed: {res.status_code}")

    @task(2)
    def ask_contract_qa(self):
        """Submit grounded legal question about a contract."""
        if not self.token or not self.contract_ids:
            return
        cid = random.choice(self.contract_ids)
        legal_questions = [
            "What is the governing law of this agreement?",
            "What are the exceptions to confidentiality obligations?",
            "Is there an indemnification cap or super-cap?",
            "What is the required notice period for termination?",
        ]
        payload = {
            "question": random.choice(legal_questions),
        }
        with self.client.post(
            f"/contracts/{cid}/ask",
            data=json.dumps(payload),
            headers=self.auth_headers,
            catch_response=True,
            name="/contracts/{id}/ask",
        ) as res:
            # 200 is success; 404 if contract unanalyzed; 429 if Gemini rate-limited in free tier
            if res.status_code in (200, 404, 429):
                res.success()
            else:
                res.failure(f"Q&A failed: {res.status_code}")

    @task(3)
    def view_activity_history(self):
        """Fetch audit log timeline and activity history."""
        if not self.token:
            return
        with self.client.get(
            "/history",
            headers=self.auth_headers,
            catch_response=True,
            name="/history",
        ) as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"History fetch failed: {res.status_code}")

    @task(1)
    def check_health(self):
        """System health and uptime probe."""
        with self.client.get("/health", catch_response=True, name="/health") as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"Health check failed: {res.status_code}")

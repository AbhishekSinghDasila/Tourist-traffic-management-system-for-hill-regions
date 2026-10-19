"""Exercise a local Compose stack with disposable accounts and a complaint.

Run after scripts/start.py. This deliberately requires the local Docker project
and cannot target an arbitrary hosted application.
"""
from pathlib import Path
import http.cookiejar
import json
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1"


def operator(service, code):
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", service, "python", "-"],
        input=code, text=True, capture_output=True, check=True, cwd=ROOT,
    )
    return result.stdout.strip()


class Client:
    def __init__(self):
        self.token = None
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )

    def request(self, method, path, data=None, content_type="application/json", expected=200):
        if data is not None and not isinstance(data, bytes):
            data = json.dumps(data).encode()
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=60) as response:
                body = response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        assert status == expected, (method, path, status, body[:400])
        return json.loads(body) if body else None

    def login(self, phone, password):
        result = self.request("POST", "/api/v1/auth/login",
            urllib.parse.urlencode(dict(username=phone, password=password)).encode(),
            "application/x-www-form-urlencoded")
        self.token = result["access_token"]


def main():
    password = "IntegrationA1" + secrets.token_hex(10)
    phone = lambda: "+91" + str(secrets.randbelow(9000000000) + 1000000000)
    admin_phone = phone()
    operator("auth-service", f"""
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
with SessionLocal() as db:
    db.add(User(name="Integration admin", phone={admin_phone!r},
        hashed_password=hash_password({password!r}), role="admin", district="nainital"))
    db.commit()
""")
    admin, citizen, police, tourist = Client(), Client(), Client(), Client()
    admin.login(admin_phone, password)
    actors = {}
    for role, client in (("citizen", citizen), ("police", police), ("tourist", tourist)):
        number = phone()
        actor = admin.request("POST", "/api/v1/auth/users", dict(name="Integration " + role,
            phone=number, password=password, role=role, district="nainital"), expected=201)
        actors[role] = actor
        client.login(number, password)
    citizen.request("GET", "/api/v1/auth/users", expected=403)
    assert len(tourist.request("GET", "/api/v1/traffic/density")["districts"]) == 11

    boundary = "test" + secrets.token_hex(10)
    fields = dict(category="OTHER", description="Integration test report",
                  lat="29.3919", lng="79.4542", district="nainital")
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="test.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode())
    parts.append((ROOT / "test_image.jpg").read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    complaint = citizen.request("POST", "/api/v1/complaints", b"".join(parts),
        "multipart/form-data; boundary=" + boundary, expected=201)
    cid = complaint["id"]
    assert any(c["id"] == cid for c in citizen.request("GET", "/api/v1/complaints/mine"))
    station = police.request("GET", "/api/v1/complaints/station")
    assert any(c["id"] == cid for c in station)
    assert all("user_id" not in c for c in station)
    full = admin.request("GET", f"/api/v1/complaints/{cid}/admin")
    assert full["user_id"] == actors["citizen"]["id"]
    images = admin.request("GET", f"/api/v1/complaints/{cid}/image-url")["images"]
    assert images and images[0].get("url")
    with citizen.opener.open(images[0]["url"], timeout=30) as media:
        assert media.status == 200 and media.read()

    alert = admin.request("POST", "/api/v1/alerts", dict(alert_type="OTHER",
        description="Integration test", lat=29.3919, lng=79.4542, district="nainital"), expected=201)
    assert any(a["id"] == alert["id"] for a in tourist.request("GET", "/api/v1/alerts"))
    admin.request("PATCH", f"/api/v1/alerts/{alert['id']}/cancel", dict(reason="Integration complete"))
    assert not any(a["id"] == alert["id"] for a in tourist.request("GET", "/api/v1/alerts"))
    forecast = tourist.request("GET", "/api/v1/predict/crowd/nainital")
    assert forecast["district"] == "nainital" and forecast["predicted_vehicles"] >= 0
    refreshed = tourist.request("POST", "/api/v1/auth/refresh", {})
    tourist.token = refreshed["access_token"]
    tourist.request("POST", "/api/v1/auth/logout", {}, expected=204)
    tourist.request("GET", "/api/v1/auth/me", expected=401)
    print("PASS: accounts/RBAC, density, complaint upload/privacy/media, alerts, prediction, session revocation.")


if __name__ == "__main__":
    main()

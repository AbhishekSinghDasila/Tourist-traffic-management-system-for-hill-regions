"""Exercise a running auth service. Creates one uniquely named test citizen."""
import argparse
import http.cookiejar
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    args = parser.parse_args()
    handlers = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
    if urllib.parse.urlparse(args.base_url).hostname in ("localhost", "127.0.0.1"):
        handlers.append(urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    phone = "+91" + str(secrets.randbelow(9000000000) + 1000000000)
    password = "SmokeA1" + secrets.token_hex(12)

    def request(path, data=None, token=None, form=False):
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            data = (urllib.parse.urlencode(data) if form else json.dumps(data)).encode()
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(args.base_url + "/api/v1/auth/" + path, data=data, headers=headers)
        try:
            with opener.open(req, timeout=30) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode()

    status, user = request("register", dict(name="Integration Test", phone=phone,
        password=password, role="citizen", district="nainital"))
    assert status == 201, (status, user)
    status, result = request("login", dict(username=phone, password=password), form=True)
    assert status == 200, (status, result)
    token = result["access_token"]
    status, me = request("me", token=token)
    assert status == 200 and me["id"] == user["id"]
    assert request("users", token=token)[0] == 403
    status, refreshed = request("refresh", {})
    assert status == 200, (status, refreshed)
    token = refreshed["access_token"]
    assert request("logout", {}, token)[0] == 204
    assert request("me", token=token)[0] == 401
    assert request("refresh", {})[0] == 401
    print("PASS: register, login, identity, admin denial, refresh, logout, token revocation.")


if __name__ == "__main__":
    main()

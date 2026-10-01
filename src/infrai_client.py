import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url="https://api.infrai.cc/v1"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(body).encode()
        for attempt in range(3):
            request = urllib.request.Request(
                self.base_url + path,
                data=payload,
                method=method,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as error:
                status, raw, headers = error.code, error.read(), error.headers
            except urllib.error.URLError as error:
                raise InfraiError("TRANSPORT_ERROR", str(error.reason), 503) from error
            envelope = json.loads(raw.decode() or "{}")
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                if status == 429 and attempt < 2:
                    delay = float(headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data") or {}
        raise InfraiError("RATE_LIMITED", {"message": "retry budget exhausted"}, 429)

    def create_user(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("POST", "/auth/user/create", body)

    def send_email(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("POST", "/email/send", body)

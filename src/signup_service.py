import json
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from .infrai_client import InfraiClient, InfraiError


@dataclass
class SignupRequest:
    email: str
    password: str
    name: str
    metadata: Dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "SignupRequest":
        for field in ("email", "password", "name"):
            if not isinstance(value.get(field), str) or not value[field].strip():
                raise ValueError(f"{field} is required")
        metadata = value.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        return cls(value["email"], value["password"], value["name"], metadata)


def signup(request: SignupRequest, client: InfraiClient) -> Dict[str, str]:
    key = str(uuid.uuid4())
    user = client.create_user({"email": request.email, "password": request.password, "name": request.name,
                               "metadata": request.metadata, "idempotency_key": key})
    user_id = user.get("user_id") or user.get("id")
    if not user_id:
        raise InfraiError("INVALID_RESPONSE", {"message": "user id missing"}, 502)
    message = client.send_email({"to": request.email, "subject": "Verify your marketplace account",
                                 "body": f"Welcome {request.name}. Verify your account: /verify/{user_id}"})
    return {"user_id": str(user_id), "message_id": str(message.get("message_id", ""))}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/signup":
            self.send_error(404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", "0"))))
            result = signup(SignupRequest.from_dict(body), InfraiClient())
            self._json(201, result)
        except (ValueError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})
        except InfraiError as error:
            self._json(max(400, min(error.status, 599)), {"error": error.code, "detail": error.detail})

    def _json(self, status: int, value: Dict[str, Any]) -> None:
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()

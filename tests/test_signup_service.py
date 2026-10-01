from src.signup_service import SignupRequest, signup


class FakeClient:
    def __init__(self):
        self.calls = []

    def create_user(self, body):
        self.calls.append(("create", body))
        return {"user_id": "u-123"}

    def send_email(self, body):
        self.calls.append(("email", body))
        return {"message_id": "m-456"}


def test_signup_hands_new_buyer_to_verification_email():
    client = FakeClient()
    result = signup(SignupRequest("buyer@example.com", "pw", "Buyer", {"seller_interest": "ceramics"}), client)
    assert result == {"user_id": "u-123", "message_id": "m-456"}
    assert client.calls[0][1]["email"] == client.calls[1][1]["to"] == "buyer@example.com"
    assert client.calls[0][1]["idempotency_key"]

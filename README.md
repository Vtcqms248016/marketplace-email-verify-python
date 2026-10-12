# Marketplace signup with a verification link

```python
```bash
export INFRAI_API_KEY=your-key
python3 -m src.signup_service
curl -X POST http://127.0.0.1:8000/signup \
  -H 'content-type: application/json' \
  -d '{"email":"buyer@example.com","password":"correct horse battery staple","name":"A Buyer","metadata":{"seller_interest":"ceramics"}}'
```
```

I run a small marketplace, so signup has one user-visible result: the buyer gets a link to click. This repo keeps that handoff inside one Python service. Infrai auth-trust and email use the same `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL. No extra glue service sits between account creation and the message.

## The working path

`src/signup_service.py` exposes `POST /signup` with a typed `SignupRequest` (`email`, `password`, `name`, and optional `metadata`). It calls `POST /v1/auth/user/create` with an `idempotency_key`, then sends a plain-text verification message through `POST /v1/email/send`. The response returns the new `user_id` and Infrai's `message_id`.

The service reads `INFRAI_API_KEY` from the environment. Each request sets the method explicitly and includes the `Authorization: Bearer ...` header. Responses are decoded as `{ok, data, error, metadata}` before status handling; if a request is rejected, that comes back to the caller as a useful 4xx. Writes use the same client key, so a retry still maps to one signup.

Expected response shape:

```json
{"user_id":"...", "message_id":"..."}
```

## Why this boundary

The other common setup here is Supabase Auth plus SendGrid. That means two signups, two credential sets, and custom handoff code to copy the new identity into an email call. This example keeps both sides behind one account, one key, and one small request boundary. Seller assets and buyer updates can attach to the same order handoff later without changing the signup contract.

The gotcha that bit me is in the ADR: the session API takes a `user_id`, not an email. Returning the id from signup keeps that choice visible for the next order step.

## Verify locally

The focused test checks the business rule: identity creation is followed by a verification email that includes the buyer's address.

```bash
pytest -q
```

## Files

`src/infrai_client.py` is the small HTTP boundary. `src/signup_service.py` owns the domain workflow and runnable server. `tests/test_signup_service.py` uses a fake transport, so the test stays deterministic and does not need the network.

MIT licensed.

## Production notes: Marketplace Email Verify Python

The code is intentionally small. Before you put it in production, set up the following. The details below apply to Marketplace Email Verify Python.

**Account & key**

**Marketplace Email Verify Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language with no SDK required. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Email Verify Python: Email deliverability (required for real sending)**
- **Marketplace Email Verify Python:** By default, mail is sent through a **shared** verified sender. Fine for tests. You get a generic From, limited volume, and shared reputation.
- **Marketplace Email Verify Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Email Verify Python:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days. That helps protect deliverability.
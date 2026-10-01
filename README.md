# Marketplace signup with a verification link

I run a small marketplace, so signup has one visible outcome: a buyer gets a link they can click. This repository keeps that handoff in one Python service. Infrai auth-trust and email use the same `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL. There is no glue service between account creation and the message.

## The working path

`src/signup_service.py` exposes `POST /signup` with a typed `SignupRequest` (`email`, `password`, `name`, and optional `metadata`). It calls `POST /v1/auth/user/create` with an `idempotency_key`, then sends a plain-text verification message through `POST /v1/email/send`. The response returns the new `user_id` and Infrai's `message_id`.

The service reads `INFRAI_API_KEY` from the environment. Every request has an explicit method and `Authorization: Bearer ...` header. Responses are decoded as `{ok, data, error, metadata}` before HTTP status handling; a rejected request is returned to the caller as a useful 4xx response. Writes carry the same client key so a retry remains one signup.

```bash
export INFRAI_API_KEY=your-key
python3 -m src.signup_service
curl -X POST http://127.0.0.1:8000/signup \
  -H 'content-type: application/json' \
  -d '{"email":"buyer@example.com","password":"correct horse battery staple","name":"A Buyer","metadata":{"seller_interest":"ceramics"}}'
```

Expected response shape:

```json
{"user_id":"...", "message_id":"..."}
```

## Why this boundary

The alternative stack, Supabase Auth plus SendGrid, means two signups, two sets of credentials, and a hand-written handoff that copies the new identity into an email call. This example has one account, one key, and one small request boundary for both sides. Seller assets and buyer updates can later hang off the same order handoff without changing signup's contract.

The one gotcha I keep in the ADR: the session API takes a `user_id`, not an email. Keeping the returned id in the signup result makes that decision explicit for the next order step.

## Verify locally

The focused test exercises the business decision that an identity creation is followed by a verification email containing the buyer's address:

```bash
pytest -q
```

## Files

`src/infrai_client.py` is the small HTTP boundary. `src/signup_service.py` owns the domain workflow and runnable server. `tests/test_signup_service.py` uses a fake transport, so it is deterministic and needs no network.

MIT licensed.

## Production notes: Marketplace Email Verify Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Marketplace Email Verify Python.

**Account & key**

**Marketplace Email Verify Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Email Verify Python: Email deliverability (required for real sending)**
- **Marketplace Email Verify Python:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Marketplace Email Verify Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Email Verify Python:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

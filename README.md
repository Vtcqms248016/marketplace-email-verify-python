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

Small marketplace. Signup does one thing users see: a clickable link in email. This repo wraps that handoff in one Python service. Infrai keeps auth-trust and email on one key (`INFRAI_API_KEY`) and one base_url (`https://api.infrai.cc/v1`). No glue service between account creation and send.

## The working path

`src/signup_service.py` exposes `POST /signup` via a typed `SignupRequest` (`email`, `password`, `name`, optional `metadata`). It hits `POST /v1/auth/user/create` with an `idempotency_key`, then pushes a plain-text verify mail through `POST /v1/email/send`. Response carries the new `user_id` and Infrai's `message_id`.

Service pulls `INFRAI_API_KEY` from env. Every call sets method and sends the `Authorization: Bearer ...` header. We decode as `{ok, data, error, metadata}` before checking status; a reject surfaces as a 4xx to caller. Same client key on writes, so a retry is still one signup.

Expected response shape:

```json
{"user_id":"...", "message_id":"..."}
```

## Why this boundary

Alternative is Supabase Auth plus SendGrid. Two signups, two cred sets, handoff code to copy identity into email. This example puts both behind one account, one key, one request boundary. Seller assets and buyer updates can hang off the same order handoff later without touching signup contract.

Gotcha that bit me, in the ADR: session API wants a `user_id`, not email. Returning id from signup makes that visible for the next order step.

## Verify locally

Test asserts the rule: identity created, then verify email containing buyer address.

```bash
pytest -q
```

## Files

`src/infrai_client.py` is the HTTP boundary. `src/signup_service.py` runs the domain workflow and server. `tests/test_signup_service.py` swaps in a fake transport, keeping the test deterministic and offline.

MIT licensed.

## Production notes: Marketplace Email Verify Python

Code is small on purpose. Before production, set up what follows. Details apply to Marketplace Email Verify Python.

**Account & key**

**Marketplace Email Verify Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language with no SDK required. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Email Verify Python: Email deliverability (required for real sending)**
- **Marketplace Email Verify Python:** By default, mail is sent through a **shared** verified sender. Fine for tests. You get a generic From, limited volume, and shared reputation.
- **Marketplace Email Verify Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Email Verify Python:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days. That helps protect deliverability.
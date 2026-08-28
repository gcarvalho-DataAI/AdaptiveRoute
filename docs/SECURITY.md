# Security Notes

AdaptiveRoute is a proof of concept, but the current implementation includes a minimal security baseline for local evaluation.

## Implemented Baseline

- Driver passwords are stored as bcrypt hashes.
- Legacy driver records that still contain `temporary_password` are migrated to `password_hash` on successful login.
- Driver API responses do not expose `password_hash` or raw temporary passwords.
- Driver login returns a signed JWT instead of a forgeable mock token.
- CORS origins are configurable through `ADAPTIVEROUTE_CORS_ALLOW_ORIGINS` instead of being hardcoded as `*`.

## Relevant Environment Variables

```text
ADAPTIVEROUTE_CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
ADAPTIVEROUTE_JWT_SECRET_KEY=change-this-secret-for-non-local-runs
ADAPTIVEROUTE_JWT_EXPIRES_MINUTES=480
```

For any non-local run, `ADAPTIVEROUTE_JWT_SECRET_KEY` must be replaced with a strong secret provided by a secret manager or deployment environment.

## Current PoC Limitations

- Admin login is still implemented in the frontend for demo convenience.
- Driver JWT is accepted by driver-scoped status/profile endpoints; username/password payloads remain as a compatibility fallback for the PoC.
- There is no password reset flow.
- There is no account lockout/rate limiting.
- There is no HTTPS termination inside the local Compose stack.

## Production Hardening Required

Before production use:

1. Move admin authentication to the backend.
2. Require JWT bearer tokens for all protected endpoints and remove username/password fallback payloads.
3. Add role-based authorization middleware.
4. Remove password fields from routine action payloads after login.
5. Store secrets outside `.env` files.
6. Add rate limiting and audit logs for login attempts.
7. Run behind HTTPS.

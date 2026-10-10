# ADR 0005: SRP sign-in, and an optional second step for owners

Status: Proposed (not built)
Date: 2026-10-10

## Context

- `signIn` in `web/src/api.js` calls `InitiateAuth` with `USER_PASSWORD_AUTH`: the password travels to Cognito inside TLS. Its `ponytail:` comment says to switch to SRP beyond the pilot.
- The browser calls Cognito directly (`cognito()` in the same file). Dhool's backend never sees a password.
- The access and refresh tokens are kept in `localStorage` (`keep("tokens")`, `web/src/store.js`). What stands between a stray script and them is the Content-Security-Policy in `customHttp.yml`, sent only once Amplify hosts the app.
- `template.yaml`: `UserPoolClient` already allows `ALLOW_USER_SRP_AUTH`. `UserPool` asks for 8 characters and sets no MFA.
- An owner's sign-in can delete the home, remove members and link the inverter (`OWNER_ONLY` in `backend/dhool/authz.py`).

## Decision

In this order:

1. A second step, optional, by authenticator app (TOTP) only. `MfaConfiguration: OPTIONAL` with TOTP enabled on `UserPool`. Setup gains "Protect this account": `AssociateSoftwareToken`, the secret shown as text and as an `otpauth://` link (the authenticator is on the same phone, so no QR library), `VerifySoftwareToken`, `SetUserMFAPreference`. `signIn` answers the `SOFTWARE_TOKEN_MFA` challenge with `RespondToAuthChallenge`; today it reads `AuthenticationResult` straight off and would throw on a challenge.
2. SRP: `signIn` uses `USER_SRP_AUTH`. One new file, `web/src/srp.js`, on the browser's `crypto.subtle` and `BigInt`. Cognito checks the proof, so a wrong sum fails to sign in.
3. Remove `ALLOW_USER_PASSWORD_AUTH` from `UserPoolClient`. Until then the pool still takes a raw password from any client.

Unchanged: plain `fetch`, the JWT authorizer, tokens in `localStorage`.

Not chosen: SMS codes (SNS spend, and sender registration in India: to confirm before building) and email codes (Cognito's documentation asks for SES and the Essentials or Plus plan).

## Consequences

- The gain from SRP is small: it hides the password from a proxy that opens TLS, and from nothing else. A stolen password still signs in. The second step is what stops that.
- Worse: an owner who loses the phone is locked out. There is no support desk; the AWS account owner resets them by hand.
- Worse: more sign-in code, and every new line needs its Hindi (`npm test` fails without it).
- It must stay optional: the showcase accounts share one password for judges.
- New: `UserPool` is `Retain` with deletion protection. A property change that replaces the pool strands every account. Whether `MfaConfiguration` updates in place: to confirm before building.

## What would make us do it

- The first real inverter credential behind an account (ADR 0003), homes outside the pilot, or one account reported taken over.
- Owner-only: resetting a locked-out owner.

## Open questions

- Hand-written SRP, or `amazon-cognito-identity-js`? It would be the first runtime dependency after React (`web/package.json`), needs a credit, and its size in the bundle is not measured.
- The refresh token's lifetime: the client sets none, so Cognito's default applies (value to confirm before building).
- Which Cognito feature plan the pool is on, and whether TOTP is in it (to confirm before building).

// Sign-in (Cognito, plain fetch, no SDK) and calls to the Dhool API.
import { API_URL, CLIENT_ID, REGION } from "./config.js";
import { forget, keep, kept } from "./store.js";

const tokens = () => kept("tokens");
const OFFLINE = "No connection. Check your internet and try again.";

async function cognito(target, body) {
  const response = await fetch(`https://cognito-idp.${REGION}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  }).catch(() => { throw new Error(OFFLINE); });
  const data = await response.json();
  if (!response.ok) throw Object.assign(new Error(data.message || "Sign-in failed"), { code: data.__type });
  return data;
}

export const signedIn = () => Boolean(tokens());
export const signOut = forget;

// ponytail: sends the password over TLS (USER_PASSWORD_AUTH). Switch to SRP if this ships beyond the pilot.
export async function signIn(email, password) {
  const { AuthenticationResult: r } = await cognito("InitiateAuth", {
    ClientId: CLIENT_ID,
    AuthFlow: "USER_PASSWORD_AUTH",
    AuthParameters: { USERNAME: email, PASSWORD: password },
  });
  keep("tokens", { access: r.AccessToken, refresh: r.RefreshToken });
}

export const signUp = (email, password) =>
  cognito("SignUp", { ClientId: CLIENT_ID, Username: email, Password: password, UserAttributes: [{ Name: "email", Value: email }] });

export const confirmSignUp = (email, code) => cognito("ConfirmSignUp", { ClientId: CLIENT_ID, Username: email, ConfirmationCode: code });

async function refresh() {
  const { AuthenticationResult: r } = await cognito("InitiateAuth", {
    ClientId: CLIENT_ID,
    AuthFlow: "REFRESH_TOKEN_AUTH",
    AuthParameters: { REFRESH_TOKEN: tokens().refresh },
  });
  keep("tokens", { ...tokens(), access: r.AccessToken });
}

/** Who is signed in, as the API knows them: the `sub` inside the access token. */
export const mySub = () => JSON.parse(atob(tokens().access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).sub;

/** Removes the sign-in itself, for good. The homes are left or deleted first (see DeleteAccount). */
export async function deleteAccount() {
  await refresh();  // Cognito wants a token that has not run out
  await cognito("DeleteUser", { AccessToken: tokens().access });
}

/** `method` is POST with a body and GET without, unless given (DELETE, with or without a body). */
export async function api(path, body, method = body ? "POST" : "GET", retried = false) {
  const response = await fetch(API_URL + path, {
    method,
    headers: { Authorization: `Bearer ${tokens()?.access}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  }).catch(() => { throw Object.assign(new Error(OFFLINE), { offline: true }); });
  if (response.status === 401 && !retried) {
    try {
      await refresh();
    } catch {
      signOut();
      throw Object.assign(new Error("Please sign in again"), { signedOut: true });
    }
    return api(path, body, method, true);
  }
  const data = await response.json().catch(() => ({}));  // a DELETE may answer with nothing
  if (!response.ok) throw new Error(data.error || data.message || "Something went wrong. Try again.");
  return data;
}

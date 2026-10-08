// Sign-in (Cognito, plain fetch, no SDK) and calls to the Dhool API.
import { API_URL, CLIENT_ID, REGION } from "./config.js";

const KEY = "dhool.tokens";
const tokens = () => JSON.parse(localStorage.getItem(KEY) || "null");

async function cognito(target, body) {
  const response = await fetch(`https://cognito-idp.${REGION}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify({ ClientId: CLIENT_ID, ...body }),
  });
  const data = await response.json();
  if (!response.ok) throw Object.assign(new Error(data.message || "Sign-in failed"), { code: data.__type });
  return data;
}

export const signedIn = () => Boolean(tokens());
export const signOut = () => localStorage.removeItem(KEY);

// ponytail: sends the password over TLS (USER_PASSWORD_AUTH). Switch to SRP if this ships beyond the pilot.
export async function signIn(email, password) {
  const { AuthenticationResult: r } = await cognito("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    AuthParameters: { USERNAME: email, PASSWORD: password },
  });
  localStorage.setItem(KEY, JSON.stringify({ access: r.AccessToken, refresh: r.RefreshToken }));
}

export const signUp = (email, password) =>
  cognito("SignUp", { Username: email, Password: password, UserAttributes: [{ Name: "email", Value: email }] });

export const confirmSignUp = (email, code) => cognito("ConfirmSignUp", { Username: email, ConfirmationCode: code });

async function refresh() {
  const { AuthenticationResult: r } = await cognito("InitiateAuth", {
    AuthFlow: "REFRESH_TOKEN_AUTH",
    AuthParameters: { REFRESH_TOKEN: tokens().refresh },
  });
  localStorage.setItem(KEY, JSON.stringify({ ...tokens(), access: r.AccessToken }));
}

export async function api(path, body, retried = false) {
  const response = await fetch(API_URL + path, {
    method: body ? "POST" : "GET",
    headers: { Authorization: `Bearer ${tokens()?.access}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 401 && !retried) {
    try {
      await refresh();
    } catch {
      signOut();
      throw Object.assign(new Error("Please sign in again"), { signedOut: true });
    }
    return api(path, body, true);
  }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.message || "Something went wrong. Try again.");
  return data;
}

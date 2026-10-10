// Public identifiers of the deployed backend (stack `dhool-aws`, see template.yaml outputs). Not secrets.
export const API_URL = "https://fmq7cl7jqb.execute-api.ap-south-1.amazonaws.com";
export const REGION = "ap-south-1";
export const CLIENT_ID = "70vho6ocgpfg2atjag4ftg01vd";
export const TARIFF_RS = 7;  // for verdicts stored before each one carried its home's tariff
// The public half of the Web Push key pair. Empty until the lead fills it in: the alerts switch stays hidden.
export const VAPID_PUBLIC_KEY = "";

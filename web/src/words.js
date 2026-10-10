// What the homeowner should do, in their words. The API's verdict, cause and reason for waiting pick the line.
import { t } from "./i18n.js";

const HEADLINE = {
  "INSPECT:outage": t("Your solar has stopped"),
  "INSPECT:fault": t("Call your vendor"),
  "INSPECT:trips": t("Call your vendor"),
  "INSPECT:not_dust": t("Call your vendor"),
  "CLEAN:dust": t("Wash the panels"),
  "WAIT:dust": t("Wait for the rain"),
  "WAIT:dust:dust_storm": t("Wash after the dust storm"),
  "WAIT:dust:not_worth_it": t("Not worth washing yet"),
  "WAIT:haze": t("Don't wash. It's haze."),
  "WAIT:unclear": t("Wait and watch"),
  "WAIT:no_data": t("Still learning your roof"),
  "OK:ok": t("Your solar is working"),
};

/** `said` is a verdict, or a line of the log: { verdict, cause, wait_for } or { verdict, cause, evidence }. */
export const headline = (said) =>
  HEADLINE[`${said.verdict}:${said.cause}:${said.wait_for ?? said.evidence?.wait_for}`] || HEADLINE[`${said.verdict}:${said.cause}`] || said.verdict;

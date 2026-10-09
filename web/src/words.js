// What the homeowner should do, in their words. The API's verdict, cause and reason for waiting pick the line.
const HEADLINE = {
  "INSPECT:fault": "Call your vendor",
  "INSPECT:trips": "Call your vendor",
  "INSPECT:not_dust": "Call your vendor",
  "CLEAN:dust": "Wash the panels",
  "WAIT:dust": "Wait for the rain",
  "WAIT:dust:dust_storm": "Wash after the dust storm",
  "WAIT:dust:not_worth_it": "Not worth washing yet",
  "WAIT:haze": "Don't wash. It's haze.",
  "WAIT:unclear": "Wait and watch",
  "WAIT:no_data": "Still learning your roof",
  "OK:ok": "Your solar is working",
};

/** `said` is a verdict, or a line of the log: { verdict, cause, wait_for } or { verdict, cause, evidence }. */
export const headline = (said) =>
  HEADLINE[`${said.verdict}:${said.cause}:${said.wait_for ?? said.evidence?.wait_for}`] || HEADLINE[`${said.verdict}:${said.cause}`] || said.verdict;

"""Make the showcase accounts and their homes on a deployed stack, and wait for each home's first verdict.

    SHOWCASE_PASSWORD=... .venv/bin/python scripts/seed-demo.py wash@example.com vendor@example.com fine@example.com

Three emails, in this order: the home that should say "wash" (demo plant home-30), "call the vendor" (home-01)
and "all good" (home-05). The password is read from the environment and never printed. Safe to run again: an
account that exists keeps its homes, and a home is only added to an account that has none.
Needs AWS credentials for the account (it creates the users as an administrator, so no inbox is involved).
"""

import json
import os
import sys
import time
import urllib.request

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from handlers.mock_inverter import api_key  # noqa: E402  (the demo inverter's key for a plant: not a secret)

STACK, REGION = os.environ.get("STACK", "dhool-aws"), os.environ.get("AWS_REGION", "ap-south-1")
HOMES = [("Sharma house", "home-30", "CLEAN"), ("Verma house", "home-01", "INSPECT"), ("Iyer house", "home-05", "OK")]


def call(api, token, path, body=None):
    request = urllib.request.Request(
        api + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main(emails):
    password = os.environ.get("SHOWCASE_PASSWORD")
    if len(emails) != len(HOMES) or not password:
        sys.exit(__doc__)
    outputs = boto3.client("cloudformation", region_name=REGION).describe_stacks(StackName=STACK)["Stacks"][0][
        "Outputs"
    ]
    out = {o["OutputKey"]: o["OutputValue"] for o in outputs}
    cognito = boto3.client("cognito-idp", region_name=REGION)
    for email, (name, plant, expected) in zip(emails, HOMES, strict=True):
        try:
            cognito.admin_create_user(
                UserPoolId=out["UserPoolId"],
                Username=email,
                MessageAction="SUPPRESS",
                UserAttributes=[{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}],
            )
        except cognito.exceptions.UsernameExistsException:
            pass
        cognito.admin_set_user_password(UserPoolId=out["UserPoolId"], Username=email, Password=password, Permanent=True)
        token = cognito.initiate_auth(
            ClientId=out["UserPoolClientId"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )["AuthenticationResult"]["AccessToken"]
        houses = call(out["ApiUrl"], token, "/me")["houses"]
        if houses:
            house = houses[0]["house_id"]
        else:  # the inverter link replaces size and place with the plant's own, so these are placeholders
            house = call(out["ApiUrl"], token, "/houses", {"name": name, "kw": 3, "lat": 28.61, "lon": 77.21})[
                "house_id"
            ]
            call(out["ApiUrl"], token, f"/houses/{house}/inverter", {"api_key": api_key(plant)})
        verdict = {}
        for _ in range(30):  # the analysis runs in the background: a first run takes about 20 seconds
            verdict = call(out["ApiUrl"], token, f"/houses/{house}/verdict")
            if verdict.get("verdict"):
                break
            time.sleep(5)
        said = f"{verdict.get('verdict')} ({verdict.get('cause')}), as of {verdict.get('as_of')}"
        print(f"{email}: {name} on {plant}: {said}; expected {expected}")


if __name__ == "__main__":
    main(sys.argv[1:])

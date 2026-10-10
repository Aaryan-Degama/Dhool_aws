"""The table's keys, written once. Pure: strings in, strings out.

One table. Everything a home owns shares the partition HOUSE#<id>, told apart by the sort key:
META, MEMBER#<sub>, READING#<date>, VERDICT#<date>, ACTION#<date>, SHOT#<id>, PUSH#<hash>, INVITE#<code>,
FEEDBACK#<date>. What has to be found without knowing the home has a partition of its own: USER#<sub>
(sort key HOUSE#<id>, one per home the person is in), INVITE#<code>, JOINFAIL#<sub>, WXCACHE#<hash>, and
HOUSES (sort key <id>), the list the nightly run walks.
"""
import datetime

HOUSES = "HOUSES"
META = "META"
# Sort-key prefixes, for begins_with and startswith.
HOUSE, MEMBER, READING, VERDICT, ACTION, SHOT, PUSH, INVITE, FEEDBACK = (
    "HOUSE#", "MEMBER#", "READING#", "VERDICT#", "ACTION#", "SHOT#", "PUSH#", "INVITE#", "FEEDBACK#")


def house_pk(house_id: str) -> str:
    """A home's partition. Also the sort key of a person's membership under USER#<sub>."""
    return HOUSE + str(house_id)


def user_pk(sub: str) -> str:
    return f"USER#{sub}"


def invite_pk(code: str) -> str:
    """A family code's own partition. Also the sort key of the home's note of that code."""
    return f"INVITE#{code}"


def joinfail_pk(sub: str) -> str:
    return f"JOINFAIL#{sub}"


def wxcache_pk(digest: str) -> str:
    return f"WXCACHE#{digest}"


def member_sk(sub: str) -> str:
    return MEMBER + str(sub)


def reading_sk(date: datetime.date | str) -> str:
    return READING + str(date)


def verdict_sk(date: datetime.date | str) -> str:
    return VERDICT + str(date)


def action_sk(date: datetime.date | str) -> str:
    return ACTION + str(date)


def shot_sk(shot_id: str) -> str:
    return SHOT + str(shot_id)


def push_sk(digest: str) -> str:
    return PUSH + str(digest)


def feedback_sk(date: datetime.date | str) -> str:
    return FEEDBACK + str(date)


def tail(key: str) -> str:
    """What follows the prefix: the sub in MEMBER#<sub>, the date in READING#<date>, the id in HOUSE#<id>."""
    return key.split("#", 1)[1]

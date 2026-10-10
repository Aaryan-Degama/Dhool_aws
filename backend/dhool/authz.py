"""Who may do what in a house. Pure: the caller's role is looked up by the handler."""

OWNER_ONLY = {"create_invite", "remove_member", "connect_inverter", "disconnect_inverter", "delete_house"}


def decide(role: str | None, action: str) -> bool:
    """role is "owner", "member" or None (not in the house)."""
    if role not in ("owner", "member"):
        return False
    return role == "owner" or action not in OWNER_ONLY

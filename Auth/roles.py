"""Multi-role support for logins.

A person can hold more than one role at once — an HR lead who is also a portal
admin, for instance. The full set lives in `users.roles` as a comma-separated
string, while `users.role` keeps the single highest-privilege value so the
permission checks written against it keep working unchanged.
"""

# Most privileged first — this ordering decides the effective `role`.
ROLE_PRIORITY = ["admin", "hr", "manager", "employee"]
VALID_ROLES = set(ROLE_PRIORITY)


def normalise(names) -> list[str]:
    """Clean, de-duplicate and order a role collection. Unknown names drop out."""
    if isinstance(names, str):
        names = names.split(",")
    seen = []
    for n in names or []:
        n = (n or "").strip().lower()
        if n in VALID_ROLES and n not in seen:
            seen.append(n)
    return sorted(seen, key=ROLE_PRIORITY.index)


def get_roles(user) -> list[str]:
    """Every role held. Falls back to the single `role` column for logins that
    predate multi-role, so nobody loses access on upgrade."""
    stored = normalise(getattr(user, "roles", None))
    if stored:
        return stored
    single = normalise([getattr(user, "role", None)])
    return single or ["employee"]


def primary_role(names) -> str:
    """The highest-privilege role in the set — what `users.role` should hold."""
    ordered = normalise(names)
    return ordered[0] if ordered else "employee"


def has_role(user, *names) -> bool:
    """True when the user holds any of the given roles."""
    held = set(get_roles(user))
    return any((n or "").strip().lower() in held for n in names)


def set_roles(user, names) -> list[str]:
    """Assign the full set, keeping `role` in step. Always leaves at least one."""
    ordered = normalise(names) or ["employee"]
    user.roles = ",".join(ordered)
    user.role = ordered[0]
    return ordered

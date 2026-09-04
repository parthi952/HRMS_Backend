"""Multi-role and dynamic access control support.

Roles:
- admin: System Administrator (Full unrestricted access, unmasked salaries, portal management)
- hr: Human Resources (Core HR, Employee Directory, Onboarding, Offboarding, Celebrations, Payroll)
- developer: Developer / Tech Support (Full access to all sections for testing, sensitive salary/bank data masked by default)
- recruiter: Recruiter / Talent Acquisition (Recruitment Hub: Candidates, Interviews, Job Postings, Requirements, Offers)
- manager: Team Manager (Team attendance, leave approvals, events)
- employee: Self-Service Employee (My Space: Profile, My Attendance, My Leaves, My Payslips)
"""

ROLE_PRIORITY = ["admin", "hr", "developer", "recruiter", "manager", "employee"]
VALID_ROLES = set(ROLE_PRIORITY)

DEFAULT_ROLE_MODULES = {
    "admin": ["*"],
    "hr": ["employee_management", "payroll", "recruitment", "celebrations", "attendance_leave", "organization", "offboarding"],
    "developer": ["*"],
    "recruiter": ["recruitment", "celebrations"],
    "manager": ["attendance_leave", "celebrations"],
    "employee": ["self_service"],
}


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
    """Every role held. Falls back to the single `role` column."""
    stored = normalise(getattr(user, "roles", None))
    if stored:
        return stored
    single = normalise([getattr(user, "role", None)])
    return single or ["employee"]


def primary_role(names) -> str:
    """The highest-privilege role in the set."""
    ordered = normalise(names)
    return ordered[0] if ordered else "employee"


def has_role(user, *names) -> bool:
    """True when the user holds any of the given roles."""
    held = set(get_roles(user))
    return any((n or "").strip().lower() in held for n in names)


def set_roles(user, names) -> list[str]:
    """Assign the full set, keeping `role` in step."""
    ordered = normalise(names) or ["employee"]
    user.roles = ",".join(ordered)
    user.role = ordered[0]
    return ordered


def can_view_salary(user) -> bool:
    """True if user is permitted to view unmasked salary / CTC figures.
    
    Admins always have access.
    HR has access by default unless explicitly disabled.
    Developer, Recruiter, Employee, Manager have masked access by default,
    unless explicitly granted `can_view_salary = True` by an Admin in Portal Access.
    """
    if not user:
        return False
    
    # 1. Admin always has full view
    if has_role(user, "admin"):
        return True
        
    # 2. Check explicit database toggle if set
    explicit = getattr(user, "can_view_salary", None)
    if explicit is True or explicit == 1:
        return True
    if explicit is False or explicit == 0:
        # If explicitly set to False, respect it even for HR
        if has_role(user, "hr") and explicit is False:
            return False
        if not has_role(user, "hr"):
            return False

    # 3. Default for HR is True, for others False
    if has_role(user, "hr"):
        return True

    return False


def get_allowed_modules(user) -> list[str]:
    """Get list of module identifiers user can access."""
    if not user:
        return []
    
    # 1. Check custom allowed_modules from database
    custom = getattr(user, "allowed_modules", None)
    if custom:
        try:
            if isinstance(custom, str) and (custom.startswith("[") or custom.startswith("{")):
                import json
                return json.loads(custom)
            elif isinstance(custom, str):
                return [m.strip() for m in custom.split(",") if m.strip()]
        except Exception:
            pass

    # 2. Derive defaults from roles
    roles = get_roles(user)
    if "admin" in roles or "developer" in roles:
        return ["*"]

    modules = set()
    for r in roles:
        for m in DEFAULT_ROLE_MODULES.get(r, []):
            modules.add(m)
    return list(modules)


def has_module_access(user, module: str) -> bool:
    """True if user has access to specified module."""
    if not user:
        return False
    modules = get_allowed_modules(user)
    if "*" in modules:
        return True
    return module in modules


def mask_numeric(val):
    """Return 0.0 for masked numeric amounts."""
    return 0.0


def mask_string(val, keep_last=4, mask_char="•"):
    """Mask string showing only last N characters."""
    if not val:
        return val
    s = str(val).strip()
    if len(s) <= keep_last:
        return mask_char * len(s)
    return f"{mask_char * (len(s) - keep_last)} {s[-keep_last:]}"

import re
import secrets
import string
from datetime import date
from typing import Optional, Union


def generate_password(
    name: Optional[str] = None,
    dob: Optional[Union[date, str]] = None,
    length: int = 12
) -> str:
    """
    Generates a secure password. 
    If name and DOB are provided, it derives the password from them:
      e.g. First4LettersOfName(Capitalized) + DDMM + @ + random secure suffix (upper + digit + special).
    Otherwise, it generates a fully random secure password.
    """
    if name:
        # Extract first word and clean non-alphabetic chars
        clean_name = re.sub(r'[^a-zA-Z]', '', name)
        if not clean_name:
            clean_name = "User"
        
        name_prefix = clean_name.split()[0][:4].capitalize()
        
        dob_suffix = ""
        if dob:
            if isinstance(dob, date):
                dob_suffix = dob.strftime("%d%m")
            elif isinstance(dob, str):
                # Try format YYYY-MM-DD
                match = re.search(r'(\d{4})-(\d{2})-(\d{2})', dob)
                if match:
                    dob_suffix = f"{match.group(3)}{match.group(2)}"
                else:
                    # Try format DD-MM-YYYY
                    match2 = re.search(r'(\d{2})-(\d{2})-(\d{4})', dob)
                    if match2:
                        dob_suffix = f"{match2.group(1)}{match2.group(2)}"
                    else:
                        digits = re.sub(r'\D', '', dob)
                        if len(digits) >= 4:
                            dob_suffix = digits[:4]
                            
        if not dob_suffix:
            # Fallback to 4 random digits if DOB is missing
            dob_suffix = "".join(secrets.choice(string.digits) for _ in range(4))
            
        # Secure random suffix to satisfy complex password policy (at least 1 upper, 1 digit, 1 special)
        uppercase   = string.ascii_uppercase
        digits      = string.digits
        special     = "!@#$%^&*"
        
        suffix = [
            secrets.choice(special),
            secrets.choice(uppercase),
            secrets.choice(digits),
        ]
        secrets.SystemRandom().shuffle(suffix)
        suffix_str = "".join(suffix)
        
        return f"{name_prefix}{dob_suffix}@{suffix_str}"
        
    else:
        # Fallback to fully random password if name is not provided
        uppercase   = string.ascii_uppercase
        lowercase   = string.ascii_lowercase
        digits      = string.digits
        special     = "!@#$%^&*"

        guaranteed = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        all_chars = uppercase + lowercase + digits + special
        rest = [secrets.choice(all_chars) for _ in range(length - len(guaranteed))]

        password_list = guaranteed + rest
        secrets.SystemRandom().shuffle(password_list)

        return "".join(password_list)

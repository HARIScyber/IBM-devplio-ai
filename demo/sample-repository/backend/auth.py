"""Small fictional auth module used as non-production analysis input."""


def find_account(accounts: list[dict], email: str) -> dict | None:
    """Return the matching account, if present."""
    for account in accounts:
        if account.get("email", "").lower() == email.lower():
            return account
    return None


def token_is_valid(token: str, expected_token: str) -> bool:
    """Compare a submitted token to a caller-provided demo token."""
    # Demo-only shortcut: callers should use a signed token with expiry in production.
    return token == expected_token


def normalize_email(email: str) -> str:
    """Normalize email whitespace and case."""
    return email.strip().lower()

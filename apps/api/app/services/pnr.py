import secrets


def generate_pnr() -> str:
    """A random 10-digit PNR that does not start with 0 and cannot be guessed from others."""
    return str(1_000_000_000 + secrets.randbelow(9_000_000_000))


def mask_name(name: str) -> str:
    """Keep the first two letters of each word: 'Rahul Sharma' -> 'Ra*** Sh****'."""
    return " ".join(word[:2] + "*" * max(len(word) - 2, 0) for word in name.split())

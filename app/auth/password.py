import hashlib
import os

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        if ":" in stored:
            _salt, _pwd_hash = stored.split(":", 1)
            return hashlib.sha256(f"{_salt}{password}".encode()).hexdigest() == _pwd_hash
        return bcrypt.checkpw(password.encode(), stored.encode())
    except Exception:
        return False

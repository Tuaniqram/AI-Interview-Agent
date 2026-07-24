import hashlib
import os


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def verify_password(password: str, stored: str) -> bool:
    salt, pwd_hash = stored.split(":")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == pwd_hash

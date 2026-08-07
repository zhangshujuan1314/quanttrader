import hashlib

from app.domain.user.auth import hash_password, password_needs_rehash, verify_password


def _legacy_hash(password: str, salt: str = "0123456789abcdef" * 4) -> str:
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${digest}"


def test_new_passwords_use_bcrypt_and_verify():
    hashed = hash_password("correct horse battery staple")

    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)
    assert not password_needs_rehash(hashed)


def test_legacy_sha256_hashes_remain_compatible_for_migration():
    hashed = _legacy_hash("legacy-password")

    assert verify_password("legacy-password", hashed)
    assert not verify_password("wrong password", hashed)
    assert password_needs_rehash(hashed)


def test_malformed_hash_is_rejected():
    assert not verify_password("anything", "not-a-valid-hash")
    assert password_needs_rehash("not-a-valid-hash")

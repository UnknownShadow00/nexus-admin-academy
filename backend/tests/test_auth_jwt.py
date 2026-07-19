from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.services.auth_service import create_access_token, decode_token


def test_valid_token_round_trip():
    token = create_access_token({"sub": "42", "name": "Student"})

    payload = decode_token(token)

    assert payload["sub"] == "42"
    assert payload["name"] == "Student"


def test_expired_token_is_rejected():
    token = create_access_token({"sub": "42"}, expires_delta=timedelta(seconds=-1))

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == 401


def test_token_with_invalid_signature_is_rejected():
    token = jwt.encode({"sub": "42", "exp": 4102444800}, "wrong-secret", algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == 401


@pytest.mark.parametrize("token", ["not-a-token", "one.two", ""])
def test_malformed_token_is_rejected(token):
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == 401


def test_unsigned_token_is_rejected():
    token = jwt.encode({"sub": "42", "exp": 4102444800}, key="", algorithm="none")

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == 401

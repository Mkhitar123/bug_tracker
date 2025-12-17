import auth

import sys
sys.path.insert(0, '/app')

verify_password = auth.verify_password
get_password_hash = auth.get_password_hash
create_access_token = auth.create_access_token


def test_auth_import():
    assert verify_password is not None
    assert get_password_hash is not None


def test_password_hashing():
    password = "test123"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) == True
    assert verify_password("wrong", hashed) == False


def test_token_creation():
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
import secrets

def generate_var_token(length) -> str:
    return secrets.token_urlsafe(length)
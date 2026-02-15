import bcrypt

def hash_password(password: str):
    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt(),
    )
    return hashed_password.decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    # result = bcrypt.checkpw(
    #     b"12345678",
    #     b"$2b$12$7dtnaDwXJgsUZj4JDrJp/eYrgm5utJgbqdsCdNT7qfKDldY406jY."
    # )
    #
    # print("MANUAL CHECK:", result)

    return bcrypt.checkpw(
        password.encode('utf-8'),
        password_hash.encode('utf-8'),
    )





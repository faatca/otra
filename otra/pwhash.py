import bcrypt


def generate(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def check(hashed, password):
    return bcrypt.hashpw(password.encode('utf-8'),
                         hashed.encode('utf-8')) == hashed

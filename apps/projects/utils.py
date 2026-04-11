import secrets

def generate_unique_id(prefix, model):
    while True:
        uid = f"{prefix}{secrets.randbelow(900000) + 100000}"
        if not model.objects.filter(uid=uid).exists():
            return uid
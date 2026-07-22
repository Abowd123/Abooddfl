from cryptography.fernet import Fernet, InvalidToken
class TokenVault:
    def __init__(self, key: str): self.fernet=Fernet(key.encode())
    def encrypt(self, token: str) -> bytes: return self.fernet.encrypt(token.encode())
    def decrypt(self, value: bytes) -> str:
        try: return self.fernet.decrypt(value).decode()
        except InvalidToken as exc: raise ValueError("تعذر فك تشفير الرمز") from exc

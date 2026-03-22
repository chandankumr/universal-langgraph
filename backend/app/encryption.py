from cryptography.fernet import Fernet
from app.config import settings
import base64
import hashlib

class EncryptionService:
    def __init__(self):
        # Generate deterministic key from SECRET_KEY
        key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(key)
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt API key before storing in database."""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt API key for use."""
        return self.cipher.decrypt(ciphertext.encode()).decode()

encryption_service = EncryptionService()
import os
import tempfile
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Test signing keys are ephemeral and never depend on operator credentials.
directory = tempfile.TemporaryDirectory()
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
private = Path(directory.name) / "private.pem"
public = Path(directory.name) / "public.pem"
private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
public.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo))
os.environ["JWT_PRIVATE_KEY_PATH"] = str(private)
os.environ["JWT_PUBLIC_KEY_PATH"] = str(public)
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


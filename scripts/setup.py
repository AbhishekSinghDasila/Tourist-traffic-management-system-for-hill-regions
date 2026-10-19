"""Generate local configuration without overwriting existing credentials.

Run: python -m pip install cryptography; python scripts/setup.py
"""
from pathlib import Path
import secrets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = ROOT / ".env"
    if not env.exists():
        text = (ROOT / ".env.example").read_text()
        for name in ("strong", "auth", "traffic", "complaint", "alert", "minio"):
            text = text.replace(f"change_me_{name}_password", secrets.token_hex(24))
        env.write_text(text)
    directory = ROOT / "secrets"
    directory.mkdir(exist_ok=True)
    private = directory / "jwt_private_key.pem"
    public = directory / "jwt_public_key.pem"
    if private.exists() != public.exists():
        raise SystemExit("Incomplete signing key pair; restore the missing key before continuing.")
    if not private.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        private.chmod(0o600)
        public.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
    print("Configuration ready. Existing secrets were preserved.")


if __name__ == "__main__":
    main()

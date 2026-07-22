#!/bin/bash
# Generates an RS256 keypair for JWT signing.
# Run once during initial setup. Output goes to ./secrets/ (gitignored).
set -e

mkdir -p secrets

if [ -f "secrets/jwt_private_key.pem" ]; then
  echo "Keys already exist at secrets/. Delete them first if you want to regenerate."
  exit 1
fi

openssl genrsa -out secrets/jwt_private_key.pem 2048
openssl rsa -in secrets/jwt_private_key.pem -pubout -out secrets/jwt_public_key.pem

chmod 600 secrets/jwt_private_key.pem
chmod 644 secrets/jwt_public_key.pem

echo "Generated:"
echo "  secrets/jwt_private_key.pem  (keep secret, used by auth-service only)"
echo "  secrets/jwt_public_key.pem   (can be shared with other services for verification)"
echo ""
echo "Add 'secrets/' to .gitignore if not already present."

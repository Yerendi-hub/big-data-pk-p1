#!/usr/bin/env bash
# Generates a local Certificate Authority and a server certificate for MongoDB.
set -euo pipefail
cd "$(dirname "$0")"

# 1. Certificate Authority (CA): our own "trusted issuer"
openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
  -keyout ca.key -out ca.pem -subj "/CN=Lichess Project Local CA"

# 2. Server private key + certificate signing request
openssl req -newkey rsa:4096 -nodes \
  -keyout server.key -out server.csr -subj "/CN=localhost"

# 3. CA signs the server certificate; SAN lists names clients may connect to
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
  -days 365 -out server.crt \
  -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1")

# 4. MongoDB expects the private key and the certificate in one file
cat server.key server.crt > server.pem
rm server.csr

# mongod runs as a different user inside the container, so it must be able to read the file
chmod 644 server.pem ca.pem
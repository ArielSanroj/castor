#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, use Let's Encrypt or a real CA

set -e

SSL_DIR="$(dirname "$0")/../ssl"
mkdir -p "$SSL_DIR"

# Certificate details
COUNTRY="CO"
STATE="Bogota"
CITY="Bogota"
ORG="CASTOR"
OU="Development"
CN="localhost"
DAYS=365

echo "Generating SSL certificates for CASTOR..."

# Generate private key
openssl genrsa -out "$SSL_DIR/server.key" 2048

# Generate certificate signing request
openssl req -new -key "$SSL_DIR/server.key" -out "$SSL_DIR/server.csr" \
    -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$CN"

# Generate self-signed certificate
openssl x509 -req -days $DAYS -in "$SSL_DIR/server.csr" \
    -signkey "$SSL_DIR/server.key" -out "$SSL_DIR/server.crt"

# Generate certificate with SAN for modern browsers
cat > "$SSL_DIR/san.cnf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORG
OU = $OU
CN = $CN

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
DNS.3 = castor.local
DNS.4 = *.castor.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Regenerate with SAN
openssl req -new -key "$SSL_DIR/server.key" -out "$SSL_DIR/server.csr" \
    -config "$SSL_DIR/san.cnf"

openssl x509 -req -days $DAYS -in "$SSL_DIR/server.csr" \
    -signkey "$SSL_DIR/server.key" -out "$SSL_DIR/server.crt" \
    -extensions req_ext -extfile "$SSL_DIR/san.cnf"

# Set permissions
chmod 600 "$SSL_DIR/server.key"
chmod 644 "$SSL_DIR/server.crt"

# Cleanup
rm -f "$SSL_DIR/server.csr" "$SSL_DIR/san.cnf"

echo "SSL certificates generated successfully!"
echo "  Certificate: $SSL_DIR/server.crt"
echo "  Private Key: $SSL_DIR/server.key"
echo ""
echo "For development, you may need to add the certificate to your system's trusted store."
echo ""
echo "macOS:"
echo "  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $SSL_DIR/server.crt"
echo ""
echo "Linux:"
echo "  sudo cp $SSL_DIR/server.crt /usr/local/share/ca-certificates/"
echo "  sudo update-ca-certificates"

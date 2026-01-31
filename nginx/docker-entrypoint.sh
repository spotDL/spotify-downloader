#!/bin/sh
set -e

# Default environment variables
export API_HOST=${API_HOST:-api}
export API_PORT=${API_PORT:-8000}
export FRONTEND_HOST=${FRONTEND_HOST:-frontend}
export FRONTEND_PORT=${FRONTEND_PORT:-80}

# Substitute environment variables in nginx config
envsubst '${API_HOST} ${API_PORT} ${FRONTEND_HOST} ${FRONTEND_PORT}' \
    < /etc/nginx/nginx.conf.template \
    > /etc/nginx/nginx.conf

# Create certs directory if SSL certs don't exist
if [ ! -f /etc/nginx/certs/cert.pem ]; then
    mkdir -p /etc/nginx/certs
    # Generate self-signed certificate for development
    apk add --no-cache openssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/certs/key.pem \
        -out /etc/nginx/certs/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
fi

exec "$@"

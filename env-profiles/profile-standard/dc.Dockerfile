FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba samba-tool krb5-user winbind dnsutils netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY dc-entrypoint.sh /usr/local/bin/dc-entrypoint.sh
RUN chmod +x /usr/local/bin/dc-entrypoint.sh

EXPOSE 53 88 135 389 445 464 636 3268 3269

ENTRYPOINT ["/usr/local/bin/dc-entrypoint.sh"]

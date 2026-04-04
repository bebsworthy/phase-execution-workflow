# Application Deployment Security: Best Practices and Audit Checklist

> Deep research for building a deployment security audit plugin.
> Covers Docker, PostgreSQL, Nginx, Traefik, TLS, secrets management, pipelines, and runtime security.

---

## Table of Contents

1. [Docker Security](#1-docker-security)
2. [PostgreSQL Security](#2-postgresql-security)
3. [Nginx Security](#3-nginx-security)
4. [Traefik Security](#4-traefik-security)
5. [Application Configuration Security](#5-application-configuration-security)
6. [TLS/SSL Deployment](#6-tlsssl-deployment)
7. [HTTP Security at the Proxy Level](#7-http-security-at-the-proxy-level)
8. [Deployment Pipeline Security](#8-deployment-pipeline-security)
9. [Runtime Application Security](#9-runtime-application-security)
10. [Monitoring and Incident Response](#10-monitoring-and-incident-response)
11. [docker-compose.yml Security Patterns](#11-docker-composeyml-security-patterns)

---

## 1. Docker Security

### 1.1 Dockerfile Best Practices

#### Non-Root Users

Running containers as root (UID 0) is one of the most common and dangerous misconfigurations. A compromised root process inside a container has significantly more breakout potential.

**Audit checks:**
- Dockerfile contains a `USER` directive with a non-root user
- The USER directive appears after package installation but before ENTRYPOINT/CMD
- UIDs are explicitly assigned (not auto-generated)

```dockerfile
# INSECURE: No USER directive, runs as root
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm ci --production
CMD ["node", "server.js"]

# SECURE: Explicit non-root user with fixed UID
FROM node:20-alpine
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup
WORKDIR /app
COPY --chown=appuser:appgroup . .
RUN npm ci --production
USER appuser
CMD ["node", "server.js"]
```

#### Multi-Stage Builds

Multi-stage builds separate build-time dependencies (compilers, dev tools, test frameworks) from the runtime image, drastically reducing the attack surface.

**Audit checks:**
- Dockerfile uses multiple `FROM` statements
- Final stage uses a minimal base image (alpine, distroless, scratch)
- Build tools, source code, and test files are not present in the final image
- Only necessary artifacts are copied between stages

```dockerfile
# SECURE: Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS production
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup
WORKDIR /app
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/package.json ./
USER appuser
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

#### Minimal Base Images

The more packages in an image, the larger the attack surface. Sysdig's 2025 report found a 300% increase in the overall number of packages in container images.

**Audit checks:**
- Base image is minimal (alpine, distroless, slim variants)
- No unnecessary packages installed
- `--no-install-recommends` flag used with apt-get
- Package manager cache is cleaned after installation

```dockerfile
# INSECURE: Full Ubuntu base with extras
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 curl wget vim

# SECURE: Minimal Alpine base, no extras
FROM python:3.12-alpine
RUN apk add --no-cache libpq
```

#### COPY vs ADD

`ADD` has implicit behaviors (auto-extracting archives, fetching remote URLs) that can introduce unexpected content into layers.

**Audit checks:**
- `COPY` is used instead of `ADD` for regular file operations
- `ADD` is only used when archive extraction is explicitly needed
- Remote URLs are fetched with `curl`/`wget` where checksums can be verified

```dockerfile
# INSECURE: ADD with remote URL (no checksum verification)
ADD https://example.com/app.tar.gz /app/

# SECURE: Explicit download with checksum verification
RUN wget -O /tmp/app.tar.gz https://example.com/app.tar.gz && \
    echo "sha256sum_here  /tmp/app.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/app.tar.gz -C /app/ && \
    rm /tmp/app.tar.gz
```

#### No Secrets in Layers

Every layer in a Docker image is persistent. Secrets added in one layer and removed in the next are still recoverable.

**Audit checks:**
- No `ENV` or `ARG` directives contain secrets, passwords, or API keys
- No `.env` files are copied into the image
- Build secrets use `--mount=type=secret` (BuildKit)
- `.dockerignore` excludes `.env`, `*.pem`, `*.key`, credentials files

```dockerfile
# INSECURE: Secret in ENV (persisted in image metadata)
ENV DATABASE_URL=postgres://user:password@host/db

# INSECURE: Secret in ARG (visible in build history)
ARG API_KEY=sk-secret-key

# SECURE: BuildKit secret mount (not persisted in any layer)
RUN --mount=type=secret,id=db_url \
    export DATABASE_URL=$(cat /run/secrets/db_url) && \
    ./setup-database.sh
```

#### Pin Base Image Versions

**Audit checks:**
- Base images use specific version tags, not `latest`
- Preferably pinned by digest for reproducibility

```dockerfile
# INSECURE
FROM node:latest

# BETTER: Version tag
FROM node:20.11-alpine

# BEST: Digest pin
FROM node:20.11-alpine@sha256:abc123...
```

### 1.2 Image Scanning

Container image scanners generate a Software Bill of Materials (SBOM) and compare it against vulnerability databases. Critical note: scanners produce both false positives and false negatives, so they are a necessary but insufficient control.

| Tool | Type | Strengths |
|------|------|-----------|
| **Trivy** | OSS (Aqua Security) | Scans images, filesystems, repos, IaC; multi-format output (table, JSON, SARIF); no daemon needed |
| **Grype** | OSS (Anchore) | Fast CLI scanner; integrates with Syft for SBOMs; strong in CI/CD |
| **Snyk Container** | Commercial | Deep integration with registries; fix recommendations; license compliance |
| **Docker Scout** | Commercial (Docker) | Built into Docker Desktop/Hub; SBOM-based; policy evaluation |

**Audit checks:**
- Image scanning is integrated into CI/CD pipeline
- Scanning runs on every build, not just releases
- Critical/High vulnerabilities block deployment (scanning gate)
- SBOM is generated and stored for each release
- Base images are rebuilt regularly with updated dependencies

```bash
# Trivy scan with severity gate
trivy image --severity CRITICAL,HIGH --exit-code 1 myapp:latest

# Grype scan
grype myapp:latest --fail-on high

# Generate SBOM with Syft, scan with Grype
syft myapp:latest -o spdx-json > sbom.json
grype sbom:sbom.json
```

**Supply chain warning (March 2026):** The Trivy Docker Hub images (tags 0.69.4-0.69.6) were compromised between March 19-23, 2026, potentially exfiltrating CI/CD secrets. Always verify image provenance and use pinned digests.

### 1.3 Docker Compose Security

**Audit checks for every service definition:**

```yaml
# INSECURE: Default everything
services:
  app:
    image: myapp:latest
    ports:
      - "3000:3000"
    volumes:
      - /:/host  # Host root mounted!

# SECURE: Hardened service
services:
  app:
    image: myapp:1.2.3
    read_only: true                    # Read-only root filesystem
    security_opt:
      - no-new-privileges:true         # Prevent privilege escalation
    cap_drop:
      - ALL                            # Drop all Linux capabilities
    cap_add:
      - NET_BIND_SERVICE               # Add back only what's needed
    tmpfs:
      - /tmp:noexec,nosuid,size=100m   # Writable tmp with restrictions
    ports:
      - "127.0.0.1:3000:3000"         # Bind to localhost only
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    volumes:
      - app-data:/app/data:ro          # Named volume, read-only
    user: "1001:1001"                  # Non-root user
```

| Directive | Purpose | Default Risk |
|-----------|---------|-------------|
| `read_only: true` | Prevents filesystem writes | Attackers can write malicious files |
| `security_opt: no-new-privileges:true` | Blocks setuid/setgid escalation | Processes can gain root via setuid binaries |
| `cap_drop: ALL` | Removes all Linux capabilities | Container has ~14 default capabilities |
| `cap_add: [specific]` | Adds back only needed caps | Over-privileged containers |
| `user: "UID:GID"` | Non-root execution | Runs as root (UID 0) |
| `tmpfs` with `noexec,nosuid` | Secure writable areas | Writable areas can execute binaries |
| `ports: "127.0.0.1:..."` | Bind to localhost | Exposed on all interfaces (0.0.0.0) |

### 1.4 Runtime Security

#### Seccomp Profiles

Seccomp filters restrict which system calls a container can make. Docker provides a default profile that blocks ~44 dangerous syscalls.

**Audit checks:**
- Default seccomp profile is NOT disabled (`--security-opt seccomp=unconfined` is absent)
- Custom seccomp profiles are used for high-security workloads
- `privileged: true` is never used (it disables all security features)

#### AppArmor

AppArmor provides mandatory access control, restricting what files, network, and capabilities a container process can access.

**Audit checks:**
- AppArmor is enabled on the host
- Custom AppArmor profiles are loaded for sensitive services
- Default profile is not disabled

#### Rootless Docker

Rootless mode runs the Docker daemon and containers as a non-root user, mitigating vulnerabilities that allow container escape to host root.

**Audit checks:**
- Evaluate rootless mode for environments where possible
- Document why rootless mode cannot be used if it is not enabled

### 1.5 Docker Socket Exposure

The Docker socket (`/var/run/docker.sock`) provides unrestricted root access to the host. Mounting it into a container is equivalent to giving that container full host control.

**Audit checks:**
- Docker socket is NOT mounted into any container
- If socket access is required (e.g., Traefik Docker provider), use a socket proxy with read-only access
- TCP socket is not exposed without TLS + client certificates

```yaml
# INSECURE: Direct socket mount
volumes:
  - /var/run/docker.sock:/var/run/docker.sock

# LESS BAD: Socket proxy (read-only access)
services:
  socket-proxy:
    image: tecnativa/docker-socket-proxy
    environment:
      CONTAINERS: 1
      SERVICES: 0
      TASKS: 0
      NETWORKS: 0
      NODES: 0
      # All write operations disabled by default
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - socket-proxy

  traefik:
    depends_on:
      - socket-proxy
    # NO docker.sock mount -- uses proxy instead
    environment:
      DOCKER_HOST: tcp://socket-proxy:2375
    networks:
      - socket-proxy
      - web
```

### 1.6 Container Networking Security

**Audit checks:**
- Custom networks are defined (not using default bridge)
- `internal: true` is set on networks that should not have external access
- Services are placed on the minimum required networks
- Inter-container communication is restricted to necessary paths

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true    # No external access
  db:
    driver: bridge
    internal: true    # No external access
```

### 1.7 Docker Content Trust / Image Signing

Docker Content Trust (DCT) based on Notary is being retired. The ecosystem is moving toward **Sigstore/Cosign** for image signing and verification.

**Audit checks:**
- Container images are signed before pushing to registry
- Image signature verification is enforced at deployment time
- Signing keys are stored securely (HSM, KMS, or Sigstore keyless)

```bash
# Sign with Cosign (keyless, using OIDC identity)
cosign sign --yes myregistry.com/myapp:1.2.3

# Verify signature
cosign verify myregistry.com/myapp:1.2.3

# Sign with key pair
cosign generate-key-pair
cosign sign --key cosign.key myregistry.com/myapp:1.2.3
cosign verify --key cosign.pub myregistry.com/myapp:1.2.3
```

### Sources: Docker Security

- [Docker Build Best Practices](https://docs.docker.com/build/building/best-practices/)
- [Docker Engine Security](https://docs.docker.com/engine/security/)
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Rootless Mode](https://docs.docker.com/engine/security/rootless/)
- [Docker Content Trust](https://docs.docker.com/engine/security/trust/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Sysdig Dockerfile Best Practices](https://www.sysdig.com/learn-cloud-native/dockerfile-best-practices)
- [Snyk Docker Image Security Best Practices](https://snyk.io/blog/10-docker-image-security-best-practices/)
- [Aqua Security Docker Best Practices](https://www.aquasec.com/blog/docker-security-best-practices/)
- [NIST SP 800-190: Application Container Security Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf)
- [Sigstore Cosign](https://docs.sigstore.dev/cosign/signing/signing_with_containers/)
- [Snyk: Comparing Container Signing Solutions](https://snyk.io/blog/signing-container-images/)

---

## 2. PostgreSQL Security

### 2.1 Authentication Configuration (pg_hba.conf)

The `pg_hba.conf` file is the primary gatekeeper for PostgreSQL connections. Records are evaluated sequentially -- the first matching rule wins.

**Audit checks:**
- No `trust` authentication method on any non-local connection
- `scram-sha-256` is used instead of `md5` for password authentication
- `password` method (cleartext) is never used
- Remote connections require `hostssl` (not `host`)
- Superuser access is restricted to local connections only
- No wildcard (`all`) rules for superuser roles
- Every rule is documented with its purpose

```ini
# INSECURE pg_hba.conf
# TYPE   DATABASE  USER       ADDRESS         METHOD
host     all       all        0.0.0.0/0       trust        # Anyone can connect without password!
host     all       postgres   0.0.0.0/0       md5          # Superuser over network with weak hash

# SECURE pg_hba.conf
# TYPE      DATABASE  USER        ADDRESS           METHOD
# Local superuser access only
local       all       postgres                       scram-sha-256
# Reject superuser from network
hostssl     all       postgres    0.0.0.0/0          reject
hostssl     all       postgres    ::/0               reject
# Application user over SSL only, specific subnet
hostssl     myapp     appuser     172.20.0.0/16      scram-sha-256
# Deny everything else
host        all       all         0.0.0.0/0          reject
host        all       all         ::/0               reject
```

#### SCRAM-SHA-256 vs MD5

SCRAM-SHA-256 is a challenge-response mechanism that prevents password sniffing on untrusted connections and stores passwords in a cryptographically secure form. MD5 is deprecated and will be removed in future PostgreSQL versions.

**Migration steps:**
1. Set `password_encryption = 'scram-sha-256'` in `postgresql.conf`
2. Have all users reset their passwords (so they are re-encrypted)
3. Change all `md5` entries in `pg_hba.conf` to `scram-sha-256`
4. Reload configuration: `SELECT pg_reload_conf();`

### 2.2 Role-Based Access Control

#### GRANT/REVOKE

**Audit checks:**
- Application connects with a dedicated role (not `postgres` superuser)
- Role has minimum required privileges (SELECT only if read-only, etc.)
- `PUBLIC` schema privileges are revoked
- Default privileges are set to restrict access on new objects

```sql
-- INSECURE: App uses superuser
-- Connection string: postgres://postgres:password@host/db

-- SECURE: Dedicated role with minimal privileges
CREATE ROLE appuser WITH LOGIN PASSWORD 'strong_password_here';
REVOKE ALL ON DATABASE myapp FROM PUBLIC;
GRANT CONNECT ON DATABASE myapp TO appuser;

-- Schema-level restrictions
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO appuser;

-- Table-level restrictions
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO appuser;
REVOKE DELETE ON ALL TABLES IN SCHEMA public FROM appuser;

-- Set defaults for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO appuser;

-- Read-only role for reporting
CREATE ROLE readonly WITH LOGIN PASSWORD 'another_strong_password';
GRANT CONNECT ON DATABASE myapp TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO readonly;
```

#### Row-Level Security (RLS)

RLS provides fine-grained access control at the row level, essential for multi-tenant applications.

**Audit checks:**
- RLS is enabled on tables containing tenant-specific data
- Policies cover all operations (SELECT, INSERT, UPDATE, DELETE)
- Default-deny behavior is verified (no policy = no access)
- Superuser/table owner bypass is accounted for (use `FORCE ROW LEVEL SECURITY` on owners)

```sql
-- Enable RLS on a multi-tenant table
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant')::int);

-- Force RLS even for table owner
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

-- Separate policies for different operations
CREATE POLICY select_own ON orders FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant')::int);

CREATE POLICY insert_own ON orders FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::int);

CREATE POLICY update_own ON orders FOR UPDATE
    USING (tenant_id = current_setting('app.current_tenant')::int)
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::int);
```

### 2.3 Connection Security (SSL/TLS)

Enabling SSL in `postgresql.conf` alone is not sufficient -- it must also be enforced in `pg_hba.conf`.

**Audit checks:**
- `ssl = on` in `postgresql.conf`
- `ssl_min_protocol_version = 'TLSv1.2'` (or `TLSv1.3`)
- Only `hostssl` entries in `pg_hba.conf` for remote connections (no `host` or `hostnossl`)
- Client connections use `sslmode=verify-full` (verifies certificate AND hostname)
- SSL certificates are valid, not self-signed in production

```ini
# postgresql.conf
ssl = on
ssl_cert_file = '/etc/postgresql/server.crt'
ssl_key_file = '/etc/postgresql/server.key'
ssl_ca_file = '/etc/postgresql/ca.crt'
ssl_min_protocol_version = 'TLSv1.2'
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'

# Application connection string
# INSECURE
postgresql://user:pass@host/db

# BETTER
postgresql://user:pass@host/db?sslmode=require

# BEST (verifies server certificate and hostname)
postgresql://user:pass@host/db?sslmode=verify-full&sslrootcert=/path/to/ca.crt
```

### 2.4 postgresql.conf Security Settings

**Audit checks for critical settings:**

```ini
# --- Network ---
# INSECURE: Listen on all interfaces
listen_addresses = '*'

# SECURE: Listen only on specific interfaces
listen_addresses = '172.20.0.5'    # Or 'localhost' for local-only

# --- Authentication ---
password_encryption = 'scram-sha-256'   # NOT 'md5'

# --- Logging (security-relevant) ---
log_connections = on                # Log all connection attempts
log_disconnections = on             # Log session terminations with duration
log_statement = 'ddl'              # Log DDL statements (CREATE, ALTER, DROP)
log_line_prefix = '%m [%p] %q%u@%d '  # Include timestamp, PID, user, database

# --- Connection limits ---
max_connections = 100               # Limit total connections
superuser_reserved_connections = 3  # Reserve slots for admin access

# --- SSL (see section 2.3) ---
ssl = on
ssl_min_protocol_version = 'TLSv1.2'
```

### 2.5 Extension Security

**Audit checks:**
- Only necessary extensions are installed
- Extensions are installed in a dedicated schema, not `public`
- `CREATE EXTENSION` is restricted to superusers
- Untrusted extensions are reviewed before installation

### 2.6 Backup Encryption

**Audit checks:**
- Backups are encrypted at rest (GPG, age, or cloud KMS)
- Backup credentials are rotated regularly
- Backup restoration is tested periodically
- WAL archiving uses encrypted transport

```bash
# Encrypted backup with pg_dump + GPG
pg_dump mydb | gpg --symmetric --cipher-algo AES256 -o backup.sql.gpg

# Encrypted backup with age
pg_dump mydb | age -r age1... > backup.sql.age
```

### 2.7 Connection Pooling Security (PgBouncer)

PgBouncer sits between applications and PostgreSQL, so it must be secured on both sides.

**Audit checks:**
- Client-to-PgBouncer connection uses TLS
- PgBouncer-to-PostgreSQL connection uses TLS
- Authentication uses SCRAM-SHA-256 (not MD5 or plaintext)
- PgBouncer admin console is restricted to localhost or disabled
- `auth_type` is set to `scram-sha-256`
- Connection pool mode is appropriate (transaction mode for most apps)

```ini
# pgbouncer.ini
[databases]
mydb = host=postgres port=5432 dbname=mydb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

# Client-side TLS
client_tls_sslmode = require
client_tls_key_file = /etc/pgbouncer/pgbouncer.key
client_tls_cert_file = /etc/pgbouncer/pgbouncer.crt

# Server-side TLS
server_tls_sslmode = verify-full
server_tls_ca_file = /etc/pgbouncer/ca.crt

# Admin restrictions
admin_users = pgbouncer_admin
stats_users = pgbouncer_stats

# Pool sizing
default_pool_size = 20
max_client_conn = 200
```

### 2.8 Audit Logging (pgAudit)

pgAudit provides detailed session and object audit logging required for compliance (SOC 2, PCI-DSS, HIPAA, ISO 27001).

**Audit checks:**
- pgAudit is installed and loaded in `shared_preload_libraries`
- Audit logging covers at least DDL and ROLE operations
- Write operations are logged for sensitive tables
- `pgaudit.log_parameter` is enabled for full statement capture
- Audit logs are shipped to a separate, tamper-resistant store

```ini
# postgresql.conf
shared_preload_libraries = 'pgaudit'

# Log write operations and DDL
pgaudit.log = 'write, ddl, role'

# Include statement parameters in audit log
pgaudit.log_parameter = on

# Reduce catalog noise
pgaudit.log_catalog = off

# For object-level auditing (fine-grained)
pgaudit.role = 'auditor'
```

```sql
-- Create audit role and grant on sensitive tables
CREATE ROLE auditor NOLOGIN;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.financial_transactions TO auditor;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_accounts TO auditor;

-- Install the extension
CREATE EXTENSION pgaudit;
```

**pgaudit.log categories:**
| Category | Statements Logged |
|----------|------------------|
| `READ` | SELECT, COPY FROM |
| `WRITE` | INSERT, UPDATE, DELETE, TRUNCATE, COPY TO |
| `FUNCTION` | Function calls, DO blocks |
| `ROLE` | GRANT, REVOKE, CREATE/ALTER/DROP ROLE |
| `DDL` | All DDL except ROLE class |
| `MISC` | VACUUM, SET, CHECKPOINT, etc. |
| `ALL` | All of the above |

**Important limitation:** pgAudit cannot reliably audit superuser actions. Use the `set_user` extension to require explicit superuser escalation with logging.

### Sources: PostgreSQL Security

- [PostgreSQL: pg_hba.conf Documentation](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)
- [PostgreSQL: Password Authentication](https://www.postgresql.org/docs/current/auth-password.html)
- [PostgreSQL: Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [PostgreSQL: SSL/TLS Connections](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [PostgreSQL: Connections and Authentication Config](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [PostgreSQL: Error Reporting and Logging](https://www.postgresql.org/docs/current/runtime-config-logging.html)
- [pgAudit Documentation](https://github.com/pgaudit/pgaudit/blob/main/README.md)
- [pgAudit.org](https://www.pgaudit.org/)
- [CYBERTEC: PostgreSQL Security - 12 Rules](https://www.cybertec-postgresql.com/en/postgresql-security-things-to-avoid-in-real-life/)
- [CYBERTEC: From MD5 to SCRAM-SHA-256](https://www.cybertec-postgresql.com/en/from-md5-to-scram-sha-256-in-postgresql/)
- [PgBouncer Configuration](https://www.pgbouncer.org/config.html)
- [Crunchy Data: PgBouncer TLS/SSL Security](https://www.crunchydata.com/blog/improving-pgbouncer-security-with-tlsssl)

---

## 3. Nginx Security

### 3.1 TLS Configuration

Use the Mozilla SSL Configuration Generator to produce secure TLS settings. Two recommended profiles:

#### Modern Profile (TLS 1.3 only)

For clients that all support TLS 1.3 (internal services, modern browsers only).

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;

    ssl_protocols TLSv1.3;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # TLS 1.3 ciphers are configured at the OpenSSL level, not nginx
    # Default TLS 1.3 ciphers:
    #   TLS_AES_128_GCM_SHA256
    #   TLS_AES_256_GCM_SHA384
    #   TLS_CHACHA20_POLY1305_SHA256

    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
    resolver 127.0.0.1;
}
```

#### Intermediate Profile (TLS 1.2 + 1.3, recommended for most deployments)

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_dhparam /etc/nginx/ssl/dhparam.pem;  # 2048-bit, ffdhe2048

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
    resolver 127.0.0.1;
}
```

**Audit checks:**
- TLS 1.0 and 1.1 are disabled
- ssl_protocols includes only TLSv1.2 and/or TLSv1.3
- Cipher suite uses only AEAD ciphers (GCM, CHACHA20-POLY1305)
- No CBC, RC4, 3DES, or export ciphers
- DH parameters are at least 2048 bits
- OCSP stapling is enabled
- SSL session tickets are disabled (or keys rotated)

### 3.2 Security Headers

```nginx
# HSTS - Force HTTPS for 2 years, including subdomains
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

# Prevent MIME type sniffing
add_header X-Content-Type-Options "nosniff" always;

# Clickjacking protection
add_header X-Frame-Options "DENY" always;

# XSS protection (legacy, CSP is preferred)
add_header X-XSS-Protection "0" always;

# Content Security Policy (customize per application)
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

# Referrer Policy
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Permissions Policy
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;

# Remove server version disclosure
server_tokens off;
```

**Audit checks:**
- HSTS header present with `max-age` >= 31536000 (1 year)
- `always` parameter used (applies to error responses too)
- `server_tokens off` is set
- X-Content-Type-Options is `nosniff`
- X-Frame-Options is `DENY` or `SAMEORIGIN`
- Content-Security-Policy is defined and appropriate
- Referrer-Policy is set
- Server header does not leak version information

### 3.3 Rate Limiting

```nginx
# Define rate limiting zones
http {
    # 10 requests/second per IP
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;

    # Login endpoint: 5 requests/minute per IP (brute-force protection)
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # API rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

    server {
        # General rate limiting with burst
        location / {
            limit_req zone=general burst=20 nodelay;
            limit_req_status 429;
            proxy_pass http://backend;
        }

        # Strict rate limiting on auth endpoints
        location /api/auth/ {
            limit_req zone=login burst=3 nodelay;
            limit_req_status 429;
            proxy_pass http://backend;
        }

        # API rate limiting
        location /api/ {
            limit_req zone=api burst=50 nodelay;
            limit_req_status 429;
            proxy_pass http://backend;
        }
    }
}
```

**Audit checks:**
- Rate limiting is configured on authentication endpoints
- Rate limiting zones use `$binary_remote_addr` (not `$remote_addr` which wastes memory)
- Burst values are reasonable
- Status code 429 is returned (not default 503)
- Rate limits exist for API endpoints

### 3.4 Request Size Limits

```nginx
# Limit request body size (prevent large upload attacks)
client_max_body_size 10m;

# Limit buffer sizes to prevent buffer overflow attacks
client_body_buffer_size 16k;
client_header_buffer_size 1k;
large_client_header_buffers 4 8k;

# Timeouts to prevent slowloris attacks
client_body_timeout 12;
client_header_timeout 12;
keepalive_timeout 15;
send_timeout 10;
```

### 3.5 Proxy Security

```nginx
location /api/ {
    # Pass real client IP to upstream
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $host;

    # Prevent Host header attacks
    proxy_set_header Host $host;

    # Hide upstream headers that leak information
    proxy_hide_header X-Powered-By;
    proxy_hide_header Server;

    # Restrict HTTP methods
    limit_except GET POST PUT DELETE {
        deny all;
    }

    proxy_pass http://backend;
}
```

### 3.6 Common Misconfigurations

#### Alias Traversal (Off-by-Slash)

One of the most common and dangerous nginx misconfigurations. A missing trailing slash on a `location` directive combined with `alias` enables path traversal.

```nginx
# VULNERABLE: Missing trailing slash on location
location /static {
    alias /var/www/static/;
}
# Request: /static../etc/passwd -> reads /var/www/etc/passwd

# SECURE: Matching trailing slashes
location /static/ {
    alias /var/www/static/;
}
```

#### proxy_pass Off-by-Slash

```nginx
# VULNERABLE: Missing trailing slash enables path traversal to upstream
location /api {
    proxy_pass http://backend/v1/;
}
# Request: /api../admin -> proxied to http://backend/v1/../admin -> http://backend/admin

# SECURE: Consistent trailing slashes
location /api/ {
    proxy_pass http://backend/v1/;
}
```

**Audit checks:**
- All `location` directives with `alias` have matching trailing slashes
- All `location` + `proxy_pass` pairs have consistent trailing slashes
- Use tools like Gixy to detect nginx misconfigurations automatically

### 3.7 Access Control

```nginx
# Restrict admin endpoints by IP
location /admin/ {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    deny all;
    proxy_pass http://backend;
}

# Block access to hidden files
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}

# Block access to backup/config files
location ~* \.(bak|config|sql|fla|psd|ini|log|sh|inc|swp|dist|env)$ {
    deny all;
}
```

### 3.8 ModSecurity / WAF Integration

ModSecurity v3 with the OWASP Core Rule Set (CRS) provides protection against OWASP Top 10 attacks including SQL injection, XSS, LFI, RCE.

**Audit checks:**
- WAF is deployed in front of application (ModSecurity, Coraza, or cloud WAF)
- OWASP CRS is enabled and up to date
- WAF is in blocking mode (not just detection)
- False positive tuning has been performed

```nginx
# ModSecurity integration
modsecurity on;
modsecurity_rules_file /etc/nginx/modsec/main.conf;

# main.conf
Include /etc/nginx/modsec/modsecurity.conf
Include /etc/nginx/modsec/crs/crs-setup.conf
Include /etc/nginx/modsec/crs/rules/*.conf
```

### 3.9 Logging for Security

```nginx
# Custom log format with security-relevant fields
log_format security '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time '
                    '$ssl_protocol $ssl_cipher';

access_log /var/log/nginx/access.log security;
error_log /var/log/nginx/error.log warn;
```

### Sources: Nginx Security

- [Nginx: Configuring HTTPS Servers](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Nginx: ngx_http_limit_req_module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [Nginx Blog: Rate Limiting](https://blog.nginx.org/blog/rate-limiting-nginx)
- [Nginx Blog: HSTS](https://blog.nginx.org/blog/http-strict-transport-security-hsts-and-nginx)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Mozilla Wiki: Server Side TLS](https://wiki.mozilla.org/Security/Server_Side_TLS)
- [OWASP ModSecurity Core Rule Set](https://owasp.org/www-project-modsecurity-core-rule-set/)
- [Detectify: Common Nginx Misconfigurations](https://blog.detectify.com/industry-insights/common-nginx-misconfigurations-that-leave-your-web-server-ope-to-attack/)
- [Acunetix: Path Traversal via Nginx Alias](https://www.acunetix.com/vulnerabilities/web/path-traversal-via-misconfigured-nginx-alias/)

---

## 4. Traefik Security

### 4.1 TLS Configuration

```yaml
# traefik.yml (static configuration)
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

# Dynamic configuration: TLS options
tls:
  options:
    default:
      minVersion: VersionTLS12
      cipherSuites:
        - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
        - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
        - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
        - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
        - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
        - TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256
      sniStrict: true
    modern:
      minVersion: VersionTLS13
```

**Audit checks:**
- HTTP-to-HTTPS redirect is configured on the `web` entrypoint
- `minVersion` is at least `VersionTLS12`
- `sniStrict: true` prevents fallback to default certificate
- Cipher suites are explicitly defined (no weak ciphers)

### 4.2 Middleware Security

```yaml
# Dynamic configuration: security middlewares
http:
  middlewares:
    # Security headers
    security-headers:
      headers:
        browserXssFilter: true
        contentTypeNosniff: true
        frameDeny: true
        stsIncludeSubdomains: true
        stsPreload: true
        stsSeconds: 63072000
        customFrameOptionsValue: "DENY"
        referrerPolicy: "strict-origin-when-cross-origin"
        permissionsPolicy: "camera=(), microphone=(), geolocation=()"

    # Rate limiting
    rate-limit:
      rateLimit:
        average: 100       # requests per second
        burst: 200
        period: 1s

    # IP allowlist (for admin endpoints)
    admin-allowlist:
      ipAllowList:
        sourceRange:
          - "10.0.0.0/8"
          - "172.16.0.0/12"
          - "192.168.0.0/16"

    # Basic auth (for dashboard/admin)
    auth:
      basicAuth:
        users:
          - "admin:$apr1$hashed_password"
```

**Audit checks:**
- Security headers middleware is applied to all routers
- Rate limiting is configured
- Admin endpoints use IP allowlisting
- Authentication middleware protects sensitive routes

### 4.3 Dashboard Security

The Traefik dashboard exposes all configuration elements including sensitive data. It should NEVER be publicly accessible in production.

**Audit checks:**
- Dashboard is disabled in production (`api.dashboard: false`) or heavily restricted
- If enabled, dashboard requires authentication AND IP restriction
- Dashboard is not exposed on public entrypoints
- API insecure mode is disabled (`api.insecure: false`)

```yaml
# traefik.yml
api:
  dashboard: true    # Only if needed
  insecure: false    # NEVER true in production

# Docker labels for dashboard router
# traefik.http.routers.dashboard.rule=Host(`traefik.internal.example.com`)
# traefik.http.routers.dashboard.middlewares=auth,admin-allowlist
# traefik.http.routers.dashboard.service=api@internal
# traefik.http.routers.dashboard.tls=true
```

### 4.4 Let's Encrypt / ACME Security

```yaml
# traefik.yml
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /etc/traefik/acme.json
      httpChallenge:
        entryPoint: web
      # OR for DNS challenge (preferred for wildcard certs)
      # dnsChallenge:
      #   provider: cloudflare
```

**Audit checks:**
- ACME storage file (`acme.json`) has restrictive permissions (600)
- ACME email is monitored (for expiration notifications)
- Production ACME endpoint is used (not staging)
- Certificate renewal is tested and working
- DNS challenge credentials are managed as secrets

### 4.5 Docker Provider Security

```yaml
# traefik.yml
providers:
  docker:
    exposedByDefault: false    # CRITICAL: Don't auto-expose containers
    endpoint: "unix:///var/run/docker.sock"
    # Or use socket proxy:
    # endpoint: "tcp://socket-proxy:2375"
    network: traefik           # Specify the network for communication
```

**Audit checks:**
- `exposedByDefault: false` is set (containers must opt-in with `traefik.enable=true`)
- Docker socket access is minimized (socket proxy preferred)
- Traefik communicates with services over a dedicated network
- Container labels are reviewed for unintended exposure

### 4.6 Access Logging

```yaml
# traefik.yml
accessLog:
  filePath: "/var/log/traefik/access.log"
  format: json
  fields:
    headers:
      defaultMode: drop
      names:
        User-Agent: keep
        Authorization: redact
        Content-Type: keep
  bufferingSize: 100
```

### Sources: Traefik Security

- [Traefik: API & Dashboard](https://doc.traefik.io/traefik/reference/install-configuration/api-dashboard/)
- [Traefik: TLS Options](https://doc.traefik.io/traefik/reference/routing-configuration/http/tls/tls-options/)
- [Traefik: Docker Provider](https://doc.traefik.io/traefik/expose/docker/basic/)
- [Traefik: Docker Standalone Setup](https://doc.traefik.io/traefik/setup/docker/)
- [Traefik: EntryPoints](https://doc.traefik.io/traefik/reference/install-configuration/entrypoints/)

---

## 5. Application Configuration Security

### 5.1 Environment Variable Management

Environment variables are the most common -- and one of the least secure -- ways to manage secrets in deployments.

**Risk hierarchy (worst to best):**
1. Hardcoded in source code (worst)
2. `.env` files committed to version control
3. `.env` files on disk, excluded from VCS
4. CI/CD platform secrets (GitHub Actions secrets, GitLab CI variables)
5. Docker/Swarm secrets (injected as files)
6. External secrets manager (HashiCorp Vault, AWS Secrets Manager, etc.)
7. Application fetches secrets at runtime via identity-based auth (best)

**Audit checks:**
- No secrets in source code or version control history
- `.env` files are in `.gitignore` and `.dockerignore`
- Docker ENV/ARG instructions do not contain secrets
- Environment variables with secrets are not logged or exposed via `/proc`
- Production secrets use a dedicated secrets manager

```yaml
# INSECURE: Secrets in docker-compose.yml
services:
  app:
    environment:
      DATABASE_URL: "postgres://user:password@db/myapp"
      API_KEY: "sk-secret-key-12345"

# BETTER: Reference .env file (not committed to VCS)
services:
  app:
    env_file:
      - .env  # Must be in .gitignore AND .dockerignore

# BEST: Docker secrets
services:
  app:
    secrets:
      - db_password
      - api_key
    environment:
      DATABASE_URL_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt  # File with restricted permissions
  api_key:
    file: ./secrets/api_key.txt
```

### 5.2 Configuration File Permissions

**Audit checks:**
- Configuration files containing secrets have restrictive permissions (600 or 640)
- Configuration files are owned by the service user, not root
- No world-readable secrets files
- TLS private keys are readable only by the service (600)
- Docker Compose files with embedded secrets have restricted access

```bash
# Verify file permissions
chmod 600 /etc/app/secrets.conf
chmod 600 /etc/traefik/acme.json
chmod 600 /etc/postgresql/server.key
chown postgres:postgres /etc/postgresql/server.key
```

### 5.3 Secrets Rotation Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Gradual rotation** | New key introduced, old key maintained for reads | Database credentials, API keys |
| **Rapid rotation** | Immediate switchover, minimal backward compatibility | Compromised credentials |
| **Scheduled rotation** | Predetermined intervals per secret type | Compliance requirements |
| **Automated rotation** | Sidecar/Lambda/CronJob handles full lifecycle | Production credentials |

**Audit checks:**
- Secret rotation process is documented
- Rotation can be performed without downtime
- Old secrets are revoked after rotation window
- Rotation events are logged
- Emergency rotation procedure exists for breach scenarios

### 5.4 12-Factor App Security Implications

The Twelve-Factor App methodology has security implications:

| Factor | Security Implication |
|--------|---------------------|
| **Config** | Store config in environment, but secrets need additional protection |
| **Backing services** | Credential rotation must not require code changes |
| **Build/Release/Run** | Immutable releases prevent runtime tampering |
| **Disposability** | Fast startup/shutdown enables rapid rotation and incident response |
| **Logs** | Treat logs as event streams -- never log secrets |
| **Admin processes** | One-off admin tasks need same security as app processes |

### 5.5 Pre-Commit Secret Detection

**Audit checks:**
- Pre-commit hooks scan for secrets before they enter VCS
- CI/CD pipeline includes secret detection as a gate

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### Sources: Configuration Security

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [OWASP DevSecOps Guideline: Secrets Management](https://owasp.org/www-project-devsecops-guideline/latest/01a-Secrets-Management)
- [OWASP Configuration and Deployment Management Testing](https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/02-Test_Application_Platform_Configuration)

---

## 6. TLS/SSL Deployment

### 6.1 Certificate Management

#### Let's Encrypt + cert-manager (Kubernetes)

```yaml
# ClusterIssuer for Let's Encrypt production
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: security@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
      # OR DNS challenge for wildcard certs
      # - dns01:
      #     cloudflare:
      #       apiTokenSecretRef:
      #         name: cloudflare-api-token
      #         key: api-token
```

**Audit checks:**
- Certificates are automatically renewed (Let's Encrypt: 90-day certs, renew at 30 days)
- Production ACME endpoint is used (not staging)
- ACME account email is monitored
- DNS challenge is used for wildcard certificates
- cert-manager is deployed and healthy
- Certificate secrets have appropriate RBAC

#### Manual Certificate Management

**Audit checks:**
- Certificate expiration monitoring is in place
- Renewal process is documented and tested
- Private keys are generated with at least 2048-bit RSA or P-256 ECDSA
- Private keys are not shared between environments
- Old certificates are revoked when rotated

### 6.2 TLS 1.3 Preference

TLS 1.3 is the current standard. It removes insecure algorithms, reduces handshake round-trips, and eliminates entire classes of attacks (BEAST, POODLE, Lucky13).

**Audit checks:**
- TLS 1.0 and 1.1 are disabled everywhere
- TLS 1.2 is the minimum, TLS 1.3 is preferred
- Only AEAD cipher suites are allowed with TLS 1.2

### 6.3 Cipher Suite Selection

**Mozilla recommended cipher suites (Intermediate profile):**

TLS 1.3 (all three are mandatory to implement):
- `TLS_AES_128_GCM_SHA256`
- `TLS_AES_256_GCM_SHA384`
- `TLS_CHACHA20_POLY1305_SHA256`

TLS 1.2 (ECDHE + AEAD only):
- `ECDHE-ECDSA-AES128-GCM-SHA256`
- `ECDHE-RSA-AES128-GCM-SHA256`
- `ECDHE-ECDSA-AES256-GCM-SHA384`
- `ECDHE-RSA-AES256-GCM-SHA384`
- `ECDHE-ECDSA-CHACHA20-POLY1305`
- `ECDHE-RSA-CHACHA20-POLY1305`
- `DHE-RSA-AES128-GCM-SHA256`
- `DHE-RSA-AES256-GCM-SHA384`

**Ciphers to reject (audit flags):**
- RC4, 3DES, DES
- CBC mode ciphers (unless TLS 1.2 fallback is required)
- Export ciphers
- NULL ciphers
- Static RSA key exchange (no forward secrecy)

### 6.4 HSTS Deployment

HTTP Strict Transport Security prevents protocol downgrade attacks and cookie hijacking.

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

**Deployment strategy:**
1. Start with short `max-age` (300 seconds) to test
2. Increase to 1 week (604800), then 1 month (2592000)
3. Add `includeSubDomains` once all subdomains support HTTPS
4. Add `preload` and submit to [hstspreload.org](https://hstspreload.org/)
5. Final: `max-age=63072000` (2 years) for preload requirement

**Audit checks:**
- HSTS header is present on all HTTPS responses
- `max-age` is at least 31536000 (1 year)
- `includeSubDomains` is set if all subdomains use HTTPS
- `always` parameter is used in nginx (applies to error pages)

### 6.5 OCSP Stapling

OCSP stapling improves privacy and performance by having the server fetch and cache OCSP responses instead of clients contacting the CA.

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
resolver 127.0.0.1 valid=300s;
resolver_timeout 5s;
```

**Audit checks:**
- OCSP stapling is enabled
- Trusted certificate chain is configured
- DNS resolver is configured for stapling
- Stapling is verified with: `openssl s_client -connect host:443 -status`

### 6.6 Certificate Transparency Monitoring

Certificate Transparency (CT) logs provide visibility into certificates issued for your domains, helping detect unauthorized issuance.

**Audit checks:**
- CT monitoring is configured for all production domains
- Alerts fire on unexpected certificate issuance
- Services like crt.sh, SSLMate's Cert Spotter, or Facebook CT monitoring are used

### Sources: TLS/SSL

- [Mozilla Wiki: Server Side TLS](https://wiki.mozilla.org/Security/Server_Side_TLS)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [cert-manager: ACME Configuration](https://cert-manager.io/docs/configuration/acme/)
- [Let's Encrypt: How It Works](https://letsencrypt.org/how-it-works/)
- [Nginx Blog: HSTS and Nginx](https://blog.nginx.org/blog/http-strict-transport-security-hsts-and-nginx)
- [HSTS Preload Submission](https://hstspreload.org/)

---

## 7. HTTP Security at the Proxy Level

### 7.1 Request/Response Header Manipulation

```nginx
# Remove headers that leak information
proxy_hide_header X-Powered-By;
proxy_hide_header X-AspNet-Version;
proxy_hide_header X-AspNetMvc-Version;
proxy_hide_header Server;
server_tokens off;

# Add security headers (see Section 3.2)

# Prevent request smuggling
proxy_http_version 1.1;
proxy_set_header Connection "";
```

**Audit checks:**
- Upstream response headers that leak technology stack are stripped
- X-Powered-By, Server version, technology-specific headers are removed
- Security headers are added at proxy level (consistent across all backends)
- HTTP/1.1 is used for upstream connections (prevents smuggling with HTTP/1.0)

### 7.2 Upstream Security

```nginx
upstream backend {
    server 127.0.0.1:3000;
    # Health checks (commercial nginx plus or third-party module)
    # Keepalive connections to reduce overhead
    keepalive 32;
}

server {
    location /api/ {
        # Prevent upstream from seeing sensitive request headers
        proxy_set_header Authorization "";  # Strip if proxying to untrusted upstream
        
        # Timeout protection
        proxy_connect_timeout 5s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        proxy_pass http://backend;
    }
}
```

**Audit checks:**
- Upstream services are not directly accessible from the internet
- Proxy timeouts are configured (prevents resource exhaustion)
- Upstream communication is encrypted if crossing network boundaries
- Health check endpoints on upstream services are not exposed publicly

### 7.3 WebSocket Proxy Security

```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # Timeouts for WebSocket connections
    proxy_read_timeout 300s;    # WebSocket idle timeout
    proxy_send_timeout 300s;
    
    # Rate limiting still applies
    limit_req zone=ws burst=10 nodelay;
}
```

**Audit checks:**
- WebSocket upgrade is only allowed on intended paths
- WebSocket connections have idle timeouts
- Rate limiting applies to WebSocket upgrade requests
- Origin header validation is performed (by application or proxy)

### 7.4 DDoS Mitigation at Proxy Layer

```nginx
# Connection limits per IP
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

server {
    # Max 20 concurrent connections per IP
    limit_conn conn_limit 20;
    limit_conn_status 429;
    
    # Request rate limiting (see Section 3.3)
    limit_req zone=general burst=20 nodelay;
    
    # Limit request body size
    client_max_body_size 10m;
    
    # Timeout settings (anti-slowloris)
    client_body_timeout 12;
    client_header_timeout 12;
    keepalive_timeout 15;
    send_timeout 10;
}
```

**Audit checks:**
- Connection limits per IP are configured
- Request rate limits are configured
- Body size limits are set
- Timeouts prevent slow-rate attacks (slowloris, slow POST)
- Consider upstream DDoS protection (Cloudflare, AWS Shield, etc.) for public services

### Sources: HTTP Proxy Security

- [Nginx: Configuring HTTPS Servers](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Nginx: ngx_http_limit_req_module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [Nginx Blog: Rate Limiting](https://blog.nginx.org/blog/rate-limiting-nginx)
- [Traefik: Middlewares Overview](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/)

---

## 8. Deployment Pipeline Security

### 8.1 Image Registry Security

**Audit checks:**
- Private registry is used for proprietary images
- Registry access requires authentication
- Images are scanned for vulnerabilities before push (CI gate)
- Image tags are immutable (digest-based references in production)
- Old/vulnerable images are garbage collected
- Registry supports and enforces image signing

```yaml
# GitHub Actions: Scan and push
- name: Build image
  run: docker build -t myregistry.com/app:${{ github.sha }} .

- name: Scan for vulnerabilities
  run: trivy image --exit-code 1 --severity CRITICAL,HIGH myregistry.com/app:${{ github.sha }}

- name: Sign image
  run: cosign sign --yes myregistry.com/app:${{ github.sha }}

- name: Push image
  run: docker push myregistry.com/app:${{ github.sha }}
```

### 8.2 Deployment Secrets Injection

**Audit checks:**
- Secrets are injected at deployment time, not build time
- CI/CD platform secrets are scoped (per-environment, per-repo)
- Production secrets are not accessible from feature branches
- Secret access is logged and auditable
- Secrets are masked in CI/CD logs

```yaml
# GitHub Actions: Proper secret scoping
jobs:
  deploy-production:
    environment: production    # Requires approval + scoped secrets
    steps:
      - name: Deploy
        env:
          DATABASE_URL: ${{ secrets.PROD_DATABASE_URL }}
        run: ./deploy.sh
```

### 8.3 Rollback Security

**Audit checks:**
- Rollback procedure is documented and tested
- Previous known-good images are retained
- Rollback does not re-expose fixed vulnerabilities (vulnerability checks on rollback targets)
- Database migrations are backward-compatible (to support rollback)
- Rollback events are logged and alerted

### 8.4 Blue-Green / Canary Security

**Audit checks:**
- Both blue and green environments have identical security configurations
- Canary deployments don't bypass security middleware
- Traffic shifting preserves TLS termination
- Session/token security is maintained across deployment transitions
- Monitoring is active during traffic shifts to detect security anomalies

### 8.5 GitOps Security (Flux, ArgoCD)

**ArgoCD security considerations:**

```yaml
# ArgoCD: Restrict repository access
apiVersion: v1
kind: Secret
metadata:
  name: private-repo
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  url: https://github.com/org/deploy-configs
  password: $ARGOCD_REPO_TOKEN
  username: argocd
```

**Audit checks (ArgoCD):**
- ArgoCD server is not publicly accessible
- RBAC is configured (not everyone can sync to production)
- Repository credentials are stored as Kubernetes secrets
- SSO/OIDC is configured for authentication (not local accounts)
- Webhook secrets are configured for Git notifications
- Audit logging is enabled
- Resource hooks include security scanning (PostSync)

**Audit checks (Flux):**
- Source controller RBAC follows least privilege
- Git repository credentials use deploy keys (not personal tokens)
- Image update automation uses signature verification
- Multi-tenancy is configured with proper namespace isolation
- Policy enforcement (Kyverno/OPA) gates deployments

### Sources: Pipeline Security

- [ArgoCD Security Considerations](https://argo-cd.readthedocs.io/en/stable/security_considerations/)
- [Flux Security Documentation](https://fluxcd.io/flux/security/)
- [Trivy Documentation](https://trivy.dev/)
- [Aqua Security: Container Image Scanning Tools](https://www.aquasec.com/cloud-native-academy/docker-container/container-image-scanning-tools/)

---

## 9. Runtime Application Security

### 9.1 Health Check Endpoint Security

Health check endpoints (`/health`, `/healthz`, `/readiness`) should not expose sensitive information.

**Audit checks:**
- Health endpoints return only status (200/503), no internal details
- Detailed health checks (with dependency status) are on a separate, restricted endpoint
- Health endpoints do not require authentication (for load balancer probes)
- Health endpoints do not leak database connection strings, versions, or internal IPs

```json
// INSECURE: Leaks internal details
{
  "status": "healthy",
  "database": "postgres://user:pass@10.0.1.5:5432/mydb",
  "redis": "redis://10.0.1.6:6379",
  "version": "3.2.1-debug",
  "uptime": "72h"
}

// SECURE: Minimal response
{
  "status": "ok"
}

// SECURE: Detailed check on restricted endpoint
// GET /internal/health (only accessible from internal network)
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "disk": "ok"
  }
}
```

### 9.2 Metrics Endpoint Protection (Prometheus)

Prometheus `/metrics` endpoints expose operational data that can reveal architecture, performance characteristics, and potentially sensitive labels.

**Audit checks:**
- `/metrics` endpoint is not publicly accessible
- Metrics are served on a separate port (not the public-facing port)
- Basic auth or mTLS protects the metrics endpoint
- Metric labels do not contain PII, tokens, or credentials
- Prometheus server itself is not publicly accessible

```nginx
# Restrict metrics to internal network
location /metrics {
    allow 10.0.0.0/8;
    deny all;
    proxy_pass http://app:9090;
}
```

```yaml
# Docker Compose: Metrics on separate, unexposed port
services:
  app:
    ports:
      - "3000:3000"        # Public API
      # 9090 NOT exposed -- only accessible to Prometheus on internal network
    networks:
      - frontend
      - monitoring

  prometheus:
    networks:
      - monitoring         # Same network as app, can reach :9090
    # NOT on frontend network
```

### 9.3 Admin Interface Protection

**Audit checks:**
- Admin interfaces are on separate ports or paths
- Admin access requires strong authentication (MFA preferred)
- Admin interfaces are restricted by IP/network
- Admin actions are logged
- Debug endpoints (`/debug/pprof`, `/debug/vars`) are disabled in production

### 9.4 Graceful Shutdown Security

**Audit checks:**
- Application handles SIGTERM gracefully
- In-flight requests complete before shutdown
- Connection draining timeout is configured
- Database connections are properly closed
- Temporary files/secrets in memory are cleared

### 9.5 Resource Limits

Resource limits prevent denial-of-service and resource exhaustion attacks.

```yaml
# Docker Compose resource limits
services:
  app:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
        reservations:
          memory: 256M
          cpus: '0.25'
    ulimits:
      nofile:
        soft: 1024
        hard: 2048
      nproc:
        soft: 512
        hard: 1024
```

**Audit checks:**
- Memory limits are set (prevents OOM killing other containers)
- CPU limits are set
- File descriptor limits are set
- Process count limits are set
- Disk space/quota limits are configured for volumes
- `--restart=on-failure:N` limits restart loops (not `unless-stopped` for crash-looping containers)

### Sources: Runtime Security

- [Prometheus Security Model](https://prometheus.io/docs/operating/security/)
- [Prometheus: Basic Auth for API/UI](https://prometheus.io/docs/guides/basic-auth/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

---

## 10. Monitoring and Incident Response

### 10.1 Security-Relevant Logging

**What to log:**
- Authentication attempts (success and failure)
- Authorization failures (403 responses)
- Input validation failures
- Application errors (500 responses)
- Configuration changes
- Admin actions
- Rate limit triggers
- SSL/TLS handshake failures

**Audit checks:**
- Centralized log aggregation is configured (ELK, Loki, Datadog, etc.)
- Logs are shipped in real-time (not just stored locally)
- Log retention meets compliance requirements
- Logs are stored in a tamper-resistant system
- Log format is structured (JSON) for reliable parsing

```yaml
# Docker Compose: Centralized logging
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        tag: "app-{{.Name}}"

  # Or ship to external aggregator
  app:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "localhost:24224"
        tag: "docker.app"
```

### 10.2 Alerting on Security Events

**Alert triggers (minimum set):**

| Event | Severity | Example |
|-------|----------|---------|
| Multiple failed auth attempts | High | 5+ failures from same IP in 1 minute |
| Successful auth after failures | Medium | Potential brute-force success |
| 403 spike | Medium | Authorization bypass attempts |
| 500 spike | High | Application vulnerability exploitation |
| Certificate expiring < 7 days | Critical | TLS certificate about to expire |
| Container restart loop | High | Potential crash from attack |
| Resource limit hit | Medium | DoS or resource exhaustion |
| New network connection pattern | Medium | Lateral movement indicator |
| Config file change | High | Unauthorized modification |

### 10.3 Intrusion Detection

**Audit checks:**
- Runtime security monitoring is deployed (Falco, Tetragon, or commercial EDR)
- Behavioral anomaly detection covers:
  - Unexpected process execution in containers
  - Network connections to unusual destinations
  - File access patterns outside normal operation
  - Privilege escalation attempts
- Security events trigger alerts, not just logs

```yaml
# Falco rule example: Detect shell in container
- rule: Terminal shell in container
  desc: A shell was used as the entrypoint/exec point into a container
  condition: >
    spawned_process and container
    and shell_procs and proc.pname exists
    and not proc.pname in (container_entrypoint_proc_names)
  output: >
    Shell spawned in container (container=%container.name
    shell=%proc.name parent=%proc.pname cmdline=%proc.cmdline)
  priority: WARNING
```

### 10.4 Audit Trail Integrity

**Audit checks:**
- Logs are written to append-only storage
- Log checksums or signatures are verified
- Timestamps are synchronized (NTP configured)
- Log deletion requires elevated privileges and is itself logged
- Audit logs are separated from application logs

### 10.5 Log Injection Prevention

Attackers can inject false log entries by including newlines or log-format strings in user input.

**Audit checks:**
- User input in log messages is sanitized (newlines, carriage returns stripped)
- Structured logging (JSON) is used instead of plain text
- Log parsing does not execute embedded commands
- Log viewers are not vulnerable to XSS from log content

```python
# INSECURE: Direct user input in log
logger.info(f"User login: {username}")
# Attacker input: "admin\n2026-04-04 INFO User login: admin - success"
# Creates fake log entry

# SECURE: Structured logging
logger.info("User login attempt", extra={"username": username, "ip": request.remote_addr})
# Output: {"message": "User login attempt", "username": "admin\\nfake", "ip": "1.2.3.4"}
```

### Sources: Monitoring

- [Prometheus Security Model](https://prometheus.io/docs/operating/security/)
- [Falco Documentation](https://falco.org/docs/)
- [JFrog: Protecting Prometheus](https://jfrog.com/blog/dont-let-prometheus-steal-your-fire/)

---

## 11. docker-compose.yml Security Patterns

### 11.1 Full-Stack Secure Pattern: App + PostgreSQL + Redis + Nginx

```yaml
version: "3.8"

services:
  # ============================================================
  # REVERSE PROXY (Nginx)
  # ============================================================
  nginx:
    image: nginx:1.27-alpine
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE       # Bind to ports 80/443
    tmpfs:
      - /tmp:noexec,nosuid,size=10m
      - /var/cache/nginx:noexec,nosuid,size=50m
      - /var/run:noexec,nosuid,size=1m
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certs:/etc/nginx/ssl:ro
    networks:
      - frontend
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    depends_on:
      app:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  # ============================================================
  # APPLICATION
  # ============================================================
  app:
    image: myapp:1.2.3                 # Pinned version, not :latest
    build:
      context: .
      dockerfile: Dockerfile
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    user: "1001:1001"
    environment:
      NODE_ENV: production
      PORT: "3000"
      # Non-secret config only in environment
      DB_HOST: postgres
      DB_PORT: "5432"
      DB_NAME: myapp
      REDIS_HOST: redis
      REDIS_PORT: "6379"
    secrets:
      - db_password
      - redis_password
      - session_secret
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - frontend                       # Nginx -> App
      - backend                        # App -> Postgres
      - cache                          # App -> Redis
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
        reservations:
          memory: 256M
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  # ============================================================
  # POSTGRESQL
  # ============================================================
  postgres:
    image: postgres:16-alpine
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - DAC_OVERRIDE              # Required for PostgreSQL
      - FOWNER                    # Required for PostgreSQL
      - SETGID                    # Required for PostgreSQL
      - SETUID                    # Required for PostgreSQL
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
      - /run/postgresql:noexec,nosuid,size=10m
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
      # Do NOT use POSTGRES_PASSWORD -- use _FILE variant
    secrets:
      - db_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
      - ./postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: >
      postgres
        -c config_file=/etc/postgresql/postgresql.conf
        -c hba_file=/etc/postgresql/pg_hba.conf
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend                        # Only app can reach postgres
    # NO ports exposed to host -- accessed only via backend network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2.0'
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  # ============================================================
  # REDIS
  # ============================================================
  redis:
    image: redis:7-alpine
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:noexec,nosuid,size=10m
    command: >
      redis-server
        --requirepass /run/secrets/redis_password
        --maxmemory 256mb
        --maxmemory-policy allkeys-lru
        --rename-command FLUSHALL ""
        --rename-command FLUSHDB ""
        --rename-command CONFIG ""
        --rename-command DEBUG ""
    secrets:
      - redis_password
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - cache                          # Only app can reach redis
    # NO ports exposed to host
    deploy:
      resources:
        limits:
          memory: 300M
          cpus: '0.5'
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

# ============================================================
# NETWORKS (isolation)
# ============================================================
networks:
  frontend:
    driver: bridge
    # Nginx <-> App communication
  backend:
    driver: bridge
    internal: true                     # No external access
    # App <-> PostgreSQL communication
  cache:
    driver: bridge
    internal: true                     # No external access
    # App <-> Redis communication

# ============================================================
# VOLUMES
# ============================================================
volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local

# ============================================================
# SECRETS
# ============================================================
secrets:
  db_password:
    file: ./secrets/db_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  session_secret:
    file: ./secrets/session_secret.txt
```

### 11.2 Full-Stack Secure Pattern: App + PostgreSQL + Traefik

```yaml
version: "3.8"

services:
  # ============================================================
  # TRAEFIK (Reverse Proxy)
  # ============================================================
  traefik:
    image: traefik:v3.2
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    ports:
      - "80:80"
      - "443:443"
      # Dashboard NOT exposed on public port
    volumes:
      - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
      - ./traefik/dynamic:/etc/traefik/dynamic:ro
      - traefik-certs:/etc/traefik/acme
    networks:
      - frontend
      - socket-proxy
    depends_on:
      - socket-proxy
    environment:
      DOCKER_HOST: tcp://socket-proxy:2375
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    restart: unless-stopped

  # ============================================================
  # DOCKER SOCKET PROXY (Security layer)
  # ============================================================
  socket-proxy:
    image: tecnativa/docker-socket-proxy
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    environment:
      CONTAINERS: 1
      SERVICES: 0
      TASKS: 0
      NETWORKS: 0
      NODES: 0
      VOLUMES: 0
      IMAGES: 0
      INFO: 0
      POST: 0                          # Read-only access
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - socket-proxy
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
    restart: unless-stopped

  # ============================================================
  # APPLICATION
  # ============================================================
  app:
    image: myapp:1.2.3
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    user: "1001:1001"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app.rule=Host(`app.example.com`)"
      - "traefik.http.routers.app.tls=true"
      - "traefik.http.routers.app.tls.certresolver=letsencrypt"
      - "traefik.http.routers.app.middlewares=security-headers,rate-limit"
      - "traefik.http.services.app.loadbalancer.server.port=3000"
    secrets:
      - db_password
    networks:
      - frontend
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
    restart: unless-stopped

  # PostgreSQL (same as previous pattern, on backend network)
  postgres:
    image: postgres:16-alpine
    # ... (same security hardening as above)
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
  socket-proxy:
    driver: bridge
    internal: true

volumes:
  traefik-certs:
    driver: local
  postgres-data:
    driver: local

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### 11.3 Security Audit Checklist for docker-compose.yml

| # | Check | Severity |
|---|-------|----------|
| 1 | No `privileged: true` on any service | Critical |
| 2 | `security_opt: no-new-privileges:true` on all services | High |
| 3 | `cap_drop: ALL` on all services | High |
| 4 | `cap_add` only includes required capabilities | High |
| 5 | `read_only: true` on all services | Medium |
| 6 | No secrets in `environment` section (use `secrets`) | Critical |
| 7 | `POSTGRES_PASSWORD_FILE` used instead of `POSTGRES_PASSWORD` | High |
| 8 | No host volumes mounting sensitive paths (`/`, `/etc`, `/var/run/docker.sock`) | Critical |
| 9 | Docker socket not mounted (or uses socket proxy) | Critical |
| 10 | Database ports not exposed to host | High |
| 11 | Internal networks (`internal: true`) for backend services | High |
| 12 | Services on minimum required networks | Medium |
| 13 | Image versions pinned (no `:latest`) | Medium |
| 14 | Resource limits set (`memory`, `cpus`) | Medium |
| 15 | Health checks configured on all services | Medium |
| 16 | Logging configured with size limits | Low |
| 17 | Non-root `user` specified | High |
| 18 | `tmpfs` with `noexec,nosuid` for writable paths | Medium |
| 19 | Volumes mounted as `:ro` where possible | Medium |
| 20 | Restart policy prevents infinite restart loops | Low |
| 21 | Redis dangerous commands renamed/disabled | Medium |
| 22 | No `network_mode: host` on any service | High |
| 23 | No `pid: host` or `ipc: host` on any service | Critical |
| 24 | Proxy binds to `127.0.0.1` when only local access needed | Medium |

### Sources: Compose Security Patterns

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Docker Docs: Compose File Reference](https://docs.docker.com/compose/compose-file/)
- [Docker Docs: Build Best Practices](https://docs.docker.com/build/building/best-practices/)
- [NIST SP 800-190: Application Container Security Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf)
- [Tecnativa Docker Socket Proxy](https://github.com/Tecnativa/docker-socket-proxy)

---

## Consolidated Primary Sources

### Standards and Frameworks
- [NIST SP 800-190: Application Container Security Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [OWASP DevSecOps Guideline](https://owasp.org/www-project-devsecops-guideline/)
- [OWASP Configuration and Deployment Testing](https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/)

### Docker
- [Docker Build Best Practices](https://docs.docker.com/build/building/best-practices/)
- [Docker Engine Security](https://docs.docker.com/engine/security/)
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Rootless Mode](https://docs.docker.com/engine/security/rootless/)
- [Docker Content Trust](https://docs.docker.com/engine/security/trust/)

### PostgreSQL
- [PostgreSQL: pg_hba.conf](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)
- [PostgreSQL: Password Authentication](https://www.postgresql.org/docs/current/auth-password.html)
- [PostgreSQL: Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [PostgreSQL: SSL/TLS Connections](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [PostgreSQL: Connection Config](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [PostgreSQL: Logging Config](https://www.postgresql.org/docs/current/runtime-config-logging.html)
- [pgAudit](https://github.com/pgaudit/pgaudit)
- [PgBouncer Configuration](https://www.pgbouncer.org/config.html)

### Nginx
- [Nginx: HTTPS Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Nginx: Rate Limiting Module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [Nginx Blog: Rate Limiting](https://blog.nginx.org/blog/rate-limiting-nginx)
- [Nginx Blog: HSTS](https://blog.nginx.org/blog/http-strict-transport-security-hsts-and-nginx)

### Traefik
- [Traefik: API & Dashboard](https://doc.traefik.io/traefik/reference/install-configuration/api-dashboard/)
- [Traefik: TLS Options](https://doc.traefik.io/traefik/reference/routing-configuration/http/tls/tls-options/)
- [Traefik: Docker Setup](https://doc.traefik.io/traefik/setup/docker/)
- [Traefik: EntryPoints](https://doc.traefik.io/traefik/reference/install-configuration/entrypoints/)

### TLS/SSL
- [Mozilla Wiki: Server Side TLS](https://wiki.mozilla.org/Security/Server_Side_TLS)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [cert-manager: ACME Configuration](https://cert-manager.io/docs/configuration/acme/)
- [Let's Encrypt: How It Works](https://letsencrypt.org/how-it-works/)
- [HSTS Preload](https://hstspreload.org/)

### Container Scanning and Supply Chain
- [Trivy](https://trivy.dev/)
- [Grype (Anchore)](https://github.com/anchore/grype)
- [Sigstore/Cosign](https://docs.sigstore.dev/)
- [Snyk Container](https://snyk.io/product/container-vulnerability-management/)

### GitOps
- [ArgoCD Security Considerations](https://argo-cd.readthedocs.io/en/stable/security_considerations/)
- [Flux Security](https://fluxcd.io/flux/security/)

### Monitoring
- [Prometheus Security Model](https://prometheus.io/docs/operating/security/)
- [Prometheus: Basic Auth](https://prometheus.io/docs/guides/basic-auth/)
- [Falco](https://falco.org/docs/)

### Additional Resources
- [CYBERTEC: PostgreSQL Security Rules](https://www.cybertec-postgresql.com/en/postgresql-security-things-to-avoid-in-real-life/)
- [Crunchy Data: PgBouncer TLS](https://www.crunchydata.com/blog/improving-pgbouncer-security-with-tlsssl)
- [Sysdig: Dockerfile Best Practices](https://www.sysdig.com/learn-cloud-native/dockerfile-best-practices)
- [Sysdig: Container Security Best Practices](https://www.sysdig.com/learn-cloud-native/container-security-best-practices)
- [Detectify: Nginx Misconfigurations](https://blog.detectify.com/industry-insights/common-nginx-misconfigurations-that-leave-your-web-server-ope-to-attack/)

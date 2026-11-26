# V.A.U.L.T

**V**erified **A**ssets, **U**sage, **L**ots and **T**racking: a self-hosted, offline-first inventory manager for food, water, supplies, medications, ammunition and preparedness gear. It tracks what you have, where it is, when it expires and how long it will last, and tells you when something needs attention.

- **Image:** `ghcr.io/buguno/vault`
- **Source code and full documentation:** <https://github.com/buguno/vault>
- **Supported architectures:** `linux/amd64` and `linux/arm64` (a 64-bit Raspberry Pi works; 32-bit systems do not)
- **Maintained by:** [buguno](https://github.com/buguno)

> **Security first.** V.A.U.L.T holds sensitive data (medications, ammunition) and speaks plain HTTP. Run it on a network you trust and **never expose it directly to the internet**. To reach it from outside, use a VPN such as WireGuard or Tailscale.

## Tags

| Tag | Meaning |
| --- | --- |
| `latest` | The most recent release. |
| `1.2.3` | An exact release (recommended for production: it never changes). |
| `1.2` | The latest patch of a minor release. |
| `edge` | The `master` branch: newest code, may be unstable. |
| `sha-abc1234` | One exact commit. |

Release tags (`latest`, `1.2.3`, `1.2`) appear when a release is made: the automation opens a release pull request from the commit history, and merging it tags `v1.2.3` and publishes the image. Release candidates such as `1.3.0-rc.1` get only their own tag, never `latest` or `1.3`.

## Quick start

The app needs a **PostgreSQL** database; the image does not include one. The easiest way is Docker Compose, which starts both.

**1. Create a `.env` file** next to the compose file (no quotes around the values):

```bash
SECRET_KEY=paste-a-long-random-value-here
DB_PASSWORD=paste-another-random-value-here
```

Generate good values with:

```bash
echo "SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n')"
echo "DB_PASSWORD=$(openssl rand -hex 24)"
```

**2. Save this as `compose.yaml`:**

```yaml
services:
  db:
    image: postgres:17
    restart: unless-stopped
    environment:
      POSTGRES_USER: vault
      POSTGRES_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD in .env}
      POSTGRES_DB: vault
    volumes:
      - vault-db:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U vault -d vault']
      interval: 5s
      timeout: 3s
      retries: 10

  app:
    image: ghcr.io/buguno/vault:latest
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    ports:
      - '8000:8000'
    environment:
      SECRET_KEY: ${SECRET_KEY:?set SECRET_KEY in .env}
      ALLOWED_HOSTS: localhost,127.0.0.1
      DATABASE_URL: postgres://vault:${DB_PASSWORD}@db:5432/vault
      RUN_MIGRATIONS: '1'
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL

volumes:
  vault-db:
```

**3. Start it and read the first-time setup code:**

```bash
docker compose up -d
docker compose logs app | grep -A3 "first-time setup"
```

**4. Open <http://localhost:8000>.** There are no users yet, so the site asks for the setup code printed in the logs, a username and a password, and creates the administrator. After that the setup page is closed for good.

To open it from a phone or another computer, add the host's address to `ALLOWED_HOSTS` (for example `localhost,192.168.0.10`) and use `http://192.168.0.10:8000`.

## Running with `docker run`

With a PostgreSQL you already have (here on the host, reached by `host.docker.internal`):

```bash
docker run -d --name vault \
  -p 8000:8000 \
  -e SECRET_KEY='a-long-random-value' \
  -e ALLOWED_HOSTS='localhost,192.168.0.10' \
  -e DATABASE_URL='postgres://user:password@host.docker.internal:5432/vault' \
  -e RUN_MIGRATIONS=1 \
  --read-only --tmpfs /tmp \
  --security-opt no-new-privileges:true --cap-drop ALL \
  --restart unless-stopped \
  ghcr.io/buguno/vault:latest

docker logs vault        # the first-time setup code is printed here
```

- **`localhost` inside the container is the container itself**, not your machine. A `DATABASE_URL` that says `localhost` fails with `Connection refused`. Use the database's service name (Compose), `host.docker.internal` (Docker Desktop; on Linux add `--add-host=host.docker.internal:host-gateway`) or the other machine's address.
- On Linux, a PostgreSQL on the host must accept connections from the Docker network (not only from `127.0.0.1`).

## Environment variables

Set them with `-e`, with `environment:` in Compose, or with `--env-file` / `env_file:`. In an env file write `NAME=value` **without quotes**: Docker keeps the quotes as part of the value.

| Variable | Required | Default | What it does |
| --- | --- | --- | --- |
| `SECRET_KEY` | **yes** | | Django's secret key. Use a long random value and keep it private: the first-time setup code is derived from it. Changing it signs everyone out. |
| `DATABASE_URL` | **yes** | | PostgreSQL connection, e.g. `postgres://user:password@host:5432/dbname`. Percent-encode special characters in the password (or use hex). |
| `ALLOWED_HOSTS` | **yes** | | Comma-separated host names and addresses the site answers to, e.g. `localhost,192.168.0.10,vault.local`. A request with any other `Host` is refused (`DisallowedHost`). |
| `RUN_MIGRATIONS` | no | `0` | Set to `1` to apply database migrations every time the container starts. Convenient for a single container; leave it off if you prefer to migrate by hand. |
| `EXPIRY_WARNING_DAYS` | no | `90` | How many days ahead a batch counts as "expiring soon". |
| `CURRENCY_SYMBOL` | no | `R$` | Symbol shown next to prices and values (one currency, no conversion). |
| `ENVIRONMENT` | no | `production` | Already `production` in the image. Only change it for debugging: `development` turns `DEBUG` on. |
| `GUNICORN_BIND` | no | `0.0.0.0:8000` | Address and port inside the container. If you change the port, also change the published port. |
| `GUNICORN_WORKERS` | no | `1` | Worker processes. One is enough for a household and keeps RAM low. |
| `GUNICORN_THREADS` | no | `2` | Threads per worker. |
| `GUNICORN_TIMEOUT` | no | `30` | Worker timeout, in seconds. |
| `GUNICORN_LOG_LEVEL` | no | `info` | `debug`, `info`, `warning`, `error` or `critical`. |

## Data and volumes

The container is **stateless**: it keeps nothing on disk, so there is no volume to mount for it and you can recreate it freely. **All data is in PostgreSQL**, so persist that database (the `vault-db` volume above) and back it up.

The application also makes encrypted backups from its **Settings** page (administrators only): one GnuPG-encrypted file with all the data, protected by a passphrase you type each time and that is never stored. Download it and keep it, with the passphrase, somewhere safe off the machine.

## Users and permissions inside the container

- The app runs as an **unprivileged user** `vault` (uid and gid **10001**), a system account with no home directory, no password and no login shell. It never runs as root.
- The application code belongs to `root` and **nobody can write to it**, so a compromised process cannot change the app.
- The app only writes to `/tmp` (a throwaway directory while making a backup) and to `/dev/shm` (gunicorn's heartbeat). That is why `--read-only --tmpfs /tmp` works, and it is the recommended way to run it.
- It also works with an **arbitrary user id** (`--user 1234:1234`, as some platforms force): everything it needs is world-readable.
- No capabilities are needed: `--cap-drop ALL` and `--security-opt no-new-privileges:true` are safe.

## Health check

The image declares a `HEALTHCHECK` (a TCP connection to the app's port every 30 seconds). `docker ps` shows `healthy` once the app is up, and Compose can wait for it with `depends_on: condition: service_healthy`.

## Ports

| Port | Use |
| --- | --- |
| `8000` | The web interface (HTTP). |

Put a reverse proxy in front only inside a trusted network. The app does not mark cookies as `Secure`, because it is meant for plain HTTP on a LAN.

## Raspberry Pi

The image is built for `arm64`, so it runs on a Raspberry Pi 3, 4, 5 or Zero 2 W with a **64-bit** operating system. It is light by design (one gunicorn worker and PostgreSQL). On a small board, tune PostgreSQL for about 512 MB of RAM (for example `shared_buffers=32MB`, `work_mem=2MB`, `max_connections=20`) and use a good SD card or an SSD.

## Upgrading

1. Export an encrypted backup from the Settings page.
2. Pull the new image and recreate the container:
   ```bash
   docker compose pull app
   docker compose up -d app
   ```
   With `RUN_MIGRATIONS=1` the database is migrated on start. Otherwise run it once by hand: `docker compose run --rm app python manage.py migrate`.
3. Pin an exact tag such as `1.2.3` if you want upgrades to happen only when you decide.

## Useful commands

```bash
docker compose logs -f app                                   # follow the logs
docker compose exec app python manage.py createsuperuser     # another administrator
docker compose exec app python manage.py changepassword NAME # reset a password
docker compose exec app python manage.py migrate             # apply migrations by hand
```

## Building the image yourself

```bash
git clone https://github.com/buguno/vault.git
cd vault
docker build -t vault .

# both architectures (needs buildx and QEMU)
docker buildx build --platform linux/amd64,linux/arm64 -t vault .
```

## License

MIT. See the [LICENSE](https://github.com/buguno/vault/blob/master/LICENSE).

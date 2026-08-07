# docker

`web.Dockerfile` builds the production Next.js application from the pnpm
workspace. From the repository root:

```sh
cp .env.example .env
docker compose -f docker/docker-compose.yml up web
```

The Compose file retains the deferred Postgres service for a future
database-backed phase. The current web application does not connect to it.

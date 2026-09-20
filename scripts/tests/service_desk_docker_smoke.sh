#!/usr/bin/env bash
# Build the real production image with deliberately stale workspace links.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
scratch="$(mktemp -d -t nexus-service-desk-docker.XXXXXX)"
image="nexus-service-desk:smoke-$(basename "$scratch" | tr '[:upper:]' '[:lower:]')"
container_id=""
cleanup() {
  if [[ -n "$container_id" ]]; then docker rm -f "$container_id" >/dev/null; fi
}
trap cleanup EXIT

# Copy tracked source from the working tree, including uncommitted fixes,
# without copying local secrets or installed dependencies.
git ls-files -z service-desk-app | tar --null -T - -cf - | tar -xf - -C "$scratch"
context="$scratch/service-desk-app"
for workspace in apps/web apps/api packages/shared packages/simulation-engine packages/ui; do
  mkdir -p "$context/$workspace/node_modules"
  ln -s ../../../node_modules/.pnpm/stale-host-next/node_modules/next "$context/$workspace/node_modules/next"
done

docker build \
  --build-arg NEXUS_INTEGRATION=1 \
  --build-arg NEXT_PUBLIC_NEXUS_INTEGRATION=1 \
  --build-arg SERVICE_DESK_BASE_PATH=/service-desk \
  -f "$context/docker/web.Dockerfile" -t "$image" "$context"

container_id="$(docker run -d --publish 127.0.0.1::3000 \
  --env NEXUS_INTEGRATION=1 --env NEXT_PUBLIC_NEXUS_INTEGRATION=1 \
  --env SERVICE_DESK_BASE_PATH=/service-desk --env NEXT_PUBLIC_BASE_PATH=/service-desk \
  --health-cmd="node -e \"fetch('http://127.0.0.1:3000/service-desk/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))\"" \
  --health-interval=2s --health-timeout=5s --health-retries=10 "$image")"
port="$(docker port "$container_id" 3000/tcp | sed 's/.*://')"
healthy=false
for attempt in {1..30}; do
  if [[ "$(docker inspect --format '{{.State.Health.Status}}' "$container_id")" == healthy ]]; then
    healthy=true
    break
  fi
  sleep 2
done
if [[ "$healthy" != true ]]; then docker logs "$container_id"; exit 1; fi
payload="$(curl --fail --silent --show-error "http://127.0.0.1:$port/service-desk/api/health")"
python3 scripts/service_desk_contract_gate.py --candidate-root "$REPO_ROOT"
backend_payload="$(python3 -c 'from scripts.service_desk_contract_gate import _python_constant; import json; print(json.dumps({"contract_version": _python_constant("backend/app/services/service_desk_contract.py", "SERVICE_DESK_CONTRACT_VERSION")}))')"
python3 scripts/service_desk_contract_gate.py --backend-json "$backend_payload" --service-desk-json "$payload"
echo "Production image build, stale workspace regression, container health and backend source contract passed: $image"
echo "Build context retained at $scratch"

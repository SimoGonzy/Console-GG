#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings

. /etc/os-release
docker_distro="${ID}"
codename="${VERSION_CODENAME:-}"
if [ "$docker_distro" = "ubuntu" ] || [ "$docker_distro" = "linuxmint" ]; then
  docker_distro="ubuntu"
  codename="${UBUNTU_CODENAME:-$VERSION_CODENAME}"
elif [ "$docker_distro" = "debian" ]; then
  docker_distro="debian"
else
  echo "Distribuzione non gestita automaticamente: ${PRETTY_NAME:-$ID}" >&2
  echo "Installa Docker manualmente, poi esegui: bash deploy/docker-up.sh" >&2
  exit 2
fi

if [ -z "$codename" ]; then
  echo "Codename della distribuzione non rilevato. Controlla /etc/os-release." >&2
  exit 2
fi

if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  sudo curl -fsSL "https://download.docker.com/linux/${docker_distro}/gpg" -o /etc/apt/keyrings/docker.asc
fi
sudo chmod a+r /etc/apt/keyrings/docker.asc

cat <<EOF | sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null
Types: deb
URIs: https://download.docker.com/linux/${docker_distro}
Suites: ${codename}
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

echo
docker --version
docker compose version
echo "Docker pronto. Ora esegui: bash start-linux.sh"

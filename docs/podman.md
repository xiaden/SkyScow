# SkyScow with Podman

Podman can run the same SkyScow image as Docker. Use this guide when you prefer a daemonless or rootless container runtime, especially on Fedora, RHEL, CoreOS, Rocky, AlmaLinux, or similar Linux hosts.

This guide mirrors the minimal SkyScow web UI setup. For the full Docker Compose reference, use the main README and `docker-compose.full.yaml`.

## What this guide covers

- Running the SkyScow web UI with `podman run`
- Keeping OpenCode state, cache, and workspace files in bind mounts
- Loading provider keys from `.env` with `--env-file .env`
- Optionally mounting a runtime-only GitHub token with a Podman secret
- SELinux labels for Fedora/RHEL/CoreOS hosts
- Rootless Podman permission and user namespace notes
- Safe update and recreate behavior

## Prerequisites

Install Podman on the host and run the command from the SkyScow project folder, or from another folder that contains the same `.env.example`, data, cache, and workspace paths.

Copy the environment template and add at least one provider key:

```bash
cp .env.example .env
```

Edit `.env` and set the provider you plan to use, for example `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, or another supported provider variable.

GitHub access is optional. To use a runtime-only GitHub token, create a Podman secret without leaving the token in `.env` or the persistent data mount:

```bash
mkdir -p ./secrets
umask 077
${EDITOR:-vi} ./secrets/github_token
podman secret create github_token ./secrets/github_token
rm ./secrets/github_token
```

The commands below omit the optional secret so the base setup works without GitHub access. For GitHub access, add `--secret github_token,type=mount` before the image name. Podman mounts it read-only at `/run/secrets/github_token`; SkyScow uses it for Git and GitHub CLI operations without copying it into `/home/opencode`.

Podman treats relative bind mount sources as paths relative to the directory where you run `podman`. Missing bind mount sources fail, so create them first.

## Minimal web UI setup

Create the host directories:

```bash
mkdir -p ./data/opencode ./local-cache/opencode ./workspace
```

Run SkyScow:

```bash
podman run -d \
  --name skyscow \
  --restart unless-stopped \
  --shm-size=2g \
  -p 127.0.0.1:4096:4096 \
  -v ./data/opencode:/home/opencode \
  -v ./local-cache/opencode:/home/opencode/.cache/opencode \
  -v ./workspace:/workspace \
  --env-file .env \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  ghcr.io/xiaden/skyscow:latest
```

Open http://localhost:4096. The port is published on the host's loopback interface only, so it is not reachable from other machines.

What the important options do:

- `--shm-size=2g` gives Chromium and browser automation enough shared memory.
- `-p 127.0.0.1:4096:4096` publishes the OpenCode web UI on the host's loopback interface, so it is not reachable from other machines. To expose it remotely, bind a wider interface **and** set `OPENCODE_SERVER_PASSWORD` in `.env` (see the main README's Environment Variables) — an unauthenticated OpenCode server can execute code with your mounted workspace and provider credentials.
- `./data/opencode:/home/opencode` persists OpenCode config, sessions, plugins, and service state.
- `./local-cache/opencode:/home/opencode/.cache/opencode` keeps plugin and package cache on local disk.
- `./workspace:/workspace` mounts your project files.
- `--env-file .env` loads provider keys and optional SkyScow toggles without putting secrets in shell history.
- For GitHub access, add `--secret github_token,type=mount` after creating the Podman secret described above. The mounted file is consumed at `/run/secrets/github_token`; do not add `GITHUB_TOKEN` to `.env`.
- `PUID` and `PGID` tell SkyScow which host UID/GID to use for file ownership inside mounted paths.
- `ghcr.io/xiaden/skyscow:latest` pulls from GitHub Container Registry.

If you use a different host folder, keep the container paths unchanged. `/home/opencode`, `/home/opencode/.cache/opencode`, and `/workspace` are the paths SkyScow expects inside the container.

## SELinux hosts

On SELinux hosts such as Fedora, RHEL, or CoreOS, unlabeled bind mounts can look like permission problems from inside the container. Add `:Z` to each SkyScow bind mount for a private label used by this one container:

```bash
podman run -d \
  --name skyscow \
  --restart unless-stopped \
  --shm-size=2g \
  -p 127.0.0.1:4096:4096 \
  -v ./data/opencode:/home/opencode:Z \
  -v ./local-cache/opencode:/home/opencode/.cache/opencode:Z \
  -v ./workspace:/workspace:Z \
  --env-file .env \
  ghcr.io/xiaden/skyscow:latest
```

Use `:z` only when the same host path must be shared by multiple containers. Do not casually relabel broad system paths or your entire home directory.

## Rootless Podman and permissions

Rootless Podman runs containers inside a user namespace. That is one of the main reasons people choose Podman, but it also means bind mount ownership can behave differently from Docker.

Check these if files are unexpectedly owned or blocked:

- Your user has ranges in `/etc/subuid` and `/etc/subgid`.
- `PUID=$(id -u)` and `PGID=$(id -g)` match the host user that should own files in `./workspace`.
- The host paths exist before running the container.
- SELinux hosts use `:Z` or `:z` labels as described above.

Some rootless setups use custom user namespace modes such as `--userns=keep-id`. Do not add that flag by default for SkyScow; it changes how the container process user is mapped. Use it only after testing that it matches your host policy and does not interfere with SkyScow's `PUID`/`PGID` remapping.

## Updating SkyScow

Pull the latest image:

```bash
podman pull ghcr.io/xiaden/skyscow:latest
```

Then recreate the container:

```bash
podman stop skyscow
podman rm skyscow
```

Run the `podman run` command again. Your data stays in `./data/opencode`, `./local-cache/opencode`, and `./workspace`.

Do not use `podman start skyscow` as an update path. It restarts the existing container with the old image, environment variables, ports, and mount settings.

`--restart unless-stopped` restarts the container after normal exits unless you explicitly stopped it. Reboot persistence depends on Podman's `podman-restart.service`. If you later manage SkyScow through systemd or Quadlet, use systemd's `Restart=` behavior instead of Podman's `--restart` flag.

## Troubleshooting

### Permission denied on mounted files

Verify `PUID`, `PGID`, host directory ownership, and rootless user namespace setup:

```bash
id -u
id -g
```

Make sure those values match the `PUID` and `PGID` passed to the container. If rootless Podman still maps ownership unexpectedly, check `/etc/subuid` and `/etc/subgid` for your user.

### SELinux AVC or denied access

Add `:Z` to the three bind mounts for a private container label:

```bash
-v ./data/opencode:/home/opencode:Z \
-v ./local-cache/opencode:/home/opencode/.cache/opencode:Z \
-v ./workspace:/workspace:Z
```

Use `:z` only when multiple containers must share the same host path.

### Port 4096 already in use

Publish SkyScow on a different host port while keeping the container port at `4096`:

```bash
-p 127.0.0.1:4097:4096
```

Then open http://localhost:4097.

### Chromium or browser automation fails

Make sure the command includes:

```bash
--shm-size=2g
```

Without enough `/dev/shm`, Chromium can crash or produce broken automation results.

### Environment variables did not change

Changing `.env` does not update an already-created container. Stop and remove the container, then run the command again so Podman creates a new container with the updated environment.

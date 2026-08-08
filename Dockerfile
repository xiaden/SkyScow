# ==============================================================================
# HolyCode - Pre-configured Docker Environment for OpenCode
# https://github.com/xiaden/HolyCode
# ==============================================================================

FROM node:trixie-slim

LABEL org.opencontainers.image.source="https://github.com/xiaden/HolyCode"

# ------------------------------------------------------------------------------
# Versions
# ------------------------------------------------------------------------------

ARG S6_OVERLAY_VERSION=3.2.3.0
ARG LAZYGIT_VERSION=0.62.1
ARG DELTA_VERSION=0.19.2
ARG EZA_VERSION=0.23.4
ARG OPENCODE_VERSION=1.17.18
ARG RGA_VERSION=0.10.10
ARG DIFFTASTIC_VERSION=0.69.0
ARG TARGETARCH

# ------------------------------------------------------------------------------
# Runtime environment
# ------------------------------------------------------------------------------

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    CHROME_PATH=/usr/bin/chromium \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    OPENCODE_DISABLE_AUTOUPDATE=true \
    OPENCODE_DISABLE_TERMINAL_TITLE=true \
    PATH="/home/opencode/.local/bin:${PATH}"

# ------------------------------------------------------------------------------
# System packages
#
# Keep the image capable of:
#   - operating on arbitrary repositories
#   - compiling native dependencies
#   - debugging processes/network/files
#   - using Git/GitHub/SSH
#   - running Python projects
#   - running Chromium headlessly
#   - using AFT semantic search
#
# Project-specific frameworks/toolchains belong to the project.
# ------------------------------------------------------------------------------

RUN set -eux; \
    \
    # Bootstrap requirements for external apt repositories.
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl; \
    \
    # GitHub CLI repository.
    curl -fsSL \
        https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg; \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list; \
    \
    apt-get update; \
    apt-get install -y --no-install-recommends \
    # Archive / file utilities
    xz-utils unzip zip tar \
    file rsync \
    # Repository / shell essentials
    git git-lfs gh openssh-client git-sizer tokei \
    sudo jq tree less vim tmux wget \
    # Search / navigation
    ripgrep fd-find fzf bat \
    universal-ctags cscope cloc bear gron \
    libxml2-utils xmlstarlet poppler-utils jc \
    # Process / network diagnostics
    htop procps psmisc iproute2 \
    lsof strace netcat-openbsd dnsutils \
    socat openssl \
    # Native project builds
    build-essential pkg-config \
    # Python project support
    python3 python3-pip python3-venv python-is-python3 \
    # Database inspection / clients
    sqlite3 postgresql-client redis-tools \
    # Document / media tooling
    pandoc ffmpeg imagemagick \
    # Headless browser
    chromium chromium-sandbox fonts-noto-core \
    fonts-noto-color-emoji fonts-inter fonts-liberation2 fonts-dejavu-core \
    # AFT semantic search runtime
    libonnxruntime1.21 \
    # Code / shell quality
    shellcheck shfmt yq \
    # Benchmarking / automation
    hyperfine entr inotify-tools \
    # Unix utility upgrades
    moreutils bc \
    # Filesystem / permissions debugging
    acl attr;\
    \
    # Rename stock node UID/GID 1000 account.
    usermod -l opencode -d /home/opencode -m node; \
    groupmod -n opencode node; \
    printf '%s\n' 'opencode ALL=(ALL) NOPASSWD:ALL' \
        > /etc/sudoers.d/opencode; \
    chmod 0440 /etc/sudoers.d/opencode; \
    \
    # Debian packages bat as batcat.
    ln -sf /usr/bin/batcat /usr/local/bin/bat; \
    \
    # Chromium sandbox validation.
    chmod u+s /usr/lib/chromium/chrome-sandbox; \
    test -u /usr/lib/chromium/chrome-sandbox; \
    \
    # Chromium security/version floor.
    chromium_version="$(dpkg-query -W -f='${Version}' chromium)"; \
    chromium_sandbox_version="$(dpkg-query -W -f='${Version}' chromium-sandbox)"; \
    printf '%s\n' "$chromium_version" \
        | grep -Eq '^(15[1-9]|1[6-9][0-9]|[2-9][0-9]{2})\.'; \
    test "$chromium_version" = "$chromium_sandbox_version"; \
    \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Native standalone tools
#
# These don't belong to individual projects and are useful enough to keep in
# the base environment.
# ------------------------------------------------------------------------------

RUN set -eux; \
    case "$TARGETARCH" in \
        amd64) \
            S6_ARCH="x86_64"; \
            LAZYGIT_ARCH="x86_64"; \
            DELTA_ARCH="amd64"; \
            EZA_ARCH="x86_64"; \
            ;; \
        arm64) \
            S6_ARCH="aarch64"; \
            LAZYGIT_ARCH="arm64"; \
            DELTA_ARCH="arm64"; \
            EZA_ARCH="aarch64"; \
            ;; \
        *) \
            echo "Unsupported TARGETARCH: $TARGETARCH" >&2; \
            exit 1; \
            ;; \
    esac; \
    \
    # s6-overlay.
    curl -fsSL \
        -o /tmp/s6-overlay-noarch.tar.xz \
        "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz"; \
    curl -fsSL \
        -o /tmp/s6-overlay-arch.tar.xz \
        "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${S6_ARCH}.tar.xz"; \
    tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz; \
    tar -C / -Jxpf /tmp/s6-overlay-arch.tar.xz; \
    \
    # lazygit.
    curl -fsSL \
        -o /tmp/lazygit.tar.gz \
        "https://github.com/jesseduffield/lazygit/releases/download/v${LAZYGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_Linux_${LAZYGIT_ARCH}.tar.gz"; \
    tar -C /usr/local/bin \
        -xzf /tmp/lazygit.tar.gz \
        lazygit; \
    \
    # git-delta.
    curl -fsSL \
        -o /tmp/delta.deb \
        "https://github.com/dandavison/delta/releases/download/${DELTA_VERSION}/git-delta_${DELTA_VERSION}_${DELTA_ARCH}.deb"; \
    dpkg -i /tmp/delta.deb; \
    \
    # eza.
    curl -fsSL \
        -o /tmp/eza.tar.gz \
        "https://github.com/eza-community/eza/releases/download/v${EZA_VERSION}/eza_${EZA_ARCH}-unknown-linux-gnu.tar.gz"; \
    tar -C /usr/local/bin \
        -xzf /tmp/eza.tar.gz; \
    \
    rm -f \
        /tmp/s6-overlay-noarch.tar.xz \
        /tmp/s6-overlay-arch.tar.xz \
        /tmp/lazygit.tar.gz \
        /tmp/delta.deb \
        /tmp/eza.tar.gz

# ------------------------------------------------------------------------------
# Code exploration binaries
# ------------------------------------------------------------------------------

RUN set -eux; \
    case "$TARGETARCH" in \
        amd64) \
            RGA_TARGET="x86_64-unknown-linux-musl"; \
            DIFFT_TARGET="x86_64-unknown-linux-gnu"; \
            ;; \
        arm64) \
            RGA_TARGET="aarch64-unknown-linux-gnu"; \
            DIFFT_TARGET="aarch64-unknown-linux-gnu"; \
            ;; \
        *) \
            echo "Unsupported TARGETARCH: $TARGETARCH" >&2; \
            exit 1; \
            ;; \
    esac; \
    \
    mkdir -p /tmp/rga /tmp/difftastic; \
    \
    # ripgrep-all
    curl -fsSL --retry 3 \
        -o /tmp/rga.tar.gz \
        "https://github.com/phiresky/ripgrep-all/releases/download/v${RGA_VERSION}/ripgrep_all-v${RGA_VERSION}-${RGA_TARGET}.tar.gz"; \
    tar -xzf /tmp/rga.tar.gz -C /tmp/rga; \
    \
    for binary in rga rga-preproc rga-fzf rga-fzf-open; do \
        path="$(find /tmp/rga -type f -name "$binary" -print -quit)"; \
        test -n "$path"; \
        install -m 0755 "$path" "/usr/local/bin/$binary"; \
    done; \
    \
    # difftastic
    curl -fsSL --retry 3 \
        -o /tmp/difftastic.tar.gz \
        "https://github.com/Wilfred/difftastic/releases/download/${DIFFTASTIC_VERSION}/difft-${DIFFT_TARGET}.tar.gz"; \
    tar -xzf /tmp/difftastic.tar.gz -C /tmp/difftastic; \
    \
    path="$(find /tmp/difftastic -type f -name difft -print -quit)"; \
    test -n "$path"; \
    install -m 0755 "$path" /usr/local/bin/difft; \
    \
    # Build-time sanity check.
    rga --version; \
    difft --version; \
    \
    rm -rf \
        /tmp/rga \
        /tmp/rga.tar.gz \
        /tmp/difftastic \
        /tmp/difftastic.tar.gz

# ------------------------------------------------------------------------------
# HolyCode Python runtime dependencies
#
# Do NOT turn system Python into a generic project environment.
# Repositories being worked on should install their own dependencies.
# ------------------------------------------------------------------------------

RUN python3 -m pip install \
        --no-cache-dir \
        --break-system-packages \
        "mcp>=1,<2" \
        "tiktoken>=0,<1";

# ------------------------------------------------------------------------------
# Core Node runtime
#
# OpenCode is pinned intentionally.
# Sleev follows current releases.
# pnpm is provided as a general package manager.
#
# AFT's OpenCode plugin is configured through opencode.json, so only the AFT
# binary itself is installed globally here.
#
# unique-names-generator remains because HolyCode's local background-agent
# plugin imports it directly.
# ------------------------------------------------------------------------------

RUN set -eux; \
    npm install -g \
        "opencode-ai@${OPENCODE_VERSION}" \
        sleev \
        pnpm@11 \
        unique-names-generator \
        @ast-grep/cli; \
    \
    npm install -g \
        --legacy-peer-deps \
        @cortexkit/aft; \
    \
    # Preserve the real Sleev executable behind HolyCode's wrapper.
    mv /usr/local/bin/sleev /usr/local/bin/sleev.real; \
    \
    npm cache clean --force

# ------------------------------------------------------------------------------
# HolyCode configuration
#
# Copy configuration as a unit instead of creating a layer for every directory.
# ------------------------------------------------------------------------------

COPY config/ /usr/local/share/holycode/

COPY scripts/entrypoint.sh \
     scripts/bootstrap.sh \
     scripts/sleev-wrapper.sh \
     /tmp/holycode-scripts/

COPY s6-overlay/s6-rc.d/ /etc/s6-overlay/s6-rc.d/

RUN set -eux; \
    \
    # Executables.
    install -m 0755 \
        /tmp/holycode-scripts/entrypoint.sh \
        /usr/local/bin/entrypoint.sh; \
    install -m 0755 \
        /tmp/holycode-scripts/bootstrap.sh \
        /usr/local/bin/bootstrap.sh; \
    install -m 0755 \
        /tmp/holycode-scripts/sleev-wrapper.sh \
        /usr/local/bin/sleev; \
    rm -rf /tmp/holycode-scripts; \
    \
    # Xvfb is no longer used. Chromium runs natively headless.
    rm -rf /etc/s6-overlay/s6-rc.d/xvfb; \
    \
    # s6 services.
    chmod +x \
        /etc/s6-overlay/s6-rc.d/opencode/run \
        /etc/s6-overlay/s6-rc.d/sleev/run \
        /etc/s6-overlay/s6-rc.d/sleev/finish; \
    \
    mkdir -p /etc/s6-overlay/s6-rc.d/user/contents.d; \
    touch \
        /etc/s6-overlay/s6-rc.d/user/contents.d/opencode \
        /etc/s6-overlay/s6-rc.d/user/contents.d/sleev

# ------------------------------------------------------------------------------
# Runtime
# ------------------------------------------------------------------------------

WORKDIR /workspace

EXPOSE 4096

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=30s \
    --retries=3 \
    CMD curl -sf http://localhost:4096/ || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
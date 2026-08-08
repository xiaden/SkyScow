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
ARG TARGETARCH

# ------------------------------------------------------------------------------
# Runtime environment
# ------------------------------------------------------------------------------

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    DISPLAY=:99 \
    DBUS_SESSION_BUS_ADDRESS=disabled: \
    CHROME_PATH=/usr/bin/chromium \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    CHROMIUM_FLAGS="--disable-gpu --disable-dev-shm-usage" \
    OPENCODE_DISABLE_AUTOUPDATE=true \
    OPENCODE_DISABLE_TERMINAL_TITLE=true \
    PATH="/home/opencode/.local/bin:${PATH}"

# ------------------------------------------------------------------------------
# System packages
#
# Includes:
#   - core shell/dev tools
#   - Python
#   - database clients
#   - Chromium/Xvfb/fonts
#   - ONNX Runtime for AFT
#   - GitHub CLI
#   - locale/sudo
# ------------------------------------------------------------------------------

RUN set -eux; \
    # Bootstrap packages required to add external apt repositories.
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl; \
    # GitHub CLI repository.
    curl -fsSL \
        https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg; \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list; \
    \
    apt-get install -y --no-install-recommends \
        \
        xz-utils \
        locales \
        sudo \
        \
        git \
        wget \
        jq \
        unzip \
        zip \
        tar \
        tree \
        less \
        vim \
        tmux \
        openssh-client \
        \
        ripgrep \
        fd-find \
        fzf \
        bat \
        bubblewrap \
        \
        htop \
        procps \
        iproute2 \
        lsof \
        strace \
        \
        build-essential \
        pkg-config \
        \
        postgresql-client \
        redis-tools \
        sqlite3 \
        \
        python3 \
        python3-pip \
        python3-venv \
        python-is-python3 \
        pyenv \
        autoflake \
        \
        pandoc \
        ffmpeg \
        imagemagick \
        \
        gh \
        \
        chromium \
        chromium-sandbox \
        xvfb \
        \
        fonts-inter \
        fonts-liberation2 \
        fonts-dejavu-core \
        fonts-noto-core \
        fonts-noto-color-emoji \
        \
        libonnxruntime1.21; \
    \
    # Locale.
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen; \
    locale-gen; \
    \
    # Rename the stock node UID/GID 1000 account.
    usermod -l opencode -d /home/opencode -m node; \
    groupmod -n opencode node; \
    printf '%s\n' 'opencode ALL=(ALL) NOPASSWD:ALL' \
        > /etc/sudoers.d/opencode; \
    chmod 0440 /etc/sudoers.d/opencode; \
    \
    # Debian names bat "batcat".
    ln -sf /usr/bin/batcat /usr/local/bin/bat; \
    \
    # Sandbox helpers.
    chmod u+s /usr/bin/bwrap; \
    chmod u+s /usr/lib/chromium/chrome-sandbox; \
    test -u /usr/lib/chromium/chrome-sandbox; \
    \
    # Chromium security/version guard.
    chromium_version="$(dpkg-query -W -f='${Version}' chromium)"; \
    chromium_sandbox_version="$(dpkg-query -W -f='${Version}' chromium-sandbox)"; \
    printf '%s\n' "$chromium_version" \
        | grep -Eq '^(15[1-9]|1[6-9][0-9]|[2-9][0-9]{2})\.'; \
    test "$chromium_version" = "$chromium_sandbox_version"; \
    \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Standalone native tools
#
# s6-overlay, lazygit, delta and eza have different archive naming schemes
# between amd64 and arm64, so handle architecture once here.
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
    tar -C /usr/local/bin -xzf /tmp/lazygit.tar.gz lazygit; \
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
    tar -C /usr/local/bin -xzf /tmp/eza.tar.gz; \
    \
    rm -f \
        /tmp/s6-overlay-noarch.tar.xz \
        /tmp/s6-overlay-arch.tar.xz \
        /tmp/lazygit.tar.gz \
        /tmp/delta.deb \
        /tmp/eza.tar.gz

# ------------------------------------------------------------------------------
# Python tooling
#
# Chromium is supplied by Debian. Playwright itself is installed here; callers
# using Python Playwright should explicitly select /usr/bin/chromium where needed.
# ------------------------------------------------------------------------------

RUN python3 -m pip install \
    --no-cache-dir \
    --break-system-packages \
    "playwright>=1,<2" \
    "requests>=2,<3" \
    "httpx>=0.28,<1" \
    "beautifulsoup4>=4,<5" \
    "lxml>=6,<7" \
    "Pillow>=12,<13" \
    "openpyxl>=3,<4" \
    "python-docx>=1,<2" \
    "pandas>=3,<4" \
    "numpy>=2.5,<3" \
    "matplotlib>=3.11,<4" \
    "seaborn>=0.13,<1" \
    "rich>=15,<16" \
    "click>=8,<9" \
    "tqdm>=4,<5" \
    "apprise>=1,<2" \
    "jinja2>=3,<4" \
    "pyyaml>=6,<7" \
    "python-dotenv>=1,<2" \
    "markdown>=3,<4" \
    "fastapi>=0.139,<1" \
    "uvicorn>=0.51,<1" \
    && rm -f /usr/local/bin/dotenv

# ------------------------------------------------------------------------------
# Node / OpenCode tooling
#
# OpenCode remains exactly pinned because it is the runtime itself.
# General developer tools follow compatible major/minor release families.
# ------------------------------------------------------------------------------

RUN set -eux; \
    npm install -g \
        "opencode-ai@${OPENCODE_VERSION}" \
        sleev \
        unique-names-generator \
        \
        typescript@7 \
        tsx@4 \
        pnpm@11 \
        vite@8 \
        esbuild@0.28 \
        eslint@10 \
        prettier@3 \
        serve@14 \
        nodemon@3 \
        concurrently@10 \
        dotenv-cli@11 \
        wrangler@4 \
        vercel@58 \
        netlify-cli@27 \
        pm2@7 \
        prisma@7 \
        drizzle-kit@0.31 \
        lighthouse@13 \
        @lhci/cli@0.15 \
        sharp-cli@5 \
        json-server@0.17 \
        http-server@14; \
    \
    # AFT currently needs legacy peer dependency resolution.
    npm install -g --legacy-peer-deps \
        @cortexkit/aft \
        @cortexkit/aft-opencode; \
    \
    # Preserve the real Sleev CLI behind HolyCode's wrapper.
    mv /usr/local/bin/sleev /usr/local/bin/sleev.real; \
    \
    npm cache clean --force

# ------------------------------------------------------------------------------
# HolyCode configuration
# ------------------------------------------------------------------------------

COPY scripts/entrypoint.sh \
     scripts/bootstrap.sh \
     scripts/sleev-wrapper.sh \
     /tmp/holycode-scripts/

COPY config/ /usr/local/share/holycode/

COPY s6-overlay/s6-rc.d/ /etc/s6-overlay/s6-rc.d/

RUN set -eux; \
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
    chmod +x \
        /etc/s6-overlay/s6-rc.d/opencode/run \
        /etc/s6-overlay/s6-rc.d/xvfb/run \
        /etc/s6-overlay/s6-rc.d/sleev/run \
        /etc/s6-overlay/s6-rc.d/sleev/finish; \
    mkdir -p /etc/s6-overlay/s6-rc.d/user/contents.d; \
    touch \
        /etc/s6-overlay/s6-rc.d/user/contents.d/opencode \
        /etc/s6-overlay/s6-rc.d/user/contents.d/xvfb \
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
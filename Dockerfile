# ==============================================================================
# HolyCode - Pre-configured Docker Environment for OpenCode
# https://github.com/xiaden/HolyCode
# ==============================================================================

FROM node:trixie-slim

# ------------------------------------------------------------------------------
# Versions
# ------------------------------------------------------------------------------

ARG S6_OVERLAY_VERSION=3.2.3.0
ARG LAZYGIT_VERSION=0.62.1
ARG DELTA_VERSION=0.19.2
ARG EZA_VERSION=0.23.4
ARG OPENCODE_VERSION=1.17.18
ARG SLEEV_VERSION=1.6.16
ENV SLEEV_VERSION=${SLEEV_VERSION}
ARG HOLYCODE_VERSION=0.0.0
ENV HOLYCODE_VERSION=${HOLYCODE_VERSION}
ARG DEEPSEEK_TOKENIZER_REVISION=7872f01b1d1fe23eabc4c98b48bffcef5a386062
ARG DEEPSEEK_TOKENIZER_SHA256=8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf
ARG RGA_VERSION=0.10.10
ARG DIFFTASTIC_VERSION=0.69.0
ARG TARGETARCH

# OCI metadata is surfaced by GitHub Container Registry on the package page.
LABEL \
    org.opencontainers.image.source="https://github.com/xiaden/HolyCode" \
    org.opencontainers.image.description="Pre-configured OpenCode development environment with 50+ dev tools and headless Chromium" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.version="${HOLYCODE_VERSION}"

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
# Sleev gateway (pinned, architecture-specific, verified)
#
# The gateway is a native binary shipped in the image at build time under a
# versioned path and run by s6. At startup it is synchronized into the
# persistent volume (see scripts/sleev-gateway-sync.sh). An override through
# SLEEV_VERSION fetches and verifies the matching official CLI and gateway
# archives before s6 starts.
# ------------------------------------------------------------------------------

RUN set -eux; \
    case "$TARGETARCH" in \
        amd64) \
            GATEWAY_ARCH="x64"; \
            GATEWAY_SHA256="1d86668199689c22c08e6f65b0af94f2e4ba337c090ec368b2cf81c5412a7f93"; \
            GATEWAY_SIZE="27371540"; \
            ;; \
        arm64) \
            GATEWAY_ARCH="arm64"; \
            GATEWAY_SHA256="d26f6b9b8c34cbd31c7d9fadc861eb1cc9e4007a59268bdcf0604a50b8612e1a"; \
            GATEWAY_SIZE="25551336"; \
            ;; \
        *) \
            echo "Unsupported TARGETARCH: $TARGETARCH" >&2; \
            exit 1; \
            ;; \
    esac; \
    \
    # Download the official gateway archive.
    curl -fsSL \
        -o /tmp/sleeve-gateway.tar.gz \
        "https://storage.googleapis.com/sleeve-releases/gateway/${SLEEV_VERSION}/sleeve-gateway-linux-${GATEWAY_ARCH}.tar.gz"; \
    \
    # Verify SHA256 before extraction; fail the build on mismatch.
    echo "${GATEWAY_SHA256}  /tmp/sleeve-gateway.tar.gz" | sha256sum -c -; \
    \
    # Optional size guard against truncated/mismatched downloads.
    test "$(stat -c %s /tmp/sleeve-gateway.tar.gz)" -eq "$GATEWAY_SIZE"; \
    \
    # Extract the architecture-specific binary and legal files into the
    # image-shipped versioned directory.
    mkdir -p "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}"; \
    tar -xzf /tmp/sleeve-gateway.tar.gz \
        -C "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}" \
        "sleeve-gateway-linux-${GATEWAY_ARCH}" \
        LICENSE.md EULA.md THIRD_PARTY_NOTICES.md; \
    \
    # Rename the binary to a consistent name for the synchronizer.
    install -m 0755 \
        "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/sleeve-gateway-linux-${GATEWAY_ARCH}" \
        "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/sleeve-gateway"; \
    rm -f \
        "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/sleeve-gateway-linux-${GATEWAY_ARCH}"; \
    \
    # Legal files, non-secret, restrictive metadata.
    chmod 0644 \
        "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/LICENSE.md" \
        "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/EULA.md" \
        "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/THIRD_PARTY_NOTICES.md"; \
    \
    # Extraction integrity checks.
    test -x "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/sleeve-gateway"; \
    test -s "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/LICENSE.md"; \
    test -s "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/EULA.md"; \
    test -s "/usr/local/share/holycode/sleev/gateway/${SLEEV_VERSION}/THIRD_PARTY_NOTICES.md"; \
    ln -s "${SLEEV_VERSION}" \
        "/usr/local/share/holycode/sleev/gateway/packaged"; \
    # Do not leave the downloaded archive in the build layer.
    rm -f /tmp/sleeve-gateway.tar.gz

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
        "tiktoken>=0,<1" \
        "tokenizers>=0.23,<1";

# The tokenizer is shipped locally so context measurements are deterministic
# and do not require runtime access to Hugging Face.
RUN set -eux; \
    tokenizer_dir=/usr/local/share/holycode/tokenizers/deepseek-v4-flash-0731; \
    mkdir -p "$tokenizer_dir"; \
    curl -fsSL --retry 3 \
        -o "$tokenizer_dir/tokenizer.json" \
        "https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/resolve/${DEEPSEEK_TOKENIZER_REVISION}/tokenizer.json?download=true"; \
    printf '%s  %s\n' \
        "$DEEPSEEK_TOKENIZER_SHA256" \
        "$tokenizer_dir/tokenizer.json" | sha256sum -c -; \
    chmod 0644 "$tokenizer_dir/tokenizer.json"; \
    python3 -c 'from tokenizers import Tokenizer; t = Tokenizer.from_file("/usr/local/share/holycode/tokenizers/deepseek-v4-flash-0731/tokenizer.json"); assert t.encode("HolyCode").ids';

# ------------------------------------------------------------------------------
# Core Node runtime
#
# OpenCode is pinned intentionally.
# Sleev defaults to the same version as the gateway shipped below, so the CLI
# and native gateway artifact stay in lockstep. SLEEV_VERSION may be overridden
# at runtime; startup then fetches and verifies both matching artifacts.
# pnpm is provided as a general package manager.
#
# AFT's OpenCode plugin is configured through opencode.json, so only the AFT
# binary itself is installed globally here.
#
# unique-names-generator remains because HolyCode's local background-agent
# plugin imports it directly.
# ------------------------------------------------------------------------------

# These packages have reviewed postinstall scripts; other dependency scripts stay blocked.
RUN set -eux; \
    npm install -g \
        --allow-scripts=opencode-ai,sleev,@ast-grep/cli \
        "opencode-ai@${OPENCODE_VERSION}" \
        "sleev@${SLEEV_VERSION}" \
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
     scripts/sleev-gateway-sync.sh \
     /tmp/holycode-scripts/

COPY s6-overlay/s6-rc.d/ /etc/s6-overlay/s6-rc.d/

RUN set -eux; \
    manifest=/usr/local/share/holycode/bootstrap-manifest.tsv; \
    { \
        printf 'schema\t1\n'; \
        printf 'version\t%s\n' "$HOLYCODE_VERSION"; \
        { \
            printf '%s\n' /usr/local/share/holycode/opencode.json; \
            find \
                /usr/local/share/holycode/plugins \
                /usr/local/share/holycode/agents \
                /usr/local/share/holycode/skills \
                /usr/local/share/holycode/tools \
                /usr/local/share/holycode/commands \
                -type f -print; \
        } | LC_ALL=C sort | while IFS= read -r source; do \
            path="${source#/usr/local/share/holycode/}"; \
            hash="$(sha256sum "$source" | cut -d' ' -f1)"; \
            printf 'file\t%s\t%s\n' "$path" "$hash"; \
        done; \
    } > "$manifest"; \
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
    install -m 0755 \
        /tmp/holycode-scripts/sleev-gateway-sync.sh \
        /usr/local/bin/sleev-gateway-sync.sh; \
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

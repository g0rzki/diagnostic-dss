FROM debian:bookworm-slim

ARG TAILWIND_VERSION=v4.3.3

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN case "$(uname -m)" in \
        x86_64) arch=x64 ;; \
        aarch64) arch=arm64 ;; \
        *) echo "Nieobsługiwana architektura: $(uname -m)" && exit 1 ;; \
    esac \
    && curl -fsSL -o /usr/local/bin/tailwindcss \
        "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-${arch}" \
    && chmod +x /usr/local/bin/tailwindcss

WORKDIR /app

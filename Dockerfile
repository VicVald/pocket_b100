# ----------------------------------------------------------------------
# ESTÁGIO 0: FRONTEND BUILDER (Build React app)
# ----------------------------------------------------------------------
FROM node:18-alpine as frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ----------------------------------------------------------------------
# ESTÁGIO 1: BUILDER (Instala dependências do OS e Python)
# Objetivo: Criar o Venv com todas as dependências instaladas
# ----------------------------------------------------------------------
FROM python:3.13-slim-bookworm as builder

# Define o diretório de trabalho DENTRO DO CONTAINER
WORKDIR /app

# 1. Instalação do uv: Copia os binários pré-compilados (uv e uvx).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /usr/local/bin/

# Instalação das dependências do OS para compilação (dentro do container)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        zlib1g-dev libjpeg-dev \
        curl \
        ca-certificates \
        pkg-config \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Instala Rust toolchain (necessário para compilar pacotes Python que usam Rust extensions)
# Installed only in the builder stage so final image stays small.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copia apenas os arquivos de dependência
COPY pyproject.toml uv.lock ./

# Cria e popula o virtual environment (venv)
# O cache do uv fica isolado (via mount) e a instalação é rápida.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Copia o código da aplicação
COPY . .

# ----------------------------------------------------------------------
# ESTÁGIO 2: PRODUCTION (Imagem de runtime - Mínima e segura)
# Objetivo: Copiar artefatos, criar um usuário seguro e iniciar a aplicação.
# ----------------------------------------------------------------------
FROM python:3.12-slim-bookworm as production

# Define o diretório de trabalho DENTRO DO CONTAINER
WORKDIR /app

# 1. Instala dependências de OS APENAS de RUNTIME
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        zlib1g libjpeg62-turbo \
        build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 2. Copia o binário do uv do builder para usar uv run
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /usr/local/bin/uvx /usr/local/bin/uvx

# 3. Copia o venv e o código da app do estágio 'builder' (ainda como root)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# 3.1. Copia o frontend build do estágio frontend-builder
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# 4. CRIAÇÃO E CONFIGURAÇÃO DE USUÁRIO (CORRIGIDO)
#    --create-home: Permite que o usuário tenha um local de trabalho, resolvendo o erro 13.
RUN useradd --create-home --uid 1000 appuser

#    Transfere a propriedade de /app e todos os seus conteúdos (incluindo o venv)
#    para o appuser, dando a ele as permissões necessárias.
RUN chown -R appuser:appuser /app

# 5. Define o Usuário não-root
USER appuser

# 6. Configura o PATH (dentro do container)
ENV PATH="/app/.venv/bin:$PATH"

# Define a porta
EXPOSE 8000

# 7. Define o comando de inicialização
CMD uv run uvicorn api:app --host 0.0.0.0 --port 8000

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build tools, libpq, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application source code
COPY configs/ ./configs/
COPY services/ ./services/
COPY infra/ ./infra/

EXPOSE 8000

CMD ["uvicorn", "services.gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]

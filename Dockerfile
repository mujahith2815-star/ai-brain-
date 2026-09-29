# =========================================================================
# P.H.A.S.S SPHERE v8.0 ? Multi-Stage Containerized Runtime & Builder
# =========================================================================

# Stage 1: Build Environment
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     curl     git     ffmpeg     libasound2-dev     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user pyinstaller

COPY . .

# Build standalone executable
RUN python build.py --clean

# Stage 2: Final Minimal Runtime Environment
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg     libasound2     curl     procps     && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy project workspace
COPY . .

# Copy standalone binary
COPY --from=builder /app/dist/phass_sphere /usr/local/bin/phass_sphere

EXPOSE 8080 8999

ENV PHASS_ENV=production
ENV PYTHONUNBUFFERED=1

CMD ["python", "run_model_chat.py"]
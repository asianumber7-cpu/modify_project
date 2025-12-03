# ---------------------------------------------------
# AI Service Module Dockerfile (Optimized)
# 위치: ./ai-service/Dockerfile
# ---------------------------------------------------

# 1. Builder Stage
FROM python:3.11.14-slim AS builder

# [최적화 1] 빌드 필수 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# pip 자체 업그레이드 (먼저 실행하여 캐시 활용)
RUN pip install --upgrade pip setuptools wheel

# [최적화 2] 가장 무거운 PyTorch를 먼저 단독 설치 (캐시 레이어 생성)
# requirements.txt가 바뀌어도 이 줄은 캐시되어 다시 실행되지 않음 (약 3~5분 절약)
# GPU(CUDA) 버전이 필요하면 아래 줄 그대로 사용. 
# 만약 개발용이라 CPU만 필요하다면 끝에 '--index-url https://download.pytorch.org/whl/cpu' 추가 추천
RUN pip install --no-cache-dir torch==2.1.2 

# [최적화 3] 나머지 의존성 설치
# requirements.txt에서 torch==2.1.2 줄은 있어도 되고 없어도 됨 (이미 설치됨으로 넘어감)
COPY requirements.txt .

# --default-timeout 옵션: 네트워크 느릴 때 끊김 방지
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# ---------------------------------------------------

# 2. Runner Stage
FROM python:3.11.14-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul \
    HF_HOME=/app/models_cache \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 런타임 필수 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Builder에서 생성한 가상환경 복사
COPY --from=builder /opt/venv /opt/venv

# 유저 설정
RUN addgroup --system appgroup && adduser --system --group appuser
RUN mkdir -p /app/models_cache && chown -R appuser:appgroup /app

# 소스 코드 복사 (가장 자주 바뀌므로 맨 마지막에 배치)
COPY . .
RUN chown -R appuser:appgroup /app

USER appuser
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
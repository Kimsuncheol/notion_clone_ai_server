FROM python:3.12-slim

# 시스템 의존성(필요 시 추가)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 분리 캐시 최적화
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# App Runner 기본 포트 8080
ENV PORT=8080
EXPOSE 8080

# Uvicorn 실행 (프로세스 1개면 충분, 필요 시 --workers 조정)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
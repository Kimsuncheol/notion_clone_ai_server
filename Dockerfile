FROM python:3.12-slim

# 빌드에 자주 필요한 도구들 (grpcio, orjson 등 대비)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl git libffi-dev libssl-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip 최신화 + 필수 휠 도구 설치
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# 소스
COPY . .

ENV PORT=8080
EXPOSE 8080

# main.py가 리포 루트에 있음
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
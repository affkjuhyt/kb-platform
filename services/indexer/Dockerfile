FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv && uv pip install --system -r requirements.txt

COPY . ./

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

# AgentCore Runtime: linux/arm64, port 8080, POST /invocations, GET /ping
FROM --platform=linux/arm64 python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aftermess ./aftermess
COPY data/aftermess/directory.json ./data/aftermess/directory.json
COPY data/aftermess/config.json ./data/aftermess/config.json

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "aftermess.server:get_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]

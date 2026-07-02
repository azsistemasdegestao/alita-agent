# syntax=docker/dockerfile:1

FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alita_agent ./alita_agent

EXPOSE 8001
CMD ["uvicorn", "alita_agent.api:app", "--host", "0.0.0.0", "--port", "8001"]

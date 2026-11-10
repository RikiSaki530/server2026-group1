FROM python:3.12-slim
WORKDIR /app
COPY common ./common
COPY collector ./collector
USER 10001
CMD ["python", "-m", "collector.main"]

FROM node:22-bookworm-slim AS node
FROM python:3.12-slim
WORKDIR /app
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
COPY backend /app
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home sentinel && chown -R sentinel:sentinel /app
USER sentinel
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8001
CMD ["uvicorn", "sentinel.main:app", "--host", "0.0.0.0", "--port", "8001"]

FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
RUN useradd -m bot && chown -R bot:bot /app
USER bot
CMD ["python","main.py"]

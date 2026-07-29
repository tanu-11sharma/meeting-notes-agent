FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "-m", "app.cli"]
CMD ["sample_data/sample_transcript.txt", "--title", "Q3 Planning Sync"]

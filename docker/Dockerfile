FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pdfalchemy/ ./pdfalchemy/
COPY setup.py .
RUN pip install -e .

RUN mkdir -p /tmp/pdfalchemy/uploads /tmp/pdfalchemy/outputs

EXPOSE 8000

CMD ["uvicorn", "pdfalchemy.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

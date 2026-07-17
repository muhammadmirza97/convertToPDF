FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements-dev.txt

COPY src ./src
COPY tests ./tests
COPY sample_files ./sample_files
COPY run_app.py convert_to_pdf.py ./

CMD ["python", "-m", "pytest", "-q"]


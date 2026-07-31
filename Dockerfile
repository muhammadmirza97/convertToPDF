# Runs the core test suite in a clean Linux container.
# The Windows GUI is not part of this image; the GUI tests skip themselves without a display.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY tests ./tests
COPY assets ./assets
COPY run_app.py cli.py ./

CMD ["python", "-m", "pytest", "-q"]

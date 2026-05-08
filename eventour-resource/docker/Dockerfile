FROM python:3.11-slim

WORKDIR /eventour-resource
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "scripts/13_validate_release.py"]


FROM antganios/provenance-base:latest

WORKDIR /app

COPY python-tools .
COPY requirements.txt .

RUN chmod -R 755 /app

RUN pip install  -r requirements.txt
FROM mcr.microsoft.com/playwright/python:v1.52.0-noble AS base
WORKDIR /app
COPY ippdu.py /app/
RUN pip install --no-cache-dir playwright requests beautifulsoup4 --break-system-packages
ENTRYPOINT ["/app/ippdu.py"]

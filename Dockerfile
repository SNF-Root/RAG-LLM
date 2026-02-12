FROM python:3.11-slim

WORKDIR /app


RUN apt-get clean && apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    # ca-certificates \
    # # libgl1 \
    # # libglib2.0-0 \
    # poppler-utils \
 && rm -rf /var/lib/apt/lists/*

COPY container_requirements.txt .

RUN pip install --no-cache-dir -r container_requirements.txt

COPY . .

CMD ["/bin/bash"]


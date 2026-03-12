FROM python:3.11-slim

WORKDIR /app

COPY container_requirements.txt .

RUN pip install --no-cache-dir -r container_requirements.txt

COPY . .

CMD ["/bin/bash"]

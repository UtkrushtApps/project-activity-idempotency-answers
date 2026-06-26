FROM python:3.11-slim

WORKDIR /root/task

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /root/task/requirements.txt
RUN pip install --no-cache-dir -r /root/task/requirements.txt

COPY app /root/task/app
COPY tests /root/task/tests
COPY sample_queries.sql /root/task/sample_queries.sql

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

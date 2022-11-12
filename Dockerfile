FROM python:3.10

COPY src/* /app/
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r /app/requirements.txt
EXPOSE 57537
ENV FLASK_APP=shard_api
ENTRYPOINT ["python3", "-m", "flask", "run", "-h", "0.0.0.0", "-p", "57537"]
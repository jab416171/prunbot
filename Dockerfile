from python:3.11
# RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev git libffi python3-dev
RUN apt update && apt install -y libffi-dev libnacl-dev python3-dev ffmpeg && rm -rf /var/lib/apt/lists/*
copy requirements.txt /
run pip3 install -r /requirements.txt
ENV PYTHONPATH="/prunbot:${PYTHONPATH}"
ARG token=
ENV TOKEN="${token}"
ARG prun_apikey=
ENV PRUN_APIKEY="${prun_apikey}"
ARG sql_db=
ENV SQL_DB="${sql_db}"
ARG google_application_credentials=
ENV GOOGLE_APPLICATION_CREDENTIALS="${google_application_credentials}"
copy . /
entrypoint ["python", "/prunbot/run.py"]

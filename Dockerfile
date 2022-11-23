FROM python:3-alpine AS build
RUN apk add build-base postgresql libpq-dev libffi-dev

WORKDIR /out

COPY requirements.txt .
ADD setup.py .

RUN pip wheel . -w wheels

FROM python:3-alpine AS runtime
RUN apk add libpq-dev

ENV PYTHONUNBUFFERED 1

WORKDIR /app

ADD requirements.txt /app/requirements.txt
ADD manage.py /app/manage.py

ADD BFBC2_MasterServer /app/BFBC2_MasterServer
ADD easo /app/easo
ADD Plasma /app/Plasma

COPY --from=build /out/wheels /tmp/wheels

RUN pip install --no-index --find-links=/tmp/wheels/ -r requirements.txt

WORKDIR /app

CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload" ]
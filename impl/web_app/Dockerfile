FROM    python:3.13-alpine
WORKDIR /app
RUN     mkdir -p /app/tmp
RUN     mkdir -p /app/uploads
RUN     apk add gcc python3-dev
RUN     apk add gcc musl-dev linux-headers python3-dev
COPY    . .
RUN     pip install --upgrade pip
RUN     pip install -r requirements-alpine.txt
RUN     pip list
EXPOSE  8000
CMD     ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]

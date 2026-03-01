FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

ENV SQLALCHEMY_DATABASE_URI=sqlite:////data/stavebni_denik.db

EXPOSE 3000

CMD ["python", "app.py"]

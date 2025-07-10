FROM python:3.11-slim

WORKDIR /app

# Instala ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["python", "app.py"]

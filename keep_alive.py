from flask import Flask
from threading import Thread
from waitress import serve

app = Flask('')

@app.route('/')
def main():
  return "Your bot is alive!"

def run():
    serve(app, host="0.0.0.0", port=8080)

def keep_alive():
    server = Thread(target=run, daemon=True)
    server.start()

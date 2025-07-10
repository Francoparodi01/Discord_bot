from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive"

def keep_alive():
    thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    thread.start()

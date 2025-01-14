import main
from flask import Flask
from threading import Thread
import asyncio

app = Flask(__name__)

# Función para iniciar la aplicación de Flask
@app.route('/')
def home():
    return "Servidor Flask y bot de Discord en ejecución."

@app.route('/status')
def status():
    return "El bot de Discord está funcionando."

# Función para iniciar Flask
def run_flask():
    app.run(host='0.0.0.0', port=5000)

# Función para iniciar el bot de Discord
def run_discord_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main.run_bot())  # Asumiendo que run_bot está configurado para usar asyncio

if __name__ == '__main__':
    # Ejecutar Discord en un hilo separado
    discord_thread = Thread(target=run_discord_bot)
    discord_thread.start()

    # Ejecutar Flask en el hilo principal
    run_flask()

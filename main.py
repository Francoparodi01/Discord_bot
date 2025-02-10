import discord
import yt_dlp
from youtube_search import YoutubeSearch  
import asyncio
import os
from dotenv import load_dotenv
import requests

load_dotenv()  

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

cookies_string = os.getenv("YOUTUBE_COOKIES")

# Verificar si se encuentran cookies y escribirlas en un archivo
if cookies_string:
    cookies = {cookie.split("=")[0]: cookie.split("=")[1] for cookie in cookies_string.split("; ")}
    with open("cookies.txt", "w") as f:
        for key, value in cookies.items():
            f.write(f"{key}\tTRUE\t/\tFALSE\t0\t{value}\n")
else:
    print("Error: No se encontró la variable de entorno 'YOUTUBE_COOKIES'.")

def run_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    voice_clients = {}
    queues = {}
    current_song = {}

    yt_dl_options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "extractaudio": True,
        "audioquality": 1,
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "restrictfilenames": True,
        "source_address": None,
        'cookies': 'cookies.txt',  # Aquí pasamos el archivo de cookies
    }

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    @client.event
    async def on_ready():
        print(f"{client.user} has connected to Discord!")

    async def play_next_song(guild_id):
        """Reproduce la siguiente canción en la cola."""
        if guild_id in queues and queues[guild_id]:
            next_song = queues[guild_id].pop(0)  # Extrae la siguiente canción de la cola
            voice_client = voice_clients[guild_id]
            source = discord.FFmpegPCMAudio(next_song["url"], **ffmpeg_options)

            # Almacenar la canción actual para mostrarla en !nowplaying
            current_song[guild_id] = next_song  # Ahora almacenamos un diccionario completo

            def after_playing(error):
                if error:
                    print(f"Error al reproducir: {error}")
                # Reproduce la siguiente canción después de la actual
                asyncio.create_task(play_next_song(guild_id))  # Usamos create_task

            voice_client.play(source, after=after_playing)
        else:
            del queues[guild_id]  # Limpia la cola si está vacía
            # Desconectarse si no hay más canciones
            voice_client = voice_clients.get(guild_id)
            if voice_client:
                await voice_client.disconnect()
            del voice_clients[guild_id]

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if message.content.startswith("!play"):
            if message.author.voice:
                channel = message.author.voice.channel

                # Conectarse al canal de voz si no está conectado
                if message.guild.id not in voice_clients:
                    try:
                        voice_client = await channel.connect()
                        voice_clients[message.guild.id] = voice_client
                    except Exception as e:
                        await message.channel.send(f"No pude conectarme al canal de voz: {e}")
                        return

                try:
                    search_query = " ".join(message.content.split()[1:])
                    if not search_query:
                        await message.channel.send("Por favor, proporciona el nombre del artista y la canción.")
                        return

                    # Buscar en YouTube
                    results = YoutubeSearch(search_query, max_results=1).to_dict()
                    if not results:
                        await message.channel.send("No se encontraron resultados en YouTube.")
                        return

                    video_url = f"https://www.youtube.com{results[0]['url_suffix']}"
                    video_title = results[0]['title']

                    # Extraer información del video/audio con yt-dlp
                    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))

                    if "url" not in data:
                        await message.channel.send("No se pudo obtener el enlace de audio.")
                        return

                    song_url = data["url"]
                    await message.channel.send(f"Añadido a la cola: {video_title}")

                    # Agregar la canción a la cola
                    if message.guild.id not in queues:
                        queues[message.guild.id] = []

                    # Guardar el título y la URL en la cola
                    queues[message.guild.id].append({"title": video_title, "url": song_url})

                    # Si no hay canciones reproduciéndose, empezar a reproducir
                    if not voice_clients[message.guild.id].is_playing():
                        await play_next_song(message.guild.id)
                except Exception as e:
                    print(f"Error al intentar reproducir: {e}")
                    await message.channel.send("Ocurrió un error al intentar reproducir la música.")
            else:
                await message.channel.send("¡Necesitas estar en un canal de voz!")

        elif message.content.startswith("!resume"):
            if message.guild.id in voice_clients:
                voice_clients[message.guild.id].resume()
                await message.channel.send("Reproducción reanudada.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif message.content.startswith("!pause"):
            if message.guild.id in voice_clients:
                voice_clients[message.guild.id].pause()
                await message.channel.send("Reproducción pausada.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif message.content.startswith("!leave"):
            if message.guild.id in voice_clients:
                await voice_clients[message.guild.id].disconnect()
                if message.guild.id in queues:
                    del queues[message.guild.id]
                await message.channel.send("Desconectado del canal de voz.")
            else:
                await message.channel.send("El bot no está conectado a un canal de voz.")

        elif message.content.startswith("!skip") or message.content.startswith("!next"):
            if message.guild.id in voice_clients:
                voice_client = voice_clients[message.guild.id]
                if voice_client.is_playing():
                    voice_client.stop()
                    await message.channel.send("Canción omitida.")
                else:
                    await message.channel.send("No hay música reproduciéndose.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif message.content.startswith("!queue"):
            if message.guild.id in queues and queues[message.guild.id]:
                # Generar una lista de títulos de las canciones
                queue_list = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(queues[message.guild.id])])
                await message.channel.send(f"Cola de reproducción:\n{queue_list}")
            else:
                await message.channel.send("La cola está vacía.")

        elif message.content.startswith("!clearqueue"):
            if message.guild.id in queues:
                queues[message.guild.id].clear()
                await message.channel.send("La cola ha sido vaciada.")
            else:
                await message.channel.send("No hay canciones en la cola.")

        elif message.content.startswith("!nowplaying"):
            if message.guild.id in current_song and current_song[message.guild.id]:
                # Mostrar el título de la canción actual
                now_playing = current_song[message.guild.id]
                await message.channel.send(f"Ahora sonando: {now_playing['title']}")
            else:
                await message.channel.send("No hay ninguna canción reproduciéndose.")

        elif message.content.startswith("!help"):
            help_message = """
            Comandos:
            - !play [nombre de la canción]: Reproduce una canción desde YouTube.
            - !resume: Reanuda la reproducción de la canción actual.
            - !pause: Pausa la reproducción de la canción actual.
            - !skip o !next: Omitir la canción actual y reproducir la siguiente.
            - !queue: Muestra la cola de reproducción.
            - !clearqueue: Elimina todas las canciones de la cola.
            - !nowplaying: Muestra la canción que se está reproduciendo actualmente.
            - !leave: Desconecta al bot del canal de voz.
            - !help: Muestra este mensaje de ayuda.
            """
            await message.channel.send(help_message)

    client.run(DISCORD_TOKEN)

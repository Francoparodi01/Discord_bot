
# Discord Music Bot 🎵🎶


Este es un bot de música para Discord que te permite escuchar música directamente desde YouTube en un canal de voz. Usando comandos sencillos para gestionar la cola de reproducción, pausar, reanudar, omitir canciones y algunas funcionalidades más.

Librerías utilizadas: discord.py, yt-dlp, youtube-search, python-dotenv

Comenzando 🚀

Para crear un bot personalizado y propio, seguí estos pasos:

Ingresá a la sección de developers en https://discord.com/developers/docs/intro
Luego en applications y creas una nueva aplicación.
Una vez creado el bot, en OAuth2 copiamos la clave secreta y seleccionamos la casilla de bot con el rol de administrador para invitar el bot a nuestro canal.


Requisitos 📋
Python 3.x
Librerías necesarias: discord.py, yt-dlp, youtube-search, python-dotenv.
Una vez completados los pasos anteriores, clona el repositorio e instala las dependencias con el siguiente comando:

"pip install -r requirements.txt"


Comandos del Bot ⚙️

1. !play [nombre de la canción] 🎧
Este comando permite buscar y reproducir música directamente desde YouTube.

![Play Command](gifs/!playvideo.gif)

2. !pause & !resume ⏸️▶️
Pausa y reanuda la canción que se está reproduciendo actualmente.

![Pause/Resume Command](gifs/!pause_!resume.gif)


4. !skip o !next ⏭️
Omitir la canción actual y pasar a la siguiente en la cola.

![Next Command](gifs/!next.gif)

5. !queue 📜
Muestra la lista de canciones que están en la cola de reproducción.

![Queue Command](gifs/!queue.gif)

6. !nowplaying 🎶
Muestra el título de la canción que está sonando actualmente.

![NowPlaying Command](gifs/!nowplaying.gif)

7. !leave 👋
Desconecta el bot del canal de voz.

![Leave Command](gifs/!queue.gif)

8. !help ❓
Muestra una lista de todos los comandos disponibles y cómo usarlos.

Contribuir 🤝

Si tienes ideas para mejorar este bot, no dudes en hacer un fork y crear un pull request.





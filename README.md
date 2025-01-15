
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

![!playvideo](https://github.com/user-attachments/assets/2f412c2a-2d50-4395-981c-a7644acd7426)

2. !pause & !resume ⏸️▶️
Pausa y reanuda la canción que se está reproduciendo actualmente.

![!pause_!resume](https://github.com/user-attachments/assets/c0ef6ae5-e7e2-4f8e-9e1c-308a1a99f0d3)

4. !skip o !next ⏭️
Omitir la canción actual y pasar a la siguiente en la cola.

![!next](https://github.com/user-attachments/assets/8c39fc0d-a85c-4857-a043-a00856dc6164)

5. !queue 📜
Muestra la lista de canciones que están en la cola de reproducción.

![!queue](https://github.com/user-attachments/assets/f83944ca-4110-46dc-824f-03a203c196ba)

6. !nowplaying 🎶
Muestra el título de la canción que está sonando actualmente.

![!nowplaying](https://github.com/user-attachments/assets/fa3c36ab-7d82-4094-9f0b-068e5dde374b)

7. !leave 👋
Desconecta el bot del canal de voz.

![!queue](https://github.com/user-attachments/assets/76305fb2-5129-45c1-8a7e-0777a1e38e25)

8. !help ❓
Muestra una lista de todos los comandos disponibles y cómo usarlos.

Contribuir 🤝

Si tienes ideas para mejorar este bot, no dudes en hacer un fork y crear un pull request.





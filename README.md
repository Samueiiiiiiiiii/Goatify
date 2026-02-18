# 🐐 GOAT Music — Web App

Descargador y reproductor de música de YouTube en el navegador.

## 🚀 Cómo usar (solo necesitas Docker)

### Opción A — Docker Compose (recomendado)
```bash
docker compose up --build
```
Luego abrí: **http://localhost:5000**

### Opción B — Python directo (si tenés Python instalado)
```bash
pip install -r requirements.txt
# También necesitás ffmpeg instalado en el sistema
python app.py
```
Luego abrí: **http://localhost:5000**

---

## ✨ Funciones
- 🔍 Buscar canciones en YouTube (10 resultados)
- ▶️ Reproducción directa en el navegador
- ⏭ Autoplay al terminar una canción
- ⬇️ Descargar como MP3 (requiere ffmpeg)
- 🔊 Control de volumen
- ⏩ Barra de progreso con seek

## 📦 Requisitos
- Docker (opción A)
- Python 3.11+ y ffmpeg (opción B)

---

> **Nota:** La descarga en MP3 requiere ffmpeg. Si usás Docker, ya viene incluido. Si usás Python directo, instalá ffmpeg desde https://ffmpeg.org

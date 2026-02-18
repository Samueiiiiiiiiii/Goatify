from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import tempfile
import threading
import json
import time
import uuid

app = Flask(__name__)
CORS(app)

TEMP_DIR = tempfile.gettempdir()
download_progress = {}

COOKIES_FILE = os.path.join(TEMP_DIR, 'yt_cookies.txt')

def get_cookies_opt():
    # Priority 1: environment variable
    cookies_content = os.environ.get('YOUTUBE_COOKIES', '').strip()
    if cookies_content:
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(cookies_content)
        return {'cookiefile': COOKIES_FILE}
    # Priority 2: local file (for local dev)
    local = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    if os.path.exists(local):
        return {'cookiefile': local}
    return {}

YDL_OPTS_SEARCH = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': True,
    'default_search': 'ytsearch10',
    'no_warnings': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web']
        }
    },
    **get_cookies_opt()
}

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Query requerida'}), 400

    try:
        with YoutubeDL(YDL_OPTS_SEARCH) as ydl:
            results = ydl.extract_info(f"ytsearch10:{query}", download=False)
            if 'entries' in results:
                entries = []
                for entry in results['entries']:
                    if entry:
                        entries.append({
                            'id': entry.get('id', ''),
                            'title': entry.get('title', 'Sin título'),
                            'uploader': entry.get('uploader', 'Desconocido'),
                            'duration': entry.get('duration', 0),
                            'thumbnail': entry.get('thumbnail', ''),
                            'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                            'webpage_url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                            'view_count': entry.get('view_count', 0),
                        })
                return jsonify({'results': entries})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'results': []})


@app.route('/api/download', methods=['GET'])
def download():
    url = request.args.get('url', '').strip()
    video_id = request.args.get('id', '').strip()
    title = request.args.get('title', 'audio').strip()

    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_path = os.path.join(TEMP_DIR, f"{safe_title or video_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        **get_cookies_opt()
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_path = os.path.splitext(filename)[0] + '.mp3'

            if not os.path.exists(mp3_path):
                # fallback: try other extensions
                for ext in ['.m4a', '.webm', '.opus', '.ogg']:
                    alt = os.path.splitext(filename)[0] + ext
                    if os.path.exists(alt):
                        mp3_path = alt
                        break

            if os.path.exists(mp3_path):
                return send_file(
                    mp3_path,
                    as_attachment=True,
                    download_name=f"{safe_title or 'audio'}.mp3",
                    mimetype='audio/mpeg'
                )
            else:
                return jsonify({'error': 'No se pudo generar el archivo de audio'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stream', methods=['GET'])
def stream():
    """Stream audio directly for playback in browser"""
    url = request.args.get('url', '').strip()
    video_id = request.args.get('id', str(uuid.uuid4())).strip()

    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    output_path = os.path.join(TEMP_DIR, f"stream_{video_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        **get_cookies_opt()
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            audio_file = None
            for ext in ['.m4a', '.webm', '.opus', '.ogg', '.mp4']:
                candidate = os.path.splitext(filename)[0] + ext
                if os.path.exists(candidate):
                    audio_file = candidate
                    break
            if not audio_file and os.path.exists(filename):
                audio_file = filename

            if audio_file:
                ext = os.path.splitext(audio_file)[1].lower()
                mime_map = {
                    '.m4a': 'audio/mp4',
                    '.webm': 'audio/webm',
                    '.opus': 'audio/ogg',
                    '.ogg': 'audio/ogg',
                    '.mp3': 'audio/mpeg',
                    '.mp4': 'audio/mp4',
                }
                mime = mime_map.get(ext, 'audio/mpeg')
                return send_file(audio_file, mimetype=mime)
            else:
                return jsonify({'error': 'No se pudo obtener el audio'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    return send_file('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

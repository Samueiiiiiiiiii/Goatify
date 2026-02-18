from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import tempfile
import uuid

app = Flask(__name__)
CORS(app)

TEMP_DIR = tempfile.gettempdir()
COOKIES_FILE = os.path.join(TEMP_DIR, 'yt_cookies.txt')


def get_cookies_opt():
    cookies_content = os.environ.get('YOUTUBE_COOKIES', '').strip()
    if cookies_content:
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(cookies_content)
        return {'cookiefile': COOKIES_FILE}
    local = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    if os.path.exists(local):
        return {'cookiefile': local}
    return {}


def base_opts():
    return {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'android_vr'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        **get_cookies_opt()
    }


@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Query requerida'}), 400

    opts = {
        **base_opts(),
        'format': 'bestaudio/best',
        'noplaylist': True,
        'extract_flat': True,
        'default_search': 'ytsearch10',
    }

    try:
        with YoutubeDL(opts) as ydl:
            results = ydl.extract_info(f"ytsearch10:{query}", download=False)
            entries = []
            for entry in (results.get('entries') or []):
                if entry:
                    vid_id = entry.get('id', '')
                    entries.append({
                        'id': vid_id,
                        'title': entry.get('title', 'Sin titulo'),
                        'uploader': entry.get('uploader', 'Desconocido'),
                        'duration': entry.get('duration', 0),
                        'thumbnail': entry.get('thumbnail', ''),
                        'webpage_url': f"https://www.youtube.com/watch?v={vid_id}",
                        'view_count': entry.get('view_count', 0),
                    })
            return jsonify({'results': entries})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stream', methods=['GET'])
def stream():
    url = request.args.get('url', '').strip()
    video_id = request.args.get('id', str(uuid.uuid4())).strip()

    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    output_path = os.path.join(TEMP_DIR, f"stream_{video_id}.%(ext)s")

    opts = {
        **base_opts(),
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_path,
    }

    try:
        with YoutubeDL(opts) as ydl:
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

            if not audio_file:
                return jsonify({'error': 'No se encontro el archivo de audio'}), 500

            mime_map = {
                '.m4a': 'audio/mp4', '.webm': 'audio/webm',
                '.opus': 'audio/ogg', '.ogg': 'audio/ogg',
                '.mp3': 'audio/mpeg', '.mp4': 'audio/mp4',
            }
            ext = os.path.splitext(audio_file)[1].lower()
            mime = mime_map.get(ext, 'audio/mpeg')
            return send_file(audio_file, mimetype=mime)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['GET'])
def download():
    url = request.args.get('url', '').strip()
    video_id = request.args.get('id', '').strip()
    title = request.args.get('title', 'audio').strip()

    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_path = os.path.join(TEMP_DIR, f"{safe_title or video_id}.%(ext)s")

    opts = {
        **base_opts(),
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
    }

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_path = os.path.splitext(filename)[0] + '.mp3'

            if not os.path.exists(mp3_path):
                for ext in ['.m4a', '.webm', '.opus', '.ogg']:
                    alt = os.path.splitext(filename)[0] + ext
                    if os.path.exists(alt):
                        mp3_path = alt
                        break

            if not os.path.exists(mp3_path):
                return jsonify({'error': 'No se pudo generar el archivo'}), 500

            return send_file(
                mp3_path,
                as_attachment=True,
                download_name=f"{safe_title or 'audio'}.mp3",
                mimetype='audio/mpeg'
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    return send_file('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

from flask import Flask, request, jsonify, render_template
import requests
import re

app = Flask(__name__)

API_HOST = 'https://cnv.cx'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',
    'Accept': '*/*',
    'Origin': 'https://x2download.is',
    'Referer': 'https://x2download.is/',
    'Content-Type': 'application/x-www-form-urlencoded'
}

def get_key():
    try:
        resp = requests.get(f"{API_HOST}/v2/sanity/key", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json().get('key')
    except Exception:
        return None

def extract_video_id(url):
    # Mengambil ID video dari link YouTube
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

# --- ENDPOINT BARU UNTUK SEARCH & INFO VIDEO ---
@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.json or {}
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'status': False, 'message': 'Masukkan judul atau link YouTube'}), 400

    try:
        # Cek apakah input berupa link atau kata kunci
        if "youtube.com" in query or "youtu.be" in query:
            video_id = extract_video_id(query)
            if not video_id:
                return jsonify({'status': False, 'message': 'Link YouTube tidak valid'}), 400
                
            # Ambil info langsung pakai oEmbed (lebih cepat untuk link)
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            res = requests.get(oembed_url, timeout=10).json()
            
            info = {
                'title': res.get('title'),
                'thumbnail': res.get('thumbnail_url'),
                'uploader': res.get('author_name'),
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }
        else:
            # Jika berupa kata kunci, gunakan Piped API untuk Search
            search_url = f"https://pipedapi.kavin.rocks/search?q={query}&filter=videos"
            res = requests.get(search_url, timeout=10).json()
            items = res.get('items', [])
            
            if not items:
                return jsonify({'status': False, 'message': 'Video tidak ditemukan'}), 404
                
            first_video = items[0]
            video_id = first_video.get('url').split('/watch?v=')[-1]
            
            info = {
                'title': first_video.get('title'),
                'thumbnail': first_video.get('thumbnail'),
                'uploader': first_video.get('uploaderName'),
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }

        return jsonify({'status': True, 'data': info})

    except Exception as e:
        print("Error Info API:", str(e))
        return jsonify({'status': False, 'message': 'Gagal mengambil informasi video. Coba lagi.'}), 500

# --- ENDPOINT CONVERT (Tetap sama) ---
@app.route('/api/convert', methods=['POST'])
def convert_video():
    data = request.json or {}
    youtube_url = data.get('url')
    fmt = data.get('format', 'mp3')
    quality = data.get('quality', '720')

    if not youtube_url:
        return jsonify({'status': False, 'message': 'URL parameter required'}), 400

    api_key = get_key()
    if not api_key:
        return jsonify({'status': False, 'message': 'Server key fetch failed'}), 500

    payload = {
        'link': youtube_url,
        'format': fmt,
        'audioBitrate': '320',
        'videoQuality': quality,
        'vCodec': 'h264'
    }
    
    post_headers = HEADERS.copy()
    post_headers['Key'] = api_key

    try:
        resp = requests.post(f"{API_HOST}/v2/converter", headers=post_headers, data=payload, timeout=20)
        result = resp.json()
        print("Convert API Response:", result) # Untuk debug di Vercel

        if result.get('status') == 'tunnel' and result.get('url'):
            return jsonify({
                'status': True,
                'data': {
                    'title': result.get('filename', 'Unknown Title'),
                    'download_url': result.get('url'),
                    'format': fmt
                }
            })
        else:
            error_msg = result.get('message', 'Konversi gagal dari server.')
            return jsonify({'status': False, 'message': error_msg}), 400

    except Exception as e:
        return jsonify({'status': False, 'message': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

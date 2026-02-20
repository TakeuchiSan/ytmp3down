from flask import Flask, request, jsonify, render_template
import requests

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

@app.route('/api/convert', methods=['GET', 'POST'])
def convert_video():
    if request.method == 'GET':
        youtube_url = request.args.get('url')
        fmt = request.args.get('format', 'mp3')
        quality = request.args.get('quality', '720')
    else:
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
            return jsonify({'status': False, 'message': 'Conversion failed'}), 400

    except Exception as e:
        return jsonify({'status': False, 'message': str(e)}), 500

# Ubah route index untuk me-render HTML
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

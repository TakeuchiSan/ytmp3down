from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

# Fungsi bantuan untuk format waktu
def format_duration(seconds):
    if not seconds: return "00:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search_yt():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Query tidak boleh kosong"}), 400

    # Jika user memasukkan URL, langsung ambil infonya
    if query.startswith("http"):
        ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                filesize = info.get('filesize') or info.get('filesize_approx', 0)
                size_mb = round(filesize / (1024 * 1024), 2) if filesize else "Unknown"
                
                return jsonify([{
                    "type": "url",
                    "id": info.get('id'),
                    "url": info.get('webpage_url'),
                    "title": info.get('title'),
                    "thumbnail": info.get('thumbnail'),
                    "duration": format_duration(info.get('duration')),
                    "size_mb": size_mb
                }])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Jika query biasa, gunakan fitur ytsearch
    ydl_opts = {'extract_flat': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_result = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = search_result.get('entries', [])
            
            results = []
            for entry in entries:
                results.append({
                    "type": "search",
                    "id": entry.get('id'),
                    "url": entry.get('url'),
                    "title": entry.get('title'),
                    "thumbnail": entry.get('thumbnails', [{}])[-1].get('url', ''), # Ambil thumbnail resolusi tertinggi
                    "duration": format_duration(entry.get('duration', 0))
                })
            return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['GET'])
def download_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL tidak ditemukan"}), 400

    file_id = str(uuid.uuid4())
    temp_dir = "/tmp" 
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{temp_dir}/{file_id}.%(ext)s',
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            clean_title = "".join([c for c in info['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            
            # File hasil konversi ffmpeg akan menjadi .mp3
            file_path = f"{temp_dir}/{file_id}.mp3"
            
            return send_file(
                file_path, 
                as_attachment=True, 
                download_name=f"{clean_title}.mp3",
                mimetype='audio/mpeg'
            )
    except Exception as e:
        return jsonify({"error": f"Gagal mengunduh: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
import yt_dlp
import re  # เพิ่มการนำเข้าโมดูล re

app = Flask(__name__)
app = app  # สำหรับ Vercel
download_status = {'status': 'Waiting...', 'percent': 0, 'filename': ''}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data['url']
    format_choice = data['format']
    threading.Thread(target=download_thread, args=(url, format_choice)).start()
    return '', 204

def download_thread(url, format_choice):
    global download_status
    download_status = {'status': 'Downloading...', 'percent': 0, 'filename': ''}

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        'progress_hooks': [progress_hook],
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # ใช้ชื่อวิดีโอแทน ID
        'format': 'bestvideo+bestaudio/best' if format_choice == 'mp4' else 'bestaudio/best',
        'postprocessors': []
    }

    if format_choice == 'mp3':
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0'
        })
    else:
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        })
        ydl_opts['merge_output_format'] = 'mp4'  # บังคับให้รวมไฟล์เป็น MP4

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            if format_choice == 'mp3':
                filename = os.path.splitext(filename)[0] + '.mp3'
            else:
                filename = os.path.splitext(filename)[0] + '.mp4'
            print(f"Downloaded file: {filename}")
            download_status['status'] = 'Done!'
            download_status['filename'] = os.path.basename(filename)
            download_status['percent'] = 100
    except Exception as e:
        download_status['status'] = f"Error: {str(e)}"
        print(f"Error: {str(e)}")

def progress_hook(d):
    if d['status'] == 'downloading':
        # ลบ ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        downloaded = ansi_escape.sub('', d.get('_percent_str', '0.0%')).strip().replace('%', '')
        speed = ansi_escape.sub('', d.get('_speed_str', ''))
        eta = d.get('eta', '')

        download_status['status'] = f"Downloading... Speed: {speed}, ETA: {eta}s"
        try:
            download_status['percent'] = float(downloaded)
        except ValueError:
            download_status['percent'] = 0.0

@app.route('/progress')
def progress():
    return jsonify(download_status)

@app.route('/download_file/<filename>')
def download_file(filename):
    path = os.path.join("downloads", filename)
    if os.path.exists(path):
        return send_from_directory("downloads", filename, as_attachment=True)
    return "File not found", 404

@app.route('/list_files')
def list_files():
    files = os.listdir("downloads")
    return jsonify(files)

if __name__ == '__main__':
    app.run(debug=True)
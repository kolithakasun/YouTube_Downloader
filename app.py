from flask import Flask, render_template_string, request, send_file, redirect, url_for, flash, session
import subprocess
import json
import os
import re
import sys
from flask import Response
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

# Determine download directory from command line argument or use default
if len(sys.argv) > 1:
    DOWNLOAD_DIR = sys.argv[1]
else:
    DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')

HTML_FORM = '''
<!doctype html>
<title>YouTube Video Downloader (yt-dlp)</title>
<h2>YouTube Video Downloader (yt-dlp)</h2>
<form method=post>
  <input type=text name=url placeholder="Enter YouTube URL" required style="width:300px">
  <input type=submit value="Get Qualities">
</form>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul style="color:red;">
    {% for message in messages %}
      <li>{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
'''

QUALITY_FORM = '''
<!doctype html>
<title>Select Video Quality</title>
<h2>Select Video Quality</h2>
<form method=post>
  <input type=hidden name=url value="{{ url }}">
  <select name=format_id required>
    {% for f in formats %}
      <option value="{{ f['format_id'] }}">{{ f['format_note'] or '' }} {{ f['height'] or '' }}p ({{ f['ext'] }}, {{ f['filesize']|default('unknown', true) }} bytes)</option>
    {% endfor %}
  </select>
  <input type=submit value="Download">
</form>
'''

def extract_video_id(url):
    # Extracts the video ID from various YouTube URL formats
    match = re.search(r'(?:v=|youtu.be/)([\w-]{11})', url)
    return match.group(1) if match else None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        format_id = request.form.get('format_id')
        if not url or not url.startswith('http'):
            flash('Please enter a valid YouTube URL.')
            return redirect(url_for('index'))
        try:
            if not format_id:
                # Step 1: Get available formats using yt-dlp (JSON only)
                result = subprocess.run([
                    'yt-dlp', '--dump-json', url
                ], capture_output=True, text=True)
                if result.returncode != 0:
                    err = result.stderr.strip()
                    if len(err) > 500:
                        err = err[:500] + '... (truncated)'
                    flash('yt-dlp error: ' + err)
                    return redirect(url_for('index'))
                try:
                    info = json.loads(result.stdout)
                except Exception as json_err:
                    err = (result.stderr or result.stdout or str(json_err)).strip()
                    if len(err) > 500:
                        err = err[:500] + '... (truncated)'
                    flash('yt-dlp output error: ' + err)
                    return redirect(url_for('index'))
                # Show all video formats (even if audio is missing)
                formats = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('height')]
                formats = sorted(formats, key=lambda x: x.get('height', 0), reverse=True)
                if not formats:
                    flash('No suitable video formats found.')
                    return redirect(url_for('index'))
                return render_template_string(QUALITY_FORM, formats=formats, url=url)
            else:
                os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                output_template = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
                # Prefer mp4 for both video and audio, fallback to best available
                format_string = f"{format_id}[ext=mp4]+bestaudio[ext=m4a]/{format_id}+bestaudio/best"
                progress_file = os.path.join(DOWNLOAD_DIR, 'progress.txt')
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                # Check for cookies.txt in the app directory
                cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
                ytdlp_cmd = [
                    'yt-dlp', '-f', format_string, '-o', output_template, url,
                    '--progress', '--newline'
                ]
                if os.path.exists(cookies_path):
                    ytdlp_cmd.extend(['--cookies', cookies_path])
                def run_ytdlp():
                    filepath = None
                    with subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
                        for line in proc.stdout:
                            if '[download] Destination:' in line:
                                filepath = line.split(':', 1)[1].strip()
                            if '%' in line:
                                with open(progress_file, 'w') as pf:
                                    pf.write(line.strip())
                        proc.wait()
                    return filepath
                from threading import Thread
                thread = Thread(target=run_ytdlp)
                thread.start()
                return redirect(url_for('progress_page'))
        except Exception as e:
            flash(f'Error: {str(e)}')
            return redirect(url_for('index'))
    return render_template_string(HTML_FORM + '<p style="color:gray;">Tip: yt-dlp and ffmpeg are required for best quality. Install with <code>pip install yt-dlp</code> and <code>brew install ffmpeg</code>.</p>')

@app.route('/progress')
def progress_page():
    progress_file = os.path.join(DOWNLOAD_DIR, 'progress.txt')
    progress = ''
    if os.path.exists(progress_file):
        with open(progress_file) as pf:
            progress = pf.read()
    # Check if download is done (no progress update for 5 seconds)
    done = False
    if progress and '%' in progress:
        # If file exists and is not being updated, consider done
        last_mod = os.path.getmtime(progress_file)
        if time.time() - last_mod > 5:
            done = True
    if done:
        # Try to find the latest file in the download dir, ignoring progress.txt
        files = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)
                 if os.path.isfile(os.path.join(DOWNLOAD_DIR, f)) and f != 'progress.txt']
        if files:
            latest_file = max(files, key=os.path.getmtime)
            return render_template_string('''
            <!doctype html>
            <title>Download Complete</title>
            <h2>Download Complete</h2>
            <a href="/">&larr; Back to Home</a><br><br>
            <a href="/download?file={{filepath}}">Click here to download your file</a>
            ''', filepath=latest_file)
        else:
            flash('Could not determine downloaded file path.')
            return redirect(url_for('index'))
    else:
        # Show progress and auto-refresh
        return render_template_string('''
        <!doctype html>
        <title>Downloading...</title>
        <h2>Downloading...</h2>
        <a href="/">&larr; Back to Home</a><br><br>
        <pre>{{progress}}</pre>
        <script>setTimeout(function(){ window.location.reload(); }, 2000);</script>
        ''', progress=progress)

@app.route('/download')
def download_file():
    file = request.args.get('file')
    if not file or not os.path.exists(file):
        flash('File not found.')
        return redirect(url_for('index'))
    return send_file(file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5020)
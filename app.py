from flask import Flask, render_template_string, request, send_file, redirect, url_for, flash, session
import subprocess
import json
import os
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

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
                # Show all video formats (including video-only)
                formats = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('height')]
                formats = sorted(formats, key=lambda x: x.get('height', 0), reverse=True)
                if not formats:
                    flash('No suitable video formats found.')
                    return redirect(url_for('index'))
                return render_template_string(QUALITY_FORM, formats=formats, url=url)
            else:
                # Step 2: Download selected format using yt-dlp
                os.makedirs('downloads', exist_ok=True)
                result = subprocess.run([
                    'yt-dlp', '-f', format_id, '-o', 'downloads/%(title)s.%(ext)s', url
                ], capture_output=True, text=True)
                if result.returncode != 0:
                    flash('yt-dlp error: ' + result.stderr)
                    return redirect(url_for('index'))
                # Find the downloaded file
                # Parse yt-dlp output for the filename
                for line in result.stdout.splitlines():
                    if '[download] Destination:' in line:
                        filepath = line.split(':', 1)[1].strip()
                        break
                else:
                    flash('Could not determine downloaded file path.')
                    return redirect(url_for('index'))
                return send_file(filepath, as_attachment=True)
        except Exception as e:
            flash(f'Error: {str(e)}')
            return redirect(url_for('index'))
    return render_template_string(HTML_FORM + '<p style="color:gray;">Tip: yt-dlp and ffmpeg are required for best quality. Install with <code>pip install yt-dlp</code> and <code>brew install ffmpeg</code>.</p>')

if __name__ == '__main__':
    app.run(debug=True)
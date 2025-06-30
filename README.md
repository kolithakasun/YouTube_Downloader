# YouTube Video Downloader (yt-dlp + Flask)

This is a simple web-based YouTube video downloader built with Flask and yt-dlp. It allows you to select and download videos in your preferred quality (including 1080p, 4K, etc.).

## Requirements
- Python 3.7+
- pip

## Setup

1. **Clone or copy the project files to a folder.**

2. **Install Python dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

3. **Install ffmpeg (required for merging video+audio):**

   - Download and install ffmpeg from https://ffmpeg.org/download.html
   - Or use your OS package manager (e.g., `apt install ffmpeg` on Ubuntu, or download the binary for Windows/macOS)

4. **Run the Flask app:**

   ```sh
   python app.py
   ```

5. **Open your browser and go to:**

   [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Usage
1. Enter a YouTube video URL and click "Get Qualities".
2. Select your desired video quality from the dropdown.
3. Click "Download" to download the video. The file will be served to your browser.

## Notes
- For best results, keep yt-dlp and ffmpeg up to date.
- If you encounter errors, check the error message for details (e.g., video restrictions, network issues).
- Downloaded files are saved in the `downloads/` folder.

## Dependencies
- Flask
- yt-dlp
- ffmpeg

---

**This project is for personal/educational use. Please respect YouTube's Terms of Service.**

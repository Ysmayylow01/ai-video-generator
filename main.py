# app.py - DOLY DÜZEDILEN WERSIÝA
from flask import Flask, render_template, request, jsonify, send_file, g
import requests
import time
import os
from datetime import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import traceback
import sys

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'static/outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)

# =========================
# LOGGING - UNICODE FIX
# =========================

# Windows console üçin UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
# Emoji-siz formatter (Windows üçin)
console_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)

# File handler - UTF-8 bilen
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(funcName)s | %(message)s'))

logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])
logger = logging.getLogger(__name__)

# =========================
# API CONFIG
# =========================
API_TOKEN = os.getenv("UNIFICALLY_API_TOKEN", "sk-0e91d3e7e771ac5d9475213773fd7d3b5")
API_GENERATE_URL = "https://api.unifically.com/v1/tasks"
API_STATUS_URL = "https://api.unifically.com/v1/tasks/"

# Video cache
video_cache = {}

# =========================
# MIDDLEWARE
# =========================
@app.before_request
def log_request():
    g.start_time = time.time()
    logger.info("="*60)
    logger.info(f"[REQUEST] {request.method} {request.path}")

@app.after_request
def log_response(response):
    if hasattr(g, 'start_time'):
        elapsed = round((time.time() - g.start_time) * 1000, 2)
        logger.info(f"[RESPONSE] {response.status_code} ({elapsed}ms)")
    logger.info("="*60)
    return response

# =========================
# ROUTES
# =========================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_video():
    logger.info("[VIDEO] ===== GENERATION START =====")
    try:
        data = request.get_json()
        logger.info(f"[VIDEO] Received data: {json.dumps(data, indent=2)}")
        
        if not data:
            logger.error("[VIDEO] No JSON data!")
            return jsonify({"success": False, "error": "Invalid JSON"}), 400

        prompt = data.get("prompt")
        image_url = data.get("image_url")
        duration = int(data.get("duration", 6))
        resolution = data.get("resolution", "720p")
        aspect_ratio = data.get("aspect_ratio", "16:9")
        seed = data.get("seed")
        
        logger.info(f"[VIDEO] Parsed values:")
        logger.info(f"  - Prompt: {prompt}")
        logger.info(f"  - Image URL: {image_url}")
        logger.info(f"  - Duration: {duration}")
        logger.info(f"  - Resolution: {resolution}")
        logger.info(f"  - Aspect Ratio: {aspect_ratio}")
        logger.info(f"  - Seed: {seed}")
        
        if not prompt:
            logger.error("[VIDEO] Prompt is empty!")
            return jsonify({"success": False, "error": "Prompt required"}), 400
        
        # Validation
        if duration not in [6, 10, 15]:
            logger.warning(f"[VIDEO] Invalid duration {duration}, using 6")
            duration = 6
            
        if resolution not in ["480p", "720p"]:
            logger.warning(f"[VIDEO] Invalid resolution {resolution}, using 720p")
            resolution = "720p"
        
        # PAYLOAD
        payload = {
            "model": "xai/grok-imagine-video",
            "input": {
                "prompt": prompt,
                "duration": duration,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio
            }
        }
        
        if image_url:
            payload["input"]["image_url"] = image_url
        if seed:
            payload["input"]["seed"] = int(seed)
        
        headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
        
        logger.info(f"[API] POST {API_GENERATE_URL}")
        logger.info(f"[API] Payload: {json.dumps(payload, indent=2)}")
        logger.info(f"[API] Headers: Authorization=Bearer {API_TOKEN[:15]}...")
        
        logger.info("[API] Sending request...")
        response = requests.post(API_GENERATE_URL, json=payload, headers=headers, timeout=60)
        
        logger.info(f"[API] Response status: {response.status_code}")
        logger.info(f"[API] Response text: {response.text}")
        
        if response.status_code != 200:
            logger.error(f"[ERROR] API returned {response.status_code}")
            logger.error(f"[ERROR] Response: {response.text}")
            return jsonify({"success": False, "error": response.text}), response.status_code

        result = response.json()
        logger.info(f"[API] Parsed result: {json.dumps(result, indent=2)}")
        
        if not result.get("success"):
            logger.error(f"[ERROR] API success=false: {result}")
            return jsonify({"success": False, "error": result}), 400

        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            logger.error("[ERROR] No task_id in response!")
            logger.error(f"[ERROR] Full response: {result}")
            return jsonify({"success": False, "error": "No task_id"}), 500
        
        logger.info(f"[SUCCESS] ✅ Task created: {task_id}")
        logger.info("[VIDEO] ===== GENERATION END =====")
        return jsonify({"success": True, "task_id": task_id, "status": "pending"})

    except requests.exceptions.Timeout:
        logger.error("[ERROR] ⏱️ Request timeout (60s)")
        return jsonify({"success": False, "error": "Request timeout"}), 504
    except Exception as e:
        logger.error(f"[ERROR] ❌ Exception: {str(e)}")
        logger.error(f"[ERROR] Type: {type(e).__name__}")
        logger.error(f"[ERROR] Traceback:")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/status/<task_id>')
def check_status(task_id):
    logger.info(f"[STATUS] Check: {task_id}")
    try:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        
        # TIMEOUT INCREASED to 30 seconds
        response = requests.get(API_STATUS_URL + task_id, headers=headers, timeout=30)

        logger.info(f"[API] Status response: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"[ERROR] Status check failed: {response.text}")
            return jsonify({"success": False, "error": response.text}), response.status_code

        result = response.json()
        if not result.get("success"):
            return jsonify({"success": False, "error": result}), 400

        data = result.get("data", {})
        status = data.get("status")
        video_url = data.get("output", {}).get("video_url")
        
        logger.info(f"[STATUS] Task: {status}")
        
        if status == "completed" and video_url:
            video_cache[task_id] = {'url': video_url, 'timestamp': time.time()}
            logger.info(f"[SUCCESS] Video ready!")

        return jsonify({"success": True, "status": status, "video_url": video_url})

    except requests.exceptions.Timeout:
        logger.error("[ERROR] Status check timeout")
        return jsonify({"success": False, "error": "Status check timeout"}), 504
    except Exception as e:
        logger.error(f"[ERROR] {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download/<task_id>')
def download_video(task_id):
    logger.info(f"[DOWNLOAD] Request: {task_id}")
    try:
        if task_id not in video_cache:
            return jsonify({'success': False, 'error': 'Video not found'}), 404
        
        video_url = video_cache[task_id]['url']
        
        # TIMEOUT INCREASED
        video_resp = requests.get(video_url, timeout=120, stream=True)
        
        filename = f"video_{task_id}.mp4"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            for chunk in video_resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"[SUCCESS] Downloaded: {filename}")
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"[ERROR] {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/history')
def history():
    videos = []
    for task_id, info in video_cache.items():
        videos.append({
            "task_id": task_id,
            "url": info['url'],
            "created": datetime.fromtimestamp(info['timestamp']).strftime("%Y-%m-%d %H:%M:%S"),
            "download_url": f"/download/{task_id}"
        })
    videos.sort(key=lambda x: x['created'], reverse=True)
    return jsonify({"success": True, "videos": videos})

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("[STARTUP] AI Video Generator")
    logger.info(f"[API] {API_GENERATE_URL}")
    logger.info(f"[TOKEN] {API_TOKEN[:10]}...")
    logger.info("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
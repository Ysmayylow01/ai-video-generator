from flask import Flask, render_template, request, jsonify, send_file, g
import requests
import os
import time
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Folders
app.config['OUTPUT_FOLDER'] = 'static/outputs'
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)

# =========================
# LOGGING
# =========================
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)

file_handler = RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(funcName)s | %(message)s'))

logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])
logger = logging.getLogger(__name__)

# =========================
# API CONFIG
# =========================
API_TOKEN = os.getenv("UNIFICALLY_API_TOKEN", "sk-0e91d3e7e771ac5d9475213773fd7d3b5")
API_GENERATE_URL = "https://api.unifically.com/v1/tasks"
API_STATUS_URL = "https://api.unifically.com/v1/tasks/"

if not API_TOKEN or API_TOKEN.startswith("sk-"):
    logger.warning("⚠️ UNIFICALLY_API_TOKEN environment variable gerek!")

# Video cache
video_cache = {}

# =========================
# MIDDLEWARE
# =========================
@app.before_request
def log_request():
    g.start_time = time.time()
    logger.info("="*60)
    logger.info(f"🔵 {request.method} {request.path}")
    if request.is_json:
        logger.debug(f"Body: {request.get_json()}")

@app.after_request
def log_response(response):
    if hasattr(g, 'start_time'):
        elapsed = round((time.time() - g.start_time) * 1000, 2)
        logger.info(f"🟢 {response.status_code} ({elapsed}ms)")
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
    """xAI Grok-Imagine bilen wideo döretmek"""
    logger.info("🎬 VIDEO GENERATION REQUEST")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Invalid JSON"}), 400

        # Required
        prompt = data.get("prompt")
        
        # Optional
        image_url = data.get("image_url")  # optional başlangyç surat
        duration = int(data.get("duration", 3))  # 1, 3, 6, 9, 12, 15
        resolution = data.get("resolution", "720p")  # 480p, 720p
        aspect_ratio = data.get("aspect_ratio", "16:9")  # 1:1, 16:9, 9:16, etc
        seed = data.get("seed")
        
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Image URL: {image_url or 'None (text-to-video)'}")
        logger.info(f"Duration: {duration}s")
        logger.info(f"Resolution: {resolution}")
        logger.info(f"Aspect Ratio: {aspect_ratio}")
        
        # Validation
        if not prompt:
            return jsonify({"success": False, "error": "Prompt meýdany hökmany!"}), 400
        
        if duration not in [1, 3, 6, 9, 12, 15]:
            duration = 3
            logger.warning(f"Invalid duration, using default: {duration}")
        
        if resolution not in ["480p", "720p"]:
            resolution = "720p"
            logger.warning(f"Invalid resolution, using default: {resolution}")
        
        # API Request Payload
        payload = {
            "model": "xai/grok-imagine",
            "input": {
                "prompt": prompt,
                "duration": duration,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio
            }
        }
        
        # Optional parameters
        if image_url:
            payload["input"]["image_url"] = image_url
            logger.info("Using image-to-video mode")
        else:
            logger.info("Using text-to-video mode")
            
        if seed:
            payload["input"]["seed"] = int(seed)
        
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"📤 POST {API_GENERATE_URL}")
        logger.debug(f"Payload: {payload}")
        
        # Send request
        response = requests.post(API_GENERATE_URL, json=payload, headers=headers, timeout=30)
        
        logger.info(f"📥 Response: {response.status_code}")
        logger.debug(f"Response text: {response.text}")
        
        if response.status_code != 200:
            error_msg = response.text
            logger.error(f"❌ API error: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), response.status_code

        result = response.json()
        
        if not result.get("success"):
            logger.error(f"❌ API returned success=false")
            return jsonify({"success": False, "error": result}), 400

        task_id = result["data"]["task_id"]
        status = result["data"].get("status", "pending")
        
        logger.info(f"✅ Task created! ID: {task_id}, Status: {status}")
        
        return jsonify({
            "success": True, 
            "task_id": task_id, 
            "status": status,
            "message": "Wideo döredilýär..."
        })

    except requests.exceptions.Timeout:
        logger.error("❌ Request timeout")
        return jsonify({"success": False, "error": "Request timeout"}), 504
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/status/<task_id>')
def check_status(task_id):
    """Task statusyny barlamak"""
    logger.info(f"📊 STATUS CHECK: {task_id}")
    
    try:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        
        response = requests.get(API_STATUS_URL + task_id, headers=headers, timeout=15)
        
        logger.info(f"Status response: {response.status_code}")
        logger.debug(f"Response: {response.text}")

        if response.status_code != 200:
            logger.error(f"❌ Status check failed")
            return jsonify({"success": False, "error": response.text}), response.status_code

        result = response.json()
        
        if not result.get("success"):
            return jsonify({"success": False, "error": result}), 400

        # API response structure:
        # {"success": true, "data": {"status": "completed", "output": {"video_url": "..."}}}
        
        data = result.get("data", {})
        status = data.get("status", "pending")
        
        # Video URL output-dan almak
        output = data.get("output", {})
        video_url = output.get("video_url")
        
        logger.info(f"Task status: {status}")
        
        if video_url:
            logger.info(f"Video URL: {video_url}")
        
        # Cache-a goş
        if status == "completed" and video_url:
            video_cache[task_id] = {
                'url': video_url,
                'timestamp': time.time()
            }
            logger.info(f"✅ Video cached!")

        return jsonify({
            "success": True, 
            "status": status, 
            "video_url": video_url  # Frontend üçin
        })

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download/<task_id>')
def download_video(task_id):
    """Wideony göçürmek"""
    logger.info(f"⬇️ Download request: {task_id}")
    
    try:
        if task_id not in video_cache:
            return jsonify({'success': False, 'error': 'Video tapylmady'}), 404
        
        video_url = video_cache[task_id]['url']
        
        # Download video
        video_resp = requests.get(video_url, timeout=90, stream=True)
        
        if video_resp.status_code != 200:
            return jsonify({'success': False, 'error': 'Video göçürilmedi'}), 500
        
        filename = f"{task_id}.mp4"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            for chunk in video_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"✅ Downloaded: {filename}")
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/history')
def history():
    """Wideo taryhy"""
    logger.info("📚 History request")
    
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
    logger.info("🚀 AI Video Generator - xAI Grok-Imagine")
    logger.info(f"API: {API_GENERATE_URL}")
    logger.info("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
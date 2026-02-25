# app.py
from flask import Flask, render_template, request, jsonify, send_file
import requests
import time
import os
from datetime import datetime
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'static/outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 512 * 512  # 16MB max file size

# Papkalary döret
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

API_TOKEN = "sk-0e91d3e7e771ac5d9475213773fd7d3b5"
API_URL = "https://api.unifically.com/higgsfield/generate"

# Predefined motion templates
MOTION_TEMPLATES = {
    "zoom_in": {
        "id": "d2389a9a-91c2-4276-bc9c-c9e35e8fb85a",
        "name": "Zoom In",
        "icon": "🔍",
        "description": "Surata ýakynlaşma effekti"
    },
    "pan_right": {
        "id": "e3490b1b-02d3-5387-cd0d-d0f46f9fc96b",
        "name": "Pan Right",
        "icon": "➡️",
        "description": "Saga hereket edýän kamera"
    },
    "rotate": {
        "id": "f4501c2c-13e4-6498-de1e-e1g57g0gd07c",
        "name": "Rotate",
        "icon": "🔄",
        "description": "Aýlanma effekti"
    },
    "zoom_out": {
        "id": "a1278h8h-80a1-3165-ab9b-b8d24d7ea74h",
        "name": "Zoom Out",
        "icon": "🔎",
        "description": "Suratdan daşlaşma"
    }
}

@app.route('/')
def index():
    return render_template('index.html', motion_templates=MOTION_TEMPLATES)

@app.route('/generate', methods=['POST'])
def generate_video():
    try:
        data = request.get_json()
        
        prompt = data.get('prompt', '')
        image_url = data.get('image_url', '')
        model = data.get('model', 'lite')
        motion_id = data.get('motion_id', 'd2389a9a-91c2-4276-bc9c-c9e35e8fb85a')
        enhance_prompt = data.get('enhance_prompt', False)
        seed = data.get('seed', int(time.time()))
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt gerek!'}), 400
            
        if not image_url:
            return jsonify({'success': False, 'error': 'Surat URL gerek!'}), 400
        
        payload = {
            "prompt": prompt,
            "start_image_url": image_url,
            "model": model,
            "motion_id": motion_id,
            "enhance_prompt": enhance_prompt,
            "seed": seed
        }
        
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(API_URL, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code != 200 or not response_data.get("success", False):
            return jsonify({'success': False, 'error': response_data}), 400
        
        task_id = response_data["data"]["task_id"]
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Wideo döredilýär...'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/status/<task_id>')
def check_status(task_id):
    try:
        status_url = f"https://api.unifically.com/higgsfield/feed/{task_id}"
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        status_resp = requests.get(status_url, headers=headers)
        status_data = status_resp.json()
        
        task_status = status_data["data"]["status"]
        
        response = {
            'success': True,
            'status': task_status
        }
        
        if task_status == "completed":
            video_url = status_data["data"]["video_url"]
            
            # Wideony göçür
            filename = f"video_{task_id}_{int(time.time())}.mp4"
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            
            video_resp = requests.get(video_url)
            with open(filepath, 'wb') as f:
                f.write(video_resp.content)
            
            response['video_url'] = f'/static/outputs/{filename}'
            response['download_url'] = f'/download/{filename}'
            
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_video(filename):
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/history')
def get_history():
    try:
        videos = []
        for filename in os.listdir(app.config['OUTPUT_FOLDER']):
            if filename.endswith('.mp4'):
                filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                videos.append({
                    'filename': filename,
                    'url': f'/static/outputs/{filename}',
                    'download_url': f'/download/{filename}',
                    'size': os.path.getsize(filepath),
                    'created': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        videos.sort(key=lambda x: x['created'], reverse=True)
        return jsonify({'success': True, 'videos': videos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
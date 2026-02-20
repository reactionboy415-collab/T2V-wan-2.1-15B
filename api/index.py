from flask import Flask, request, jsonify
import httpx
import json
import random
import string
import time

app = Flask(__name__)

# Constants
BASE_URL = "https://luca115-wan2-2-fp8da-aoti.hf.space/gradio_api"
NEG_PROMPT = "色调艳丽, 过曝, 静态, 细节模糊不清, 字幕, 风格, 作品, 画作, 画面, 静止, 整体发灰, 最差质量, 低质量, JPEG压缩残留, 丑陋的, 残缺的, 多余的手指, 画得不好的手部, 画得不好的脸部, 畸形的, 毁容 of, 形态畸形的肢体, 手指融合, 静止不动的画面, 杂乱的背景, 三条腿, 背景人很多, 倒着走"

def gen_hash():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))

@app.route('/')
def home():
    return jsonify({"status": "ready", "engine": "Wan 2.1 Video API"}), 200

@app.route('/generate')
def generate_video():
    prompt = request.args.get('p')
    if not prompt:
        return jsonify({"error": "Prompt 'p' is required"}), 400

    session_hash = gen_hash()
    headers = {
        "x-gradio-user": "api",
        "content-type": "application/json",
        "origin": "https://upsampler.com",
        "referer": "https://upsampler.com/"
    }

    payload = {
        "data": [prompt, NEG_PROMPT, 5, 1, 3, 4, 42, True],
        "event_data": None,
        "fn_index": 0,
        "session_hash": session_hash
    }

    try:
        # Step 1: Join Queue
        with httpx.Client(http2=True, timeout=120.0) as client:
            join_resp = client.post(f"{BASE_URL}/queue/join", headers=headers, json=payload)
            if join_resp.status_code != 200:
                return jsonify({"error": "Failed to join queue"}), 500

            # Step 2: Listen for the result link (Polling/Streaming)
            data_url = f"{BASE_URL}/queue/data?session_hash={session_hash}"
            
            # We poll the stream until 'process_completed' appears
            with client.stream("GET", data_url, headers=headers) as r:
                for line in r.iter_lines():
                    if "process_completed" in line:
                        # Parsing the SSE data format
                        json_str = line.replace("data: ", "").strip()
                        data = json.loads(json_str)
                        
                        # Extracting the video URL
                        video_url = data['output']['data'][0]['video']['url']
                        
                        return jsonify({
                            "success": True,
                            "prompt": prompt,
                            "video_url": video_url,
                            "session_hash": session_hash
                        }), 200
                        
            return jsonify({"error": "Stream closed without completion"}), 504

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# For Vercel deployment
app.debug = True

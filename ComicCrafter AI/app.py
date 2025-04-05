import os
import time
import base64
import requests
from io import BytesIO
from PIL import Image
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

HF_API_KEY = os.environ.get("HF_API_KEY") or "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"

headers = {
    "Authorization": f"Bearer {HF_API_KEY}"
}


def generate_story(prompt):
    payload = {
        "inputs": f"Write a 4-panel comic story about: {prompt}\nSeparate each panel with ---",
        "parameters": {"max_new_tokens": 300}
    }
    response = requests.post(
        "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct",
        headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"Story generation failed: {response.text}")

    return response.json()[0]["generated_text"].split("---")


def generate_image(prompt):
    payload = {
        "inputs": prompt,
    }
    response = requests.post(
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"Image generation failed: {response.text}")

    image_bytes = response.content
    return Image.open(BytesIO(image_bytes))


def create_comic_strip(images):
    widths, heights = zip(*(img.size for img in images if img is not None))
    total_height = sum(heights)
    max_width = max(widths)

    comic = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))

    y_offset = 0
    for img in images:
        comic.paste(img, (0, y_offset))
        y_offset += img.height

   
    if not os.path.exists("static"):
        os.makedirs("static")

    filename = f"static/comic_{int(time.time())}.png"
    comic.save(filename, format="PNG")

    
    buffered = BytesIO()
    comic.save(buffered, format="PNG")
    encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return encoded, filename


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate_comic", methods=["POST"])
def generate_comic():
    try:
        data = request.get_json()
        prompt = data["prompt"]

        
        panel_texts = generate_story(prompt)

        
        images = []
        for i, panel in enumerate(panel_texts):
            try:
                img = generate_image(panel)
                images.append(img)
            except Exception as e:
                print(f"Image generation failed for panel {i+1}: {e}")
                images.append(Image.new("RGB", (512, 512), color=(200, 200, 200)))

        
        comic_base64, filename = create_comic_strip(images)

        return jsonify({
            "script": "---".join(panel_texts),
            "comic_strip": comic_base64,
            "filename": filename
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

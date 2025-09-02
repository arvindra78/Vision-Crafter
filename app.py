from flask import Flask, request, jsonify, render_template, send_from_directory
import together
import logging
from urllib.parse import urlparse
import requests
import os

app = Flask(__name__)

# Base builder configuration
BASE_BUILDER_CONFIG = {
    "baseBuilder": {
        "allowedAddresses": ["0x723068d6AA8bE4eD97311455066d0E6a0c9A0729"]
    }
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Together API client
try:
    together.api_key = "tgp_v1_UEGfPv24aifWIfPxHeeOtrdjg5YYlrdSISLoDh5NGX4"
    client = together.Together()
except Exception as e:
    logger.error(f"Failed to initialize Together client: {str(e)}")
    raise

def is_valid_together_url(url):
    try:
        parsed = urlparse(url)
        return parsed.netloc.endswith('together.ai') and (
            parsed.path.startswith('/shrt/') or 
            parsed.path.startswith('/files/')
        )
    except:
        return False

def sanitize_image_url(url):
    if not url:
        return None
    if url.startswith('https:/') and not url.startswith('https://'):
        url = url.replace('https:/', 'https://')
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    return url if is_valid_together_url(url) else None

def verify_image_url(url):
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            return content_type.startswith('image/')
        return False
    except Exception as e:
        logger.warning(f"URL verification failed: {str(e)}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/enhance', methods=['POST'])
def enhance_prompt():
    """Enhance user prompt using Together text model"""
    data = request.get_json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Please enter a prompt"}), 400

    try:
        logger.info(f"Enhancing prompt: {prompt}")

        response = client.chat.completions.create(
    model="lgai/exaone-3-5-32b-instruct",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a prompt enhancer for AI image generation. "
                "Expand the user’s short input into a clean, natural, descriptive sentence. "
                "Do not use markdown, headings, bullet points, or labels like 'Subject', 'Description'. "
                "Output should be a single descriptive prompt only."
            )
        },
        {"role": "user", "content": prompt}
    ],
    max_tokens=120
)


        enhanced_prompt = response.choices[0].message.content.strip()
        logger.info(f"Enhanced prompt: {enhanced_prompt}")

        return jsonify({"enhanced_prompt": enhanced_prompt})

    except Exception as e:
        logger.error(f"Error enhancing prompt: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to enhance prompt", "details": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.get_json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Please enter a description for your image"}), 400

    try:
        logger.info(f"Generating image for prompt: {prompt}")
        
        response = client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            steps=4,
            n=1
        )

        if not response.data or not response.data[0].url:
            return jsonify({"error": "No image URL returned"}), 500

        image_url = sanitize_image_url(response.data[0].url)
        if not image_url or not verify_image_url(image_url):
            return jsonify({"error": "Invalid image URL"}), 500

        return jsonify({"image_url": image_url, "prompt": prompt})

    except Exception as e:
        logger.error(f"Error generating image: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to generate image", "details": str(e)}), 500

@app.route('/farcaster.json')
def serve_farcaster_manifest():
    return send_from_directory('.', 'farcaster.json', mimetype='application/json')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)



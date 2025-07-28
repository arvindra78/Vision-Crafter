from flask import Flask, request, jsonify, render_template
from together import Together
import logging
from urllib.parse import urlparse
import requests

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Together API client
client = Together(api_key="tgp_v1_UEGfPv24aifWIfPxHeeOtrdjg5YYlrdSISLoDh5NGX4")

def is_valid_together_url(url):
    """Check if the URL is from Together.ai's domain"""
    try:
        parsed = urlparse(url)
        # Allow Together.ai short URLs (shrt) and their CDN URLs
        return parsed.netloc.endswith('together.ai') and (
            parsed.path.startswith('/shrt/') or 
            parsed.path.startswith('/files/')
        )
    except:
        return False

def sanitize_image_url(url):
    """Ensure the URL has proper https protocol and is valid."""
    if not url:
        return None
        
    # Fix common URL issues
    if url.startswith('https:/') and not url.startswith('https://'):
        url = url.replace('https:/', 'https://')
    
    # Ensure proper https protocol
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    return url if is_valid_together_url(url) else None

def verify_image_url(url):
    """Verify the URL actually returns an image"""
    try:
        # Send HEAD request to check content type without downloading
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
    """Render the main page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    """Generate image from text prompt using Together API."""
    data = request.get_json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        logger.warning("Empty prompt received")
        return jsonify({"error": "Please enter a description for your image"}), 400

    try:
        logger.info(f"Generating image for prompt: {prompt}")
        
        # Generate image using Together API
        response = client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            steps=4,
            n=1
        )

        logger.debug(f"API Response: {response}")

        if not response.data or not response.data[0].url:
            logger.error("No image URL in API response")
            return jsonify({"error": "The API didn't return an image. Please try again."}), 500

        # Sanitize the image URL
        image_url = sanitize_image_url(response.data[0].url)
        
        if not image_url:
            logger.error(f"Invalid image URL format received: {response.data[0].url}")
            return jsonify({"error": "Received an invalid image URL format from the API."}), 500

        # Verify the URL actually points to an image
        if not verify_image_url(image_url):
            logger.error(f"URL doesn't point to valid image: {image_url}")
            return jsonify({"error": "The generated image URL is not accessible. Please try again."}), 500

        logger.info(f"Successfully generated image at: {image_url}")
        return jsonify({
            "image_url": image_url,
            "prompt": prompt  # Return the prompt for reference
        })

    except Exception as e:
        logger.error(f"Error generating image: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to generate image. Please try again later.",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
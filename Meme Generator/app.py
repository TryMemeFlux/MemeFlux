import gradio as gr
import json
import re
import random
import os
from datetime import datetime, timedelta
import google.generativeai as genai
import fal_client
from pydantic import BaseModel
import time

# Load API keys from environment variables
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FAL_KEY = os.environ.get('FAL_KEY')

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

class MemeResponse(BaseModel):
    image_url: str
    top_text: str
    bottom_text: str

def get_ist_time():
    """Returns current time in IST for logging."""
    utc_time = datetime.utcnow()
    ist_time = utc_time + timedelta(hours=5, minutes=30)
    return ist_time.strftime("%d-%m-%Y %H:%M:%S IST")

def generate_meme(domain: str) -> MemeResponse:
    """Generates a meme using Gemini for text and Flux.ai for the image."""
    temperature = round(random.uniform(0.7, 1.0), 2)
    print(f"Temperature: {temperature}")

    model = genai.GenerativeModel("gemini-1.5-flash")
    system_content = "You are a helpful meme maker who creates non-offensive, unique, and funny memes."
    user_content = (
        f"Create a unique and funny meme for the topic '{domain}'. "
        "Ensure the scene description accurately reflects the topic, including specific details like animals or objects mentioned. "
        "For example, if the topic is 'cute cat', the description must prominently feature a cute cat. "
        "Provide a detailed scene description without text for the image, and include top and bottom text for the meme. "
        "Return the meme details in this JSON format:\n"
        '{{"stableDiffusionPrompt": "detailed scene description here", "topText": "top text here", "bottomText": "bottom text here"}}\n'
        "Ensure all fields are filled and return only the JSON object."
    )
    prompt = f"{system_content}\n\n{user_content}"

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json"
            )
        )
        print(f"Raw Gemini API response: {response.text}")

        result = response.text
        try:
            meme_data = json.loads(result)
        except json.JSONDecodeError:
            json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
            if json_match:
                meme_data = json.loads(json_match.group(1))
            else:
                raise ValueError("No valid JSON found in response")

        print(f"Parsed meme_data: {meme_data}")
        print("Meme subject:", domain)
        print("Meme Generated on:", get_ist_time())
        print("Image Prompt:", meme_data['stableDiffusionPrompt'])
        print("Top Text:", meme_data['topText'])
        print("Bottom Text:", meme_data['bottomText'])

        fal_client.api_key = FAL_KEY
        handler = fal_client.submit(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": meme_data['stableDiffusionPrompt'],
                "image_size": "landscape_4_3",
                "num_inference_steps": 4,
                "num_images": 1,
                "enable_safety_checker": True
            }
        )

        result = handler.get()
        print("Flux.ai response:", result)
        image_url = result['images'][0]['url']
        print("Generated Image URL:", image_url)

        return MemeResponse(
            top_text=meme_data['topText'],
            image_url=image_url,
            bottom_text=meme_data['bottomText']
        )

    except Exception as e:
        print(f"Error generating meme: {str(e)}")
        raise

def generate_meme_gradio(domain):
    """Wrapper for Gradio interface."""
    try:
        meme_response = generate_meme(domain)
        return meme_response.top_text, meme_response.image_url, meme_response.bottom_text
    except Exception as e:
        return "Error", None, f"Failed to generate meme: {str(e)}"

# Check if logo file exists locally (for debugging)
logo_path = "logo11.jpg"
if os.path.exists(logo_path):
    print(f"Logo file found at: {logo_path}")
else:
    print(f"Logo file NOT found at: {logo_path}")

# Set up the Gradio interface with logo beneath buttons
demo = gr.Interface(
    fn=generate_meme_gradio,
    inputs=[gr.Textbox(label="Enter your meme topic", placeholder="e.g., cute cat")],
    outputs=[gr.Textbox(label="Top Text"), gr.Image(label="Generated Meme Image"), gr.Textbox(label="Bottom Text")],
    title="<h1>MemeFlux Meme Generator</h1>",
    description="""
    <p style='text-align: center;'>Enter a topic to generate a meme with a futuristic twist.</p>
    <div style='text-align: center; margin-top: 20px;'>
        <img src='/file=logo11.jpg' style='max-width: 200px; height: auto;' alt='MemeFlux Logo' onerror='this.style.display=\"none\"; this.nextSibling.style.display=\"block\";'>
        <span style='display:none; color:#ff00ff;'>Logo not found - check file path</span>
    </div>
    """,
    css="style.css",
    allow_flagging="never"
)

# Launch the app with debug output
print("Launching Gradio interface with logo...")
demo.launch(debug=True)
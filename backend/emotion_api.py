import os
import base64
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Microsoft Emotion API endpoint and key
EMOTION_API_ENDPOINT = os.getenv("EMOTION_API_ENDPOINT", 
                                "https://prince-hack.cognitiveservices.azure.com/")
EMOTION_API_KEY = os.getenv("EMOTION_API_KEY", "CoVawT49HTuNStWtjSOCa48M2xPXVlAh5fdbmHbZ2DKoX6LFcQCLJQQJ99BCACYeBjFXJ3w3AAAKACOGYVxz")

def detect_emotion(image_base64):
    """
    Detect the primary emotion from a facial image using Microsoft Emotion API.
    
    Args:
        image_base64: Base64 encoded image data
    
    Returns:
        String representing the dominant emotion (happy, sad, angry, etc.)
    """
    try:
        # Convert base64 to binary
        image_data = base64.b64decode(image_base64)
        
        # Set up the API request
        headers = {
            'Content-Type': 'application/octet-stream',
            'Ocp-Apim-Subscription-Key': EMOTION_API_KEY
        }
        
        params = {
            'returnFaceId': 'false',
            'returnFaceLandmarks': 'false',
            'returnFaceAttributes': 'emotion'
        }
        
        # Make the API request
        response = requests.post(
            EMOTION_API_ENDPOINT,
            headers=headers,
            params=params,
            data=image_data
        )
        
        # If request was not successful, raise exception
        response.raise_for_status()
        
        # Parse the response
        faces = response.json()
        
        # If no faces detected, return neutral
        if not faces:
            print("No faces detected in the image")
            return "neutral"
        
        # Get the emotions from the first detected face
        emotions = faces[0]['faceAttributes']['emotion']
        
        # Find the emotion with the highest score
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
        
        # Map API emotion names to our simplified set if needed
        emotion_mapping = {
            'happiness': 'happy',
            'sadness': 'sad',
            'anger': 'angry',
            'surprise': 'surprised',
            'fear': 'fearful',
            'disgust': 'disgusted',
            'contempt': 'contempt',
            'neutral': 'neutral'
        }
        
        return emotion_mapping.get(dominant_emotion, dominant_emotion)
        
    except Exception as e:
        print(f"Error in emotion detection: {str(e)}")
        
        # Mock implementation for development or when API is not available
        # In a production environment, you'd want to handle the error more appropriately
        print("Using mock emotion detection since API call failed")
        import random
        emotions = ['happy', 'sad', 'neutral', 'surprised']
        return random.choice(emotions)
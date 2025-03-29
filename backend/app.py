from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import json
import requests
from PIL import Image
import io
import numpy as np
from datetime import datetime

# Import custom modules
from emotion_api import detect_emotion_from_image
from heart_rate_sensor import get_heart_rate
from spotify_api import get_spotify_client, get_user_top_genres, get_recently_played
from playlist_logic import generate_playlist_based_on_mood

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
import logging
logging.basicConfig(
    filename='data/logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MOOD_MAPPING = {
    'happy': {'energy': 0.7, 'valence': 0.8, 'instrumentalness': 0.2},
    'sad': {'energy': 0.4, 'valence': 0.3, 'instrumentalness': 0.4},
    'angry': {'energy': 0.8, 'valence': 0.3, 'instrumentalness': 0.2},
    'relaxed': {'energy': 0.3, 'valence': 0.6, 'instrumentalness': 0.5},
    'energetic': {'energy': 0.9, 'valence': 0.7, 'instrumentalness': 0.1},
    'focused': {'energy': 0.5, 'valence': 0.5, 'instrumentalness': 0.7}
}

# Goal-based adjustments
GOAL_ADJUSTMENTS = {
    'increase_energy': {'energy': 0.2, 'valence': 0.1},
    'calm_down': {'energy': -0.2, 'valence': 0.0, 'instrumentalness': 0.2},
    'stay_same': {'energy': 0.0, 'valence': 0.0, 'instrumentalness': 0.0}
}

# Context adjustments
CONTEXT_ADJUSTMENTS = {
    'working': {'energy': -0.1, 'instrumentalness': 0.3},
    'exercising': {'energy': 0.3, 'instrumentalness': -0.2},
    'relaxing': {'energy': -0.3, 'valence': 0.1, 'instrumentalness': 0.1},
    'socializing': {'energy': 0.1, 'valence': 0.2},
    'studying': {'energy': -0.1, 'instrumentalness': 0.4, 'valence': -0.1}
}

@app.route("/")
def home():
    """Serve the home page"""
    return "Mood-based Music Recommender API"

@app.route("/detect_emotion", methods=["POST"])
def detect_emotion():
    """
    Detect emotion from facial image and heart rate
    
    Expects:
    - image: Base64 encoded image or file upload
    - heart_rate: (Optional) Heart rate in BPM
    
    Returns:
    - Detected mood and confidence scores
    """
    try:
        data = {}
        
        # Handle image from request
        if 'image' in request.files:
            # Handle file upload
            image_file = request.files['image']
            image_bytes = image_file.read()
            image = Image.open(io.BytesIO(image_bytes))
        elif request.json and 'image_base64' in request.json:
            # Handle base64 encoded image
            import base64
            image_data = base64.b64decode(request.json['image_base64'])
            image = Image.open(io.BytesIO(image_data))
        else:
            return jsonify({"error": "No image provided"}), 400
        
        # Get heart rate data
        if request.json and 'heart_rate' in request.json:
            heart_rate = request.json['heart_rate']
        else:
            # Attempt to read from sensor if available
            try:
                heart_rate = get_heart_rate()
            except Exception as e:
                logger.warning(f"Could not get heart rate from sensor: {str(e)}")
                heart_rate = None
        
        # Detect emotion from image
        emotion_results = detect_emotion_from_image(image)
        
        # Combine emotion results with heart rate for more accurate assessment
        # This is a simplified version - in production, you'd use a more sophisticated model
        final_mood = emotion_results['dominant_emotion']
        confidence = emotion_results['confidence']
        
        # If heart rate is available, adjust the mood assessment
        if heart_rate:
            # High heart rate might indicate excitement/stress
            if heart_rate > 100 and final_mood in ['relaxed', 'sad']:
                # Adjust confidence in the current mood
                confidence *= 0.8
                # Check secondary emotions
                if 'secondary_emotions' in emotion_results:
                    for emotion, score in emotion_results['secondary_emotions'].items():
                        if emotion in ['excited', 'stressed', 'energetic']:
                            if score * 1.2 > confidence:
                                final_mood = emotion
                                confidence = score * 1.2
        
        # Log the detection
        logger.info(f"Emotion detected: {final_mood} with confidence {confidence}")
        
        return jsonify({
            "mood": final_mood,
            "confidence": confidence,
            "heart_rate": heart_rate,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in emotion detection: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/recommend_music", methods=["POST"])
def recommend_music():
    """
    Recommend music based on detected mood, user goals, and context
    
    Expects:
    - mood: Detected mood (happy, sad, etc.)
    - goal: User goal (increase_energy, calm_down, stay_same)
    - context: What user is doing (working, exercising, etc.)
    - custom_mood: (Optional) User-selected mood if they feel different
    
    Returns:
    - Recommended playlist with tracks
    """
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract parameters
        mood = data.get('mood')
        goal = data.get('goal', 'stay_same')
        context = data.get('context', None)
        custom_mood = data.get('custom_mood', None)
        
        # If user specified they feel different, use their custom mood
        if custom_mood:
            mood = custom_mood
        
        # Validate mood
        if mood not in MOOD_MAPPING:
            return jsonify({"error": f"Invalid mood: {mood}. Supported moods: {list(MOOD_MAPPING.keys())}"}), 400
        
        # Get Spotify client
        spotify = get_spotify_client()
        
        # Get user's music preferences
        top_genres = get_user_top_genres(spotify)
        recently_played = get_recently_played(spotify)
        
        # Start with base mood parameters
        params = MOOD_MAPPING[mood].copy()
        
        # Apply goal adjustments
        if goal in GOAL_ADJUSTMENTS:
            for param, adjustment in GOAL_ADJUSTMENTS[goal].items():
                if param in params:
                    params[param] = min(1.0, max(0.0, params[param] + adjustment))
        
        # Apply context adjustments
        if context and context in CONTEXT_ADJUSTMENTS:
            for param, adjustment in CONTEXT_ADJUSTMENTS[context].items():
                if param in params:
                    params[param] = min(1.0, max(0.0, params[param] + adjustment))
        
        # Generate playlist
        playlist = generate_playlist_based_on_mood(
            spotify=spotify,
            mood_params=params,
            top_genres=top_genres,
            recently_played=recently_played
        )
        
        # Log the recommendation
        logger.info(f"Recommended playlist for mood: {mood}, goal: {goal}, context: {context}")
        
        response = {
            "mood": mood,
            "goal": goal,
            "context": context,
            "playlist": playlist,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in music recommendation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/user_feedback", methods=["POST"])
def user_feedback():
    """
    Handle user feedback to improve future recommendations
    
    Expects:
    - playlist_id: ID of the recommended playlist
    - rating: User rating (1-5)
    - feedback_text: (Optional) Text feedback
    - song_ratings: (Optional) Ratings for individual songs
    
    Returns:
    - Confirmation of feedback received
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No feedback data provided"}), 400
        
        # Extract feedback data
        playlist_id = data.get('playlist_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback_text', '')
        song_ratings = data.get('song_ratings', {})
        
        # Validate data
        if not playlist_id or not rating:
            return jsonify({"error": "Missing required feedback parameters"}), 400
        
        # Log feedback
        logger.info(f"User feedback for playlist {playlist_id}: Rating {rating}")
        
        # Store feedback (in a production app, you'd save this to a database)
        feedback_data = {
            "playlist_id": playlist_id,
            "rating": rating,
            "feedback_text": feedback_text,
            "song_ratings": song_ratings,
            "timestamp": datetime.now().isoformat()
        }
        
        # Here you would typically store this in a database
        # For now, we'll just log it
        logger.info(f"Feedback data: {json.dumps(feedback_data)}")
        
        # You could also trigger model re-training or adjustments based on feedback
        
        return jsonify({"message": "Feedback received successfully"})
        
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/sensor/heartrate", methods=["POST"])
def receive_heartrate():
    """
    Endpoint to receive heart rate data from the sensor
    
    Expects:
    - heart_rate: Heart rate in BPM
    - timestamp: When the reading was taken
    
    Returns:
    - Confirmation of data received
    """
    try:
        data = request.json
        
        if not data or 'heart_rate' not in data:
            return jsonify({"error": "No heart rate data provided"}), 400
        
        heart_rate = data['heart_rate']
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Log the heart rate data
        logger.info(f"Heart rate received: {heart_rate} BPM at {timestamp}")
        
        # Store the data for future use
        # In a production app, you'd save this to a database
        
        return jsonify({
            "message": "Heart rate data received",
            "heart_rate": heart_rate,
            "timestamp": timestamp
        })
        
    except Exception as e:
        logger.error(f"Error processing heart rate data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Ensure log directory exists
    os.makedirs('data/logs', exist_ok=True)
    
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=True)
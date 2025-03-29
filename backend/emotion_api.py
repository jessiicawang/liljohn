import os
import requests
import json
import logging
import numpy as np
from datetime import datetime
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from PIL import Image
import io

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../data/logs/emotion_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('emotion_api')

class EmotionDetector:
    def __init__(self):
        # Load configuration from environment variables
        self.face_api_key = os.environ.get('MICROSOFT_FACE_API_KEY')
        self.face_api_endpoint = os.environ.get('MICROSOFT_FACE_API_ENDPOINT')
        
        if not self.face_api_key or not self.face_api_endpoint:
            logger.error("Microsoft Face API credentials not found in environment variables")
            raise ValueError("Missing Microsoft Face API credentials")
        
        # Initialize the Face client
        self.face_client = FaceClient(
            self.face_api_endpoint,
            CognitiveServicesCredentials(self.face_api_key)
        )
        
        # Emotion mapping constants
        self.EMOTION_MAP = {
            'anger': {'valence': 0.1, 'energy': 0.8, 'tempo': 'high'},
            'contempt': {'valence': 0.3, 'energy': 0.5, 'tempo': 'medium'},
            'disgust': {'valence': 0.2, 'energy': 0.6, 'tempo': 'medium-high'},
            'fear': {'valence': 0.2, 'energy': 0.7, 'tempo': 'high'},
            'happiness': {'valence': 0.9, 'energy': 0.7, 'tempo': 'medium-high'},
            'neutral': {'valence': 0.5, 'energy': 0.5, 'tempo': 'medium'},
            'sadness': {'valence': 0.2, 'energy': 0.2, 'tempo': 'low'},
            'surprise': {'valence': 0.7, 'energy': 0.8, 'tempo': 'high'},
        }
        
        logger.info("Emotion Detector initialized successfully")
    
    def detect_emotion_from_image(self, image_path=None, image_bytes=None):
        """
        Detect emotions from an image using Microsoft Face API
        
        Args:
            image_path (str, optional): Path to image file
            image_bytes (bytes, optional): Image as bytes
            
        Returns:
            dict: Detected emotions with confidence scores and music parameters
        """
        try:
            if image_path:
                # Open image from file path
                with open(image_path, 'rb') as image_file:
                    image_content = image_file.read()
            elif image_bytes:
                # Use provided image bytes
                image_content = image_bytes
            else:
                logger.error("No image provided")
                return {'error': 'No image provided'}
            
            # Detect faces and analyze emotions
            face_attributes = ['emotion']
            detected_faces = self.face_client.face.detect_with_stream(
                image=io.BytesIO(image_content),
                return_face_attributes=face_attributes
            )
            
            if not detected_faces:
                logger.warning("No faces detected in the image")
                return {'primary_emotion': 'neutral', 'music_params': self.EMOTION_MAP['neutral']}
            
            # Get emotions from the first detected face
            face = detected_faces[0]
            emotions = face.face_attributes.emotion
            
            # Convert emotion scores to dictionary
            emotion_scores = {
                'anger': emotions.anger,
                'contempt': emotions.contempt,
                'disgust': emotions.disgust,
                'fear': emotions.fear,
                'happiness': emotions.happiness,
                'neutral': emotions.neutral,
                'sadness': emotions.sadness,
                'surprise': emotions.surprise
            }
            
            # Find the emotion with highest confidence
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            highest_score = emotion_scores[primary_emotion]
            
            # Create result object with music parameters
            result = {
                'primary_emotion': primary_emotion,
                'confidence': highest_score,
                'all_emotions': emotion_scores,
                'music_params': self.EMOTION_MAP[primary_emotion],
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Detected primary emotion: {primary_emotion} with confidence: {highest_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in emotion detection: {str(e)}")
            return {'error': str(e)}
    
    def combine_sensor_data(self, face_emotion, heart_rate):
        """
        Combine facial emotion data with heart rate sensor data for better emotion detection
        
        Args:
            face_emotion (dict): Emotion data from facial recognition
            heart_rate (int): Heart rate in BPM
            
        Returns:
            dict: Combined emotion assessment with music parameters
        """
        try:
            # Check if face emotion detection had an error
            if 'error' in face_emotion:
                logger.warning(f"Using only heart rate data due to face detection error: {face_emotion['error']}")
                return self._get_emotion_from_heart_rate(heart_rate)
            
            primary_emotion = face_emotion['primary_emotion']
            emotion_confidence = face_emotion['confidence']
            
            # Adjust emotion based on heart rate
            adjusted_emotion = self._adjust_emotion_with_heart_rate(primary_emotion, emotion_confidence, heart_rate)
            
            # Get music parameters for the adjusted emotion
            music_params = self._calculate_music_parameters(adjusted_emotion, heart_rate)
            
            result = {
                'primary_emotion': adjusted_emotion,
                'face_emotion': face_emotion['primary_emotion'],
                'heart_rate': heart_rate,
                'music_params': music_params,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Combined emotion assessment: {adjusted_emotion} (HR: {heart_rate} BPM)")
            return result
            
        except Exception as e:
            logger.error(f"Error combining sensor data: {str(e)}")
            return {'error': str(e)}
    
    def _adjust_emotion_with_heart_rate(self, emotion, confidence, heart_rate):
        """
        Adjust detected emotion based on heart rate
        
        Args:
            emotion (str): Primary emotion from facial detection
            confidence (float): Confidence score for the emotion
            heart_rate (int): Heart rate in BPM
            
        Returns:
            str: Adjusted emotion
        """
        # Heart rate thresholds
        # These thresholds should be calibrated based on the user's baseline
        RESTING_HR = 70  # Average resting heart rate
        ELEVATED_HR = 90  # Slightly elevated heart rate
        HIGH_HR = 110  # High heart rate
        
        # If confidence is high, trust the facial emotion more
        if confidence > 0.7:
            return emotion
        
        # Adjust based on heart rate if facial confidence is not high
        if heart_rate > HIGH_HR:
            # High heart rate could indicate excitement, fear, anger, or exercise
            if emotion in ['neutral', 'sadness', 'contempt']:
                # Facial expression doesn't match high heart rate, adjust
                return 'excitement' if heart_rate > 120 else 'stress'
                
        elif heart_rate < RESTING_HR:
            # Low heart rate suggests calm or relaxed state
            if emotion in ['anger', 'fear', 'surprise']:
                # Facial expression doesn't match low heart rate, adjust
                return 'neutral'
                
        # Default: return original emotion
        return emotion
    
    def _get_emotion_from_heart_rate(self, heart_rate):
        """
        Estimate emotion based only on heart rate when facial detection fails
        
        Args:
            heart_rate (int): Heart rate in BPM
            
        Returns:
            dict: Estimated emotion with music parameters
        """
        # Basic estimation - could be improved with more advanced models
        if heart_rate > 110:
            emotion = 'excitement'
            music_params = {'valence': 0.8, 'energy': 0.8, 'tempo': 'high'}
        elif heart_rate > 90:
            emotion = 'stress'
            music_params = {'valence': 0.4, 'energy': 0.7, 'tempo': 'medium-high'}
        elif heart_rate > 70:
            emotion = 'neutral'
            music_params = {'valence': 0.5, 'energy': 0.5, 'tempo': 'medium'}
        else:
            emotion = 'relaxed'
            music_params = {'valence': 0.6, 'energy': 0.3, 'tempo': 'low'}
        
        return {
            'primary_emotion': emotion,
            'face_emotion': 'unknown',
            'heart_rate': heart_rate,
            'music_params': music_params,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_music_parameters(self, emotion, heart_rate):
        """
        Calculate Spotify music parameters based on emotion and heart rate
        
        Args:
            emotion (str): Detected emotion
            heart_rate (int): Heart rate in BPM
            
        Returns:
            dict: Music parameters for Spotify API
        """
        # Start with base parameters from emotion map
        if emotion in self.EMOTION_MAP:
            params = self.EMOTION_MAP[emotion].copy()
        else:
            # Default to neutral if emotion not in map
            params = self.EMOTION_MAP['neutral'].copy()
        
        # Fine-tune based on heart rate
        # Higher heart rate -> slightly higher energy
        hr_factor = min(1.0, max(0.0, (heart_rate - 60) / 100))
        params['energy'] = min(1.0, params['energy'] + (hr_factor * 0.2))
        
        # Add target BPM based on emotion and heart rate
        if params['tempo'] == 'low':
            params['target_bpm'] = 70 + (heart_rate - 70) * 0.3
        elif params['tempo'] == 'medium':
            params['target_bpm'] = 90 + (heart_rate - 70) * 0.3
        elif params['tempo'] == 'medium-high':
            params['target_bpm'] = 110 + (heart_rate - 70) * 0.3
        else:  # high
            params['target_bpm'] = 130 + (heart_rate - 70) * 0.3
        
        # Keep BPM in reasonable range
        params['target_bpm'] = min(180, max(60, params['target_bpm']))
        
        return params
    
    def adapt_to_user_goal(self, current_emotion, user_goal, heart_rate=None):
        """
        Adapt music parameters based on user's goal (calm down, energize, maintain)
        
        Args:
            current_emotion (dict): Current emotion assessment
            user_goal (str): 'calm', 'energize', or 'maintain'
            heart_rate (int, optional): Current heart rate
            
        Returns:
            dict: Adjusted music parameters
        """
        # Get current music parameters
        if isinstance(current_emotion, dict) and 'music_params' in current_emotion:
            params = current_emotion['music_params'].copy()
        else:
            # Default parameters if not available
            params = {'valence': 0.5, 'energy': 0.5, 'tempo': 'medium', 'target_bpm': 100}
        
        # Adjust based on user goal
        if user_goal == 'calm':
            params['energy'] = max(0.1, params['energy'] - 0.3)
            params['target_bpm'] = max(60, params.get('target_bpm', 100) - 30)
            params['tempo'] = 'low'
            # Adjust valence to slightly positive for calming
            params['valence'] = 0.6
            
        elif user_goal == 'energize':
            params['energy'] = min(1.0, params['energy'] + 0.3)
            params['target_bpm'] = min(180, params.get('target_bpm', 100) + 30)
            params['tempo'] = 'high'
            # Keep valence relatively high for energizing
            params['valence'] = max(params.get('valence', 0.5), 0.7)
            
        # For 'maintain', keep parameters roughly the same
        
        logger.info(f"Adapted parameters for goal '{user_goal}': {params}")
        return {
            'adapted_goal': user_goal,
            'original_emotion': current_emotion.get('primary_emotion', 'unknown') if isinstance(current_emotion, dict) else 'unknown',
            'music_params': params,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_context_adjusted_params(self, emotion_data, activity, user_goal):
        """
        Adjust music parameters based on user's current activity and goal
        
        Args:
            emotion_data (dict): Current emotion assessment
            activity (str): What the user is doing (e.g., 'working', 'exercising', 'relaxing')
            user_goal (str): How the user wants to feel ('calm', 'energize', 'maintain')
            
        Returns:
            dict: Context-adjusted music parameters
        """
        # Get base parameters from emotion data
        if isinstance(emotion_data, dict) and 'music_params' in emotion_data:
            params = emotion_data['music_params'].copy()
        else:
            # Default parameters if not available
            params = {'valence': 0.5, 'energy': 0.5, 'tempo': 'medium', 'target_bpm': 100}
        
        # Activity-specific adjustments
        if activity == 'working':
            # For work: reduce lyrics, moderate energy
            params['instrumentalness'] = 0.7
            params['energy'] = 0.5
            
        elif activity == 'exercising':
            # For exercise: high energy, clear beat
            params['energy'] = 0.8
            params['target_bpm'] = max(120, params.get('target_bpm', 100))
            params['instrumentalness'] = 0.3
            
        elif activity == 'relaxing':
            # For relaxing: lower energy, potentially more acoustic
            params['energy'] = 0.3
            params['acousticness'] = 0.7
            params['target_bpm'] = min(90, params.get('target_bpm', 100))
            
        elif activity == 'sleeping':
            # For sleeping: very low energy, minimal vocals
            params['energy'] = 0.1
            params['instrumentalness'] = 0.9
            params['target_bpm'] = 60
            
        elif activity == 'socializing':
            # For socializing: higher valence, moderate-high energy
            params['valence'] = 0.8
            params['energy'] = 0.7
            params['popularity'] = 70  # More popular tracks
            
        # Apply user goal adjustments on top of activity adjustments
        goal_adjusted = self.adapt_to_user_goal({'music_params': params}, user_goal)
        
        # Final result
        result = {
            'activity': activity,
            'user_goal': user_goal,
            'original_emotion': emotion_data.get('primary_emotion', 'unknown') if isinstance(emotion_data, dict) else 'unknown',
            'music_params': goal_adjusted['music_params'],
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Context adjusted parameters for {activity}/{user_goal}: {result['music_params']}")
        return result

# Usage example (would be imported by app.py)
if __name__ == "__main__":
    # This is just for testing - actual implementation would be in app.py
    detector = EmotionDetector()
    
    # Test with a local image
    # result = detector.detect_emotion_from_image(image_path="test_image.jpg")
    # print(f"Detected emotion: {result['primary_emotion']}")
    
    # Test with heart rate
    # combined = detector.combine_sensor_data(result, heart_rate=85)
    # print(f"Combined assessment: {combined['primary_emotion']}")
    
    # Test adaptation
    # adapted = detector.adapt_to_user_goal(combined, user_goal="calm")
    # print(f"Adapted for calming: Energy={adapted['music_params']['energy']}")
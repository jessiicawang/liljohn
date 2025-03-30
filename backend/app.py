from flask import Flask, request, redirect, jsonify, session, render_template, send_from_directory
import os
import requests
import base64
import json
import uuid
from dotenv import load_dotenv
from emotion_api import detect_emotion
from spotify_api import get_spotify_tokens, refresh_spotify_token, get_user_profile, get_user_top_genres, get_recently_played, create_spotify_playlist, add_tracks_to_playlist
from playlist_logic import generate_playlist_recommendations

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Flask app
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Spotify API credentials
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "475798783ee1433e9ab36ad3b6ddd1c0")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "afa1eb83dbb24aa5a122381fe5aae9b4")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)

@app.route('/login')
def login():
    """Redirect to Spotify authorization page."""
    # Define the scope of permissions you need
    scope = 'user-read-private user-read-email playlist-modify-private playlist-modify-public user-top-read user-read-recently-played'
    
    # Generate a state value for security
    state = str(uuid.uuid4())
    session['state'] = state

    # Temp log
    app.logger.debug("Generated state: %s", state)
    
    # Construct the authorization URL
    auth_url = (
        f'https://accounts.spotify.com/authorize?response_type=code'
        f'&client_id={CLIENT_ID}'
        f'&scope={scope}'
        f'&redirect_uri={REDIRECT_URI}'
        f'&state={state}'
    )
    
    # Redirect to Spotify's authorization page
    return redirect(auth_url)

@app.route('/detect-emotion', methods=['POST'])
def process_emotion():
    """Process the image and detect emotion using Microsoft Emotion API."""
    try:
        data = request.json
        image_data = data.get('image')
        
        # Remove data URL prefix if present
        if image_data and ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Detect emotion
        emotion = detect_emotion(image_data)
        
        return jsonify({'emotion': emotion})
    except Exception as e:
        print(f"Error detecting emotion: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/exchange-token', methods=['POST'])
def exchange_token():
    """Exchange authorization code for access and refresh tokens."""
    try:
        data = request.json
        code = data.get('code')
        
        if not code:
            return jsonify({'error': 'Authorization code is required'}), 400
        
        # Exchange code for tokens
        token_data = get_spotify_tokens(CLIENT_ID, CLIENT_SECRET, code, REDIRECT_URI)
        
        if 'error' in token_data:
            return jsonify({'error': token_data['error']}), 400
        
        return jsonify({
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_in': token_data['expires_in']
        })
    except Exception as e:
        print(f"Error exchanging token: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/refresh-token', methods=['POST'])
def refresh_token():
    """Refresh the access token using the refresh token."""
    try:
        data = request.json
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400
        
        # Refresh the token
        token_data = refresh_spotify_token(CLIENT_ID, CLIENT_SECRET, refresh_token)
        
        if 'error' in token_data:
            return jsonify({'error': token_data['error']}), 400
        
        return jsonify({
            'access_token': token_data['access_token'],
            'expires_in': token_data['expires_in']
        })
    except Exception as e:
        print(f"Error refreshing token: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/create-playlist', methods=['POST'])
def create_playlist():
    """Create a playlist based on emotion and goal."""
    try:
        data = request.json
        emotion = data.get('emotion', 'neutral')
        goal = data.get('goal', 'maintain')
        access_token = data.get('access_token')
        
        if not access_token:
            return jsonify({'error': 'Access token is required'}), 400
        
        # Get user profile
        user_profile = get_user_profile(access_token)
        user_id = user_profile['id']
        
        # Get user's top genres
        top_genres = get_user_top_genres(access_token)
        
        # Get recently played tracks
        recently_played = get_recently_played(access_token)
        
        # Generate playlist recommendations
        playlist_tracks = generate_playlist_recommendations(
            access_token, 
            emotion=emotion, 
            goal=goal, 
            top_genres=top_genres, 
            recently_played=recently_played
        )
        
        if not playlist_tracks:
            return jsonify({'error': 'Failed to generate playlist recommendations'}), 500
        
        # Create a title for the playlist
        emotion_emoji_map = {
            'happy': '😊', 'sad': '😢', 'angry': '😠', 'surprised': '😮',
            'fearful': '😨', 'disgusted': '🤢', 'contempt': '😒', 'neutral': '😐'
        }
        
        goal_emoji_map = {
            'energize': '⚡', 'maintain': '✨', 'calm': '🌊'
        }
        
        playlist_name = f"{emotion_emoji_map.get(emotion, '🎵')} {emotion.capitalize()} {goal_emoji_map.get(goal, '✨')} Playlist"
        playlist_description = f"Music to {goal} your {emotion} mood. Created with Mood Music."
        
        # Create the playlist
        playlist = create_spotify_playlist(
            access_token, 
            user_id, 
            playlist_name,
            playlist_description,
            public=False
        )
        
        if 'id' not in playlist:
            return jsonify({'error': 'Failed to create playlist'}), 500
        
        # Add tracks to the playlist
        track_uris = [track['uri'] for track in playlist_tracks]
        add_result = add_tracks_to_playlist(access_token, playlist['id'], track_uris)
        
        # Construct the response
        playlist_data = {
            'id': playlist['id'],
            'name': playlist['name'],
            'description': playlist['description'],
            'external_url': playlist['external_urls']['spotify'],
            'images': playlist.get('images', []),
            'tracks': playlist_tracks,
            'playlist_id': playlist['id']
        }
        
        return jsonify(playlist_data)
    except Exception as e:
        print(f"Error creating playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/callback')
def callback():
    """Handle the OAuth callback from Spotify."""
    # Get the authorization code
    code = request.args.get('code')
    state = request.args.get('state')
    stored_state = session.get('state')
    
    # Log the state values for debugging
    app.logger.debug("Returned state: %s", state)
    app.logger.debug("Stored state: %s", stored_state)

    # Validate state to prevent CSRF attacks
    if state != stored_state:
        return jsonify({'error': 'State verification failed'}), 403
    
    # Get tokens using the code
    token_data = get_spotify_tokens(CLIENT_ID, CLIENT_SECRET, code, REDIRECT_URI)
    
    if 'error' in token_data:
        return f"Error: {token_data['error']}"
    
    # Store tokens in session or pass to frontend
    session['access_token'] = token_data['access_token']
    session['refresh_token'] = token_data['refresh_token']

    # Log test
    app.logger.debug("Callback query parameters: %s", request.args)
    
    # Redirect to the app with tokens
    return redirect(f'/?access_token={token_data["access_token"]}&refresh_token={token_data["refresh_token"]}')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
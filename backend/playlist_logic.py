import json
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add more detailed logging in validate_spotify_token
def validate_spotify_token(access_token):
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://api.spotify.com/v1/me',
        headers=headers,
        timeout=10)
        

        logger.info(f"Token validation status: {response.status_code}")
        logger.info(f"Token validation response: {response.text[:200]}")

        if response.status_code == 200:
            logger.info("Token is valid")
            return True
        else:
            logger.error(f"Token validation failed: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return False
    
def test_recommendations_endpoint(access_token):
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'seed_genres': 'pop', 'limit': 1}
        response = requests.get(
            'https://api.spotify.com/v1/recommendations',
            headers=headers,
            params=params,
            timeout=10
        )
        
        logger.info(f"Recommendations test status: {response.status_code}")
        logger.info(f"Response: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Recommendations test error: {str(e)}")
        return False
    
def get_available_genres(access_token):
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://api.spotify.com/v1/recommendations/available-genre-seeds',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            genres = response.json().get('genres', [])
            logger.info(f"Available genres: {genres}")
            return genres
        else:
            logger.error(f"Failed to get genres: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Genre retrieval error: {str(e)}")
        return []

def get_fallback_tracks():
    """Return a list of popular tracks as fallback"""
    # Hardcoded list of popular tracks with minimal information
    return [
        {
            "id": "4cluDES4hQEUhmXj6TXkSo",
            "name": "Lose Yourself",
            "artists": [{"name": "Eminem"}],
            "album": {"name": "8 Mile"},
            "uri": "spotify:track:4cluDES4hQEUhmXj6TXkSo"  # Added URI field
        },
        {
            "id": "7GhIk7Il098yCjg4BQjzvb",
            "name": "Never Gonna Give You Up",
            "artists": [{"name": "Rick Astley"}],
            "album": {"name": "Whenever You Need Somebody"},
            "uri": "spotify:track:7GhIk7Il098yCjg4BQjzvb"  # Added URI field
        },
        {
            "id": "4cOdK2wGLETKBW3PvgPWqT",
            "name": "Billie Jean",
            "artists": [{"name": "Michael Jackson"}],
            "album": {"name": "Thriller"},
            "uri": "spotify:track:4cOdK2wGLETKBW3PvgPWqT"  # Added URI field
        },
        {
            "id": "1jDJFeK9x3OZboIAHsY9k2",
            "name": "Imagine",
            "artists": [{"name": "John Lennon"}],
            "album": {"name": "Imagine"},
            "uri": "spotify:track:1jDJFeK9x3OZboIAHsY9k2"  # Added URI field
        },
        {
            "id": "3SdTKo2uVsxFblQjpScoHy",
            "name": "Bohemian Rhapsody",
            "artists": [{"name": "Queen"}],
            "album": {"name": "A Night at the Opera"},
            "uri": "spotify:track:3SdTKo2uVsxFblQjpScoHy"  # Added URI field
        }
    ]

def generate_playlist_recommendations(access_token, emotion='neutral', goal='maintain', top_genres=None, recently_played=None):
    """
    Generate playlist recommendations based on mood and goal with robust error handling.
    """
    try:
        logger.info(f"Generating recommendations for emotion: {emotion}, goal: {goal}")
        
        # Don't immediately return fallback tracks if token validation fails
        # Instead, log it but continue trying with the token anyway
        if not validate_spotify_token(access_token):
            logger.warning("Token validation check failed - attempting recommendations anyway")
        
        # Define mood mappings with more nuanced parameters for each emotion
        mood_params = {
            'happy': {
                'target_valence': 0.8,
                'target_energy': 0.7,
                'target_danceability': 0.7,
                'min_valence': 0.6  # Ensure tracks are actually happy
            },
            'sad': {
                'target_valence': 0.2,
                'target_energy': 0.3,
                'target_danceability': 0.4,
                'max_valence': 0.4  # Ensure tracks are actually sad
            },
            'energetic': {
                'target_energy': 0.9,
                'target_tempo': 130,
                'target_danceability': 0.7,
                'min_energy': 0.7  # Ensure tracks are actually energetic
            },
            'calm': {
                'target_energy': 0.3,
                'target_valence': 0.5,
                'target_acousticness': 0.7,
                'max_energy': 0.5  # Ensure tracks are actually calm
            },
            'neutral': {
                'target_valence': 0.5,
                'target_energy': 0.5,
                'target_danceability': 0.5
            },
            'angry': {
                'target_energy': 0.8,
                'target_valence': 0.3,
                'min_tempo': 120
            },
            'surprised': {
                'target_energy': 0.7,
                'target_valence': 0.6,
                'target_acousticness': 0.3
            },
            'fearful': {
                'target_energy': 0.3,
                'target_valence': 0.2,
                'target_acousticness': 0.6
            },
            'disgusted': {
                'target_energy': 0.6,
                'target_valence': 0.3,
                'target_acousticness': 0.4
            },
            'contempt': {
                'target_energy': 0.5,
                'target_valence': 0.3,
                'target_acousticness': 0.5
            }
        }
        
        # Define goal adjustments with more meaningful changes
        goal_adjustments = {
            'elevate': {
                'target_valence': 0.3,  # Add 0.3 to the base valence
                'target_energy': 0.3,   # Add 0.3 to the base energy
                'min_energy': 0.6       # Ensure minimum energy level
            },
            'maintain': {},  # No change needed
            'reduce': {
                'target_valence': -0.2,  # Subtract 0.2 from the base valence
                'target_energy': -0.2,   # Subtract 0.2 from the base energy
                'max_energy': 0.5        # Ensure maximum energy level
            },
            'calm': {
                'target_valence': 0.1,   # Add 0.1 to the base valence
                'target_energy': -0.3,   # Subtract 0.3 from the base energy
                'max_energy': 0.4,       # Ensure maximum energy level
                'target_acousticness': 0.6  # Prefer acoustic tracks
            },
            'energize': {
                'target_energy': 0.3,    # Add 0.3 to the base energy
                'min_energy': 0.7,       # Ensure minimum energy level
                'target_tempo': 20       # Add 20 to the base tempo
            }
        }
        
        # Get parameters for the emotion and goal
        base_params = {}
        
        # Get base params for the emotion
        emotion_params = mood_params.get(emotion, mood_params['neutral'])
        base_params.update(emotion_params)
        
        # Apply goal adjustments
        goal_params = goal_adjustments.get(goal, {})
        for key, value in goal_params.items():
            if key in base_params and isinstance(value, (int, float)):
                # If it's a numerical adjustment (positive or negative), add it to the existing value
                if value > 0 or value < 0:
                    base_params[key] = min(1.0, max(0.0, base_params.get(key, 0.5) + value))
                else:
                    base_params[key] = value
            else:
                # For new parameters or non-numerical adjustments, just set the value
                base_params[key] = value
        
        # Set limit
        base_params['limit'] = 30  # Request more tracks for better variety
        
        # IMPORTANT: Multi-strategy approach to seed the recommendations
        all_tracks = []
        success = False
        
        # Strategy 1: Use user's top genres
        if top_genres and len(top_genres) > 0:
            try:
                # Get available genres first
                available_genres = get_available_genres(access_token)
                valid_genres = [g for g in top_genres if g in available_genres]
                
                if valid_genres:
                    # Try with combinations of top genres
                    for i in range(min(3, len(valid_genres))):
                        genre_seed = valid_genres[i:i+2]  # Take 1-2 genres at a time
                        params = base_params.copy()
                        params['seed_genres'] = ','.join(genre_seed)
                        
                        logger.info(f"Trying with user's preferred genres: {params['seed_genres']}")
                        tracks = get_recommendations(access_token, params)
                        if tracks:
                            logger.info(f"Got {len(tracks)} tracks using genres {params['seed_genres']}")
                            all_tracks.extend(tracks)
                            if len(all_tracks) >= 15:  # Once we have enough tracks, stop
                                success = True
                                break
            except Exception as e:
                logger.warning(f"Genre-based recommendations failed: {str(e)}")
        
        # Strategy 2: Use recently played tracks as seeds
        if recently_played and (not success or len(all_tracks) < 15):
            try:
                # Get up to 5 track IDs from recently played
                track_ids = []
                for track in recently_played[:10]:  # Look at up to 10 recently played tracks
                    if 'id' in track and track['id'] not in track_ids:
                        track_ids.append(track['id'])
                        if len(track_ids) >= 5:  # Spotify allows max 5 seed tracks
                            break
                
                if track_ids:
                    # Try different combinations of seed tracks
                    for i in range(0, len(track_ids), 2):  # Try 2 tracks at a time
                        seed_tracks = track_ids[i:i+2]
                        params = base_params.copy()
                        params['seed_tracks'] = ','.join(seed_tracks)
                        
                        logger.info(f"Trying with recently played tracks: {params['seed_tracks']}")
                        tracks = get_recommendations(access_token, params)
                        if tracks:
                            logger.info(f"Got {len(tracks)} tracks using seed tracks")
                            all_tracks.extend(tracks)
                            if len(all_tracks) >= 25:  # Once we have plenty of tracks, stop
                                success = True
                                break
            except Exception as e:
                logger.warning(f"Track-based recommendations failed: {str(e)}")
        
        # Strategy 3: Use genre + audio features
        if not success or len(all_tracks) < 20:
            try:
                # Use popular genres with specific audio features
                genres = ['pop', 'rock', 'alternative', 'electronic', 'indie']
                
                for genre in genres[:3]:  # Try the first 3 genres
                    params = base_params.copy()
                    params['seed_genres'] = genre
                    
                    logger.info(f"Trying recommendations with genre {genre} and audio features")
                    tracks = get_recommendations(access_token, params)
                    if tracks:
                        logger.info(f"Got {len(tracks)} tracks using genre {genre}")
                        all_tracks.extend(tracks)
                        if len(all_tracks) >= 15:
                            success = True
                            break
            except Exception as e:
                logger.warning(f"Genre+audio feature recommendations failed: {str(e)}")
        
        # De-duplicate tracks by ID
        unique_tracks = {}
        for track in all_tracks:
            if track.get('id') and track.get('id') not in unique_tracks:
                unique_tracks[track['id']] = track
        
        final_tracks = list(unique_tracks.values())
        
        # If we got any tracks, return them; otherwise fall back to defaults
        if final_tracks:
            logger.info(f"Returning {len(final_tracks)} personalized tracks")
            # Sort tracks to match emotion better - happier tracks first for happy emotion, etc.
            if emotion == 'happy':
                final_tracks.sort(key=lambda x: (-(x.get('valence', 0)), -(x.get('energy', 0))))
            elif emotion == 'sad':
                final_tracks.sort(key=lambda x: (x.get('valence', 1), x.get('energy', 1)))
            elif emotion == 'energetic':
                final_tracks.sort(key=lambda x: (-(x.get('energy', 0)), -(x.get('tempo', 0))))
            elif emotion == 'calm':
                final_tracks.sort(key=lambda x: (x.get('energy', 1), -(x.get('acousticness', 0))))
            
            return final_tracks[:20]  # Return up to 20 tracks
        
        # Only use fallback as absolute last resort
        logger.warning("Couldn't retrieve any personalized tracks, using fallback")
        return get_fallback_tracks()

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {str(e)}")
        # Return fallback tracks as last resort
        return get_fallback_tracks()

def get_recommendations(access_token, params):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Process parameters for Spotify API
    api_params = {}
    
    # Copy parameters that can be directly passed to API
    for key, value in params.items():
        # Handle specific types of parameters
        if key.startswith('min_') or key.startswith('max_') or key.startswith('target_'):
            api_params[key] = value
        elif key in ['seed_genres', 'seed_tracks', 'seed_artists', 'limit']:
            if isinstance(value, list):
                api_params[key] = ','.join(value)
            else:
                api_params[key] = value
    
    # Ensure we have valid seed parameters
    has_seed = any(key in api_params for key in ['seed_genres', 'seed_tracks', 'seed_artists'])
    if not has_seed:
        logger.warning("No seed parameters found, using 'pop' as fallback seed")
        api_params['seed_genres'] = 'pop'
    
    # Ensure limit is reasonable
    if 'limit' not in api_params:
        api_params['limit'] = 20
    
    logger.info(f"Requesting recommendations with params: {api_params}")
    
    try:
        response = requests.get(
            'https://api.spotify.com/v1/recommendations',
            headers=headers,
            params=api_params,
            timeout=15  # Increased timeout for more reliability
        )
        
        # Log response status for debugging
        logger.info(f"Spotify recommendations response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Spotify API error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
        
        data = response.json()
        tracks = data.get('tracks', [])
        
        # Log how many tracks we got
        logger.info(f"Received {len(tracks)} tracks from Spotify")
        
        return tracks
    except Exception as e:
        logger.error(f"Exception in get_recommendations: {str(e)}")
        return None
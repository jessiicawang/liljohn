import os
import base64
import requests
import json
import time
from urllib.parse import urlencode
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Spotify API constants
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-top-read",
    "user-read-recently-played",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-library-read"
]

class SpotifyClient:
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        """Initialize Spotify client with credentials"""
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("SPOTIFY_REDIRECT_URI")
        
        if not (self.client_id and self.client_secret):
            raise ValueError("Spotify client credentials missing. Check your .env file.")
            
        self.access_token = None
        self.token_expiry = 0
        self.refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")
        
        # Check for cached token
        if os.getenv("SPOTIFY_ACCESS_TOKEN") and os.getenv("SPOTIFY_TOKEN_EXPIRY"):
            self.access_token = os.getenv("SPOTIFY_ACCESS_TOKEN")
            self.token_expiry = int(os.getenv("SPOTIFY_TOKEN_EXPIRY"))

    def _get_auth_header(self):
        """Generate Authorization header for client credentials"""
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode("utf-8")
        return {"Authorization": f"Basic {auth_header}"}

    def generate_authorization_url(self):
        """Generate URL for user authorization"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(SPOTIFY_SCOPES)
        }
        return f"https://accounts.spotify.com/authorize?{urlencode(params)}"

    def get_tokens_from_code(self, code):
        """Exchange authorization code for tokens"""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(SPOTIFY_AUTH_URL, data=payload)
        if response.status_code != 200:
            logger.error(f"Error getting tokens: {response.text}")
            response.raise_for_status()
        
        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens.get("refresh_token", self.refresh_token)
        self.token_expiry = int(time.time()) + tokens["expires_in"]
        
        # Store tokens in environment for future use
        os.environ["SPOTIFY_ACCESS_TOKEN"] = self.access_token
        os.environ["SPOTIFY_REFRESH_TOKEN"] = self.refresh_token
        os.environ["SPOTIFY_TOKEN_EXPIRY"] = str(self.token_expiry)
        
        return tokens

    def refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            raise ValueError("No refresh token available")
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(SPOTIFY_AUTH_URL, data=payload)
        if response.status_code != 200:
            logger.error(f"Error refreshing token: {response.text}")
            response.raise_for_status()
        
        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.token_expiry = int(time.time()) + tokens["expires_in"]
        
        # If a new refresh token is provided, update it
        if "refresh_token" in tokens:
            self.refresh_token = tokens["refresh_token"]
            os.environ["SPOTIFY_REFRESH_TOKEN"] = self.refresh_token
        
        # Update stored tokens
        os.environ["SPOTIFY_ACCESS_TOKEN"] = self.access_token
        os.environ["SPOTIFY_TOKEN_EXPIRY"] = str(self.token_expiry)
        
        return tokens

    def get_client_credentials_token(self):
        """Get an access token using client credentials flow (no user)"""
        headers = self._get_auth_header()
        payload = {
            "grant_type": "client_credentials"
        }
        
        response = requests.post(SPOTIFY_AUTH_URL, headers=headers, data=payload)
        if response.status_code != 200:
            logger.error(f"Error getting client credentials token: {response.text}")
            response.raise_for_status()
        
        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.token_expiry = int(time.time()) + tokens["expires_in"]
        
        return tokens

    def ensure_token_valid(self):
        """Ensure we have a valid access token"""
        if not self.access_token or time.time() >= self.token_expiry - 60:
            # Token is missing or about to expire
            if self.refresh_token:
                logger.info("Refreshing access token...")
                self.refresh_access_token()
            else:
                logger.info("Getting client credentials token...")
                self.get_client_credentials_token()

    def make_api_request(self, method, endpoint, params=None, data=None):
        """Make an authenticated request to the Spotify API"""
        self.ensure_token_valid()
        
        url = f"{SPOTIFY_API_BASE_URL}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, params=params, json=data)
        elif method.upper() == "PUT":
            headers["Content-Type"] = "application/json"
            response = requests.put(url, headers=headers, params=params, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code >= 400:
            logger.error(f"API request error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        if response.status_code == 204:  # No content
            return None
            
        return response.json()

    def get_user_profile(self):
        """Get current user's profile"""
        return self.make_api_request("GET", "me")

    def get_user_top_tracks(self, time_range="medium_term", limit=50):
        """Get user's top tracks
        
        Args:
            time_range: short_term (4 weeks), medium_term (6 months), long_term (years)
            limit: Number of tracks to return (max 50)
        """
        params = {
            "time_range": time_range,
            "limit": min(limit, 50)
        }
        return self.make_api_request("GET", "me/top/tracks", params=params)

    def get_user_top_artists(self, time_range="medium_term", limit=50):
        """Get user's top artists
        
        Args:
            time_range: short_term (4 weeks), medium_term (6 months), long_term (years)
            limit: Number of artists to return (max 50)
        """
        params = {
            "time_range": time_range,
            "limit": min(limit, 50)
        }
        return self.make_api_request("GET", "me/top/artists", params=params)

    def get_recently_played_tracks(self, limit=50):
        """Get user's recently played tracks
        
        Args:
            limit: Number of tracks to return (max 50)
        """
        params = {
            "limit": min(limit, 50)
        }
        return self.make_api_request("GET", "me/player/recently-played", params=params)

    def search_tracks(self, query, limit=50):
        """Search for tracks
        
        Args:
            query: Search query
            limit: Number of results to return (max 50)
        """
        params = {
            "q": query,
            "type": "track",
            "limit": min(limit, 50)
        }
        return self.make_api_request("GET", "search", params=params)

    def get_audio_features(self, track_ids):
        """Get audio features for multiple tracks
        
        Args:
            track_ids: List of track IDs or comma-separated string
        """
        if isinstance(track_ids, list):
            track_ids = ",".join(track_ids)
            
        return self.make_api_request("GET", f"audio-features?ids={track_ids}")

    def get_tracks(self, track_ids):
        """Get full track objects for multiple tracks
        
        Args:
            track_ids: List of track IDs or comma-separated string
        """
        if isinstance(track_ids, list):
            track_ids = ",".join(track_ids)
            
        return self.make_api_request("GET", f"tracks?ids={track_ids}")

    def get_recommendations(self, seed_artists=None, seed_genres=None, seed_tracks=None, 
                           limit=50, **audio_features):
        """Get track recommendations
        
        Args:
            seed_artists: List of artist IDs (max 5 total seeds)
            seed_genres: List of genre names (max 5 total seeds)
            seed_tracks: List of track IDs (max 5 total seeds)
            limit: Number of tracks to return (max 100)
            **audio_features: Audio feature targets and ranges
                (e.g., min_energy, target_valence, max_instrumentalness)
        """
        params = {"limit": min(limit, 100)}
        
        # Add seed artists
        if seed_artists:
            if isinstance(seed_artists, list):
                seed_artists = ",".join(seed_artists[:5])
            params["seed_artists"] = seed_artists
            
        # Add seed genres
        if seed_genres:
            if isinstance(seed_genres, list):
                seed_genres = ",".join(seed_genres[:5])
            params["seed_genres"] = seed_genres
            
        # Add seed tracks
        if seed_tracks:
            if isinstance(seed_tracks, list):
                seed_tracks = ",".join(seed_tracks[:5])
            params["seed_tracks"] = seed_tracks
            
        # Validate we have at least one seed type
        if not any([seed_artists, seed_genres, seed_tracks]):
            raise ValueError("At least one seed type (artists, genres, tracks) is required")
            
        # Add audio feature parameters
        for key, value in audio_features.items():
            params[key] = value
            
        return self.make_api_request("GET", "recommendations", params=params)

    def create_playlist(self, user_id, name, description=None, public=False):
        """Create a new playlist
        
        Args:
            user_id: User ID
            name: Playlist name
            description: Playlist description
            public: Whether the playlist should be public
        """
        data = {
            "name": name,
            "public": public
        }
        
        if description:
            data["description"] = description
            
        return self.make_api_request("POST", f"users/{user_id}/playlists", data=data)

    def add_tracks_to_playlist(self, playlist_id, track_uris):
        """Add tracks to a playlist
        
        Args:
            playlist_id: Playlist ID
            track_uris: List of track URIs (max 100)
        """
        if isinstance(track_uris, list):
            track_uris = track_uris[:100]  # Limit to 100
        
        data = {
            "uris": track_uris
        }
            
        return self.make_api_request("POST", f"playlists/{playlist_id}/tracks", data=data)

    def get_available_genres(self):
        """Get a list of available genre seeds for recommendations"""
        return self.make_api_request("GET", "recommendations/available-genre-seeds")


# Helper functions for the main application

def get_spotify_client():
    """Get an initialized Spotify client"""
    # Create a client with the credentials from environment variables
    client = SpotifyClient()
    
    # Ensure we have a valid token
    client.ensure_token_valid()
    
    return client

def get_user_top_genres(spotify_client, time_range="medium_term", limit=20):
    """Get user's top genres based on their top artists
    
    Args:
        spotify_client: Initialized SpotifyClient
        time_range: Time period to consider
        limit: Number of artists to analyze
        
    Returns:
        List of genres sorted by frequency
    """
    try:
        # Get top artists
        top_artists_response = spotify_client.get_user_top_artists(time_range=time_range, limit=limit)
        
        # If we got no artists, fall back to general popular genres
        if not top_artists_response or "items" not in top_artists_response or not top_artists_response["items"]:
            logger.warning("No top artists found, using popular genres")
            return ["pop", "rock", "hip hop", "electronic", "indie"]
        
        # Extract genres from each artist and count frequency
        genres = {}
        for artist in top_artists_response["items"]:
            for genre in artist["genres"]:
                genres[genre] = genres.get(genre, 0) + 1
        
        # Sort genres by frequency
        sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
        
        # Return list of genre names
        return [genre for genre, count in sorted_genres]
        
    except Exception as e:
        logger.error(f"Error getting top genres: {str(e)}")
        # Fall back to popular genres
        return ["pop", "rock", "hip hop", "electronic", "indie"]

def get_recently_played(spotify_client, limit=20):
    """Get user's recently played tracks
    
    Args:
        spotify_client: Initialized SpotifyClient
        limit: Number of tracks to return
        
    Returns:
        List of track objects with id and uri
    """
    try:
        # Get recently played tracks
        recent_tracks_response = spotify_client.get_recently_played_tracks(limit=limit)
        
        if not recent_tracks_response or "items" not in recent_tracks_response:
            return []
        
        # Extract track IDs and URIs
        tracks = []
        for item in recent_tracks_response["items"]:
            track = item["track"]
            tracks.append({
                "id": track["id"],
                "uri": track["uri"],
                "name": track["name"],
                "artists": [artist["name"] for artist in track["artists"]]
            })
        
        return tracks
        
    except Exception as e:
        logger.error(f"Error getting recently played tracks: {str(e)}")
        return []

def create_mood_playlist(spotify_client, mood, tracks, user_id=None):
    """Create a new playlist based on mood and add tracks
    
    Args:
        spotify_client: Initialized SpotifyClient
        mood: Mood name for playlist title
        tracks: List of track URIs to add
        user_id: User ID (if None, will get from profile)
        
    Returns:
        Created playlist object
    """
    try:
        # Get user ID if not provided
        if not user_id:
            user_profile = spotify_client.get_user_profile()
            user_id = user_profile["id"]
        
        # Format current time
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        
        # Create playlist
        playlist_name = f"Mood: {mood.capitalize()} - {timestamp}"
        playlist_description = f"Generated based on your {mood} mood on {timestamp}"
        
        playlist = spotify_client.create_playlist(
            user_id=user_id,
            name=playlist_name,
            description=playlist_description,
            public=False
        )
        
        # Add tracks to playlist
        if tracks and playlist and "id" in playlist:
            track_uris = [track["uri"] for track in tracks if "uri" in track]
            if track_uris:
                spotify_client.add_tracks_to_playlist(playlist["id"], track_uris)
        
        return playlist
        
    except Exception as e:
        logger.error(f"Error creating mood playlist: {str(e)}")
        return None

def get_audio_features_for_tracks(spotify_client, track_ids):
    """Get audio features for a list of tracks
    
    Args:
        spotify_client: Initialized SpotifyClient
        track_ids: List of track IDs
        
    Returns:
        Dictionary mapping track IDs to their audio features
    """
    # Process in batches of 100 (Spotify API limit)
    features_by_id = {}
    
    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i+100]
        response = spotify_client.get_audio_features(batch)
        
        if response and "audio_features" in response:
            for feature in response["audio_features"]:
                if feature and "id" in feature:
                    features_by_id[feature["id"]] = feature
    
    return features_by_id

def filter_tracks_by_mood(tracks, mood_params, audio_features=None):
    """Filter tracks based on mood parameters
    
    Args:
        tracks: List of track objects
        mood_params: Dictionary of mood parameters (energy, valence, etc.)
        audio_features: Pre-fetched audio features (optional)
        
    Returns:
        Filtered list of tracks
    """
    if not tracks:
        return []
    
    # If no audio features provided, we need IDs to fetch them
    if not audio_features:
        track_ids = [track["id"] for track in tracks if "id" in track]
        audio_features = get_audio_features_for_tracks(get_spotify_client(), track_ids)
    
    # Define tolerance for each parameter
    tolerances = {
        "energy": 0.2,
        "valence": 0.2,
        "instrumentalness": 0.3,
        "danceability": 0.2,
        "acousticness": 0.3,
        "tempo": 20  # BPM
    }
    
    filtered_tracks = []
    
    for track in tracks:
        if "id" not in track or track["id"] not in audio_features:
            continue
            
        features = audio_features[track["id"]]
        match = True
        
        # Check each mood parameter
        for param, target in mood_params.items():
            if param in features:
                # For tempo, we use a different approach
                if param == "tempo":
                    if abs(features[param] - target) > tolerances[param]:
                        match = False
                        break
                # For other numeric parameters
                elif abs(features[param] - target) > tolerances.get(param, 0.2):
                    match = False
                    break
        
        if match:
            filtered_tracks.append(track)
    
    return filtered_tracks
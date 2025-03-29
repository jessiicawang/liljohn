import os
import base64
import requests
import json
from urllib.parse import urlencode

def get_spotify_tokens(client_id, client_secret, auth_code, redirect_uri):
    """
    Exchange authorization code for access and refresh tokens.
    
    Args:
        client_id: Spotify client ID
        client_secret: Spotify client secret
        auth_code: Authorization code from the callback
        redirect_uri: Application redirect URI
    
    Returns:
        Dictionary containing access_token, refresh_token, and expires_in
    """
    # Encode client ID and secret for authorization header
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    # Set up the API request
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri
    }
    
    # Make the API request
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        headers=headers,
        data=data
    )
    
    # Parse the response
    return response.json()

def refresh_spotify_token(client_id, client_secret, refresh_token):
    """
    Refresh an access token using a refresh token.
    
    Args:
        client_id: Spotify client ID
        client_secret: Spotify client secret
        refresh_token: Refresh token from a previous authentication
    
    Returns:
        Dictionary containing new access_token and expires_in
    """
    # Encode client ID and secret for authorization header
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    # Set up the API request
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    
    # Make the API request
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        headers=headers,
        data=data
    )
    
    # Parse the response
    return response.json()

def get_user_profile(access_token):
    """
    Get the current user's Spotify profile.
    
    Args:
        access_token: Spotify access token
    
    Returns:
        Dictionary containing user profile information
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(
        'https://api.spotify.com/v1/me',
        headers=headers
    )
    
    return response.json()

def get_user_top_genres(access_token, limit=10, time_range='medium_term'):
    """
    Get the user's top genres based on their top artists.
    
    Args:
        access_token: Spotify access token
        limit: Number of top artists to fetch (max 50)
        time_range: Time range to consider (short_term, medium_term, long_term)
    
    Returns:
        List of genre strings
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    params = {
        'limit': limit,
        'time_range': time_range
    }
    
    response = requests.get(
        'https://api.spotify.com/v1/me/top/artists',
        headers=headers,
        params=params
    )
    
    data = response.json()
    
    # Extract all genres from top artists
    all_genres = []
    for artist in data.get('items', []):
        all_genres.extend(artist.get('genres', []))
    
    # Count genre occurrences
    genre_counts = {}
    for genre in all_genres:
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    # Sort genres by occurrence count
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Return just the genre names
    return [genre for genre, count in sorted_genres]

def get_recently_played(access_token, limit=20):
    """
    Get the user's recently played tracks.
    
    Args:
        access_token: Spotify access token
        limit: Number of tracks to fetch (max 50)
    
    Returns:
        List of track objects
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    params = {
        'limit': limit
    }
    
    response = requests.get(
        'https://api.spotify.com/v1/me/player/recently-played',
        headers=headers,
        params=params
    )
    
    data = response.json()
    
    # Extract just the track objects
    tracks = [item['track'] for item in data.get('items', [])]
    
    return tracks

def create_spotify_playlist(access_token, user_id, name, description, public=False):
    """
    Create a new Spotify playlist.
    
    Args:
        access_token: Spotify access token
        user_id: Spotify user ID
        name: Playlist name
        description: Playlist description
        public: Whether the playlist should be public
    
    Returns:
        Playlist object from the API response
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'name': name,
        'description': description,
        'public': public
    }
    
    response = requests.post(
        f'https://api.spotify.com/v1/users/{user_id}/playlists',
        headers=headers,
        data=json.dumps(data)
    )
    
    return response.json()

def add_tracks_to_playlist(access_token, playlist_id, track_uris):
    """
    Add tracks to a Spotify playlist.
    
    Args:
        access_token: Spotify access token
        playlist_id: Spotify playlist ID
        track_uris: List of Spotify track URIs
    
    Returns:
        API response
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Spotify API has a limit of 100 tracks per request
    # Split into batches if needed
    batch_size = 100
    batches = [track_uris[i:i + batch_size] for i in range(0, len(track_uris), batch_size)]
    
    responses = []
    for batch in batches:
        data = {
            'uris': batch
        }
        
        response = requests.post(
            f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
            headers=headers,
            data=json.dumps(data)
        )
        
        responses.append(response.json())
    
    return responses

def get_recommendations(access_token, seed_genres=None, seed_tracks=None, seed_artists=None, 
                         limit=30, target_energy=None, target_valence=None, 
                         target_danceability=None, target_instrumentalness=None):
    """
    Get track recommendations from Spotify.
    
    Args:
        access_token: Spotify access token
        seed_genres: List of genre seeds (max 5)
        seed_tracks: List of track ID seeds (max 5)
        seed_artists: List of artist ID seeds (max 5)
        limit: Number of tracks to return (max 100)
        target_energy: Target energy level (0.0 to 1.0)
        target_valence: Target valence/positivity (0.0 to 1.0)
        target_danceability: Target danceability (0.0 to 1.0)
        target_instrumentalness: Target instrumentalness (0.0 to 1.0)
    
    Returns:
        List of recommended track objects
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    # Prepare parameters, limiting seeds to 5 total
    params = {'limit': limit}
    
    # Add seed genres if provided
    if seed_genres and len(seed_genres) > 0:
        params['seed_genres'] = ','.join(seed_genres[:5])
    
    # Add seed tracks if provided and if we have room for more seeds
    if seed_tracks and len(seed_tracks) > 0:
        max_tracks = 5 - len(params.get('seed_genres', '').split(',') if 'seed_genres' in params else 0)
        if max_tracks > 0:
            params['seed_tracks'] = ','.join(seed_tracks[:max_tracks])
    
    # Add seed artists if provided and if we have room for more seeds
    if seed_artists and len(seed_artists) > 0:
        current_seeds = len(params.get('seed_genres', '').split(',') if 'seed_genres' in params else 0)
        current_seeds += len(params.get('seed_tracks', '').split(',') if 'seed_tracks' in params else 0)
        max_artists = 5 - current_seeds
        if max_artists > 0:
            params['seed_artists'] = ','.join(seed_artists[:max_artists])
    
    # Add audio feature targets if provided
    if target_energy is not None:
        params['target_energy'] = target_energy
    
    if target_valence is not None:
        params['target_valence'] = target_valence
    
    if target_danceability is not None:
        params['target_danceability'] = target_danceability
    
    if target_instrumentalness is not None:
        params['target_instrumentalness'] = target_instrumentalness
    
    response = requests.get(
        'https://api.spotify.com/v1/recommendations',
        headers=headers,
        params=params
    )
    
    data = response.json()
    
    return data.get('tracks', [])

def get_audio_features(access_token, track_ids):
    """
    Get audio features for multiple tracks.
    
    Args:
        access_token: Spotify access token
        track_ids: List of track IDs
    
    Returns:
        List of audio features objects
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    params = {
        'ids': ','.join(track_ids)
    }
    
    response = requests.get(
        'https://api.spotify.com/v1/audio-features',
        headers=headers,
        params=params
    )
    
    data = response.json()
    
    return data.get('audio_features', [])
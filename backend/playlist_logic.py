import random
from spotify_api import get_recommendations, get_audio_features

def generate_playlist_recommendations(access_token, emotion, goal, top_genres, recently_played, num_tracks=30):
    """
    Generate a playlist based on the user's emotion, goal, and preferences.
    
    Args:
        access_token: Spotify access token
        emotion: Detected emotion (happy, sad, angry, etc.)
        goal: User's goal (energize, maintain, calm)
        top_genres: List of user's top genres
        recently_played: List of user's recently played tracks
        num_tracks: Number of tracks to include in the playlist
    
    Returns:
        List of track objects for the playlist
    """
    # Define emotional mappings to audio features
    emotion_mappings = {
        'happy': {'energy': 0.7, 'valence': 0.8, 'danceability': 0.7},
        'sad': {'energy': 0.4, 'valence': 0.3, 'danceability': 0.4},
        'angry': {'energy': 0.8, 'valence': 0.4, 'danceability': 0.6},
        'surprised': {'energy': 0.7, 'valence': 0.6, 'danceability': 0.6},
        'fearful': {'energy': 0.5, 'valence': 0.3, 'danceability': 0.4},
        'disgusted': {'energy': 0.6, 'valence': 0.3, 'danceability': 0.5},
        'contempt': {'energy': 0.6, 'valence': 0.4, 'danceability': 0.5},
        'neutral': {'energy': 0.5, 'valence': 0.5, 'danceability': 0.5}
    }
    
    # Define goal modifiers
    goal_modifiers = {
        'energize': {'energy': 0.2, 'valence': 0.1, 'danceability': 0.1},
        'maintain': {'energy': 0, 'valence': 0, 'danceability': 0},
        'calm': {'energy': -0.2, 'valence': 0, 'danceability': -0.1}
    }
    
    # Get base values for the emotion
    base_values = emotion_mappings.get(emotion, emotion_mappings['neutral'])
    
    # Apply goal modifiers
    modifiers = goal_modifiers.get(goal, goal_modifiers['maintain'])
    
    target_energy = min(max(base_values['energy'] + modifiers['energy'], 0), 1)
    target_valence = min(max(base_values['valence'] + modifiers['valence'], 0), 1)
    target_danceability = min(max(base_values['danceability'] + modifiers['danceability'], 0), 1)
    
    # Set instrumentalness based on emotion
    target_instrumentalness = None
    if emotion in ['sad', 'neutral'] and goal == 'calm':
        target_instrumentalness = 0.5  # More instrumental for calming sad/neutral moods
    
    # Extract seed tracks from recently played
    seed_tracks = []
    if recently_played:
        # Get audio features for recently played tracks
        track_ids = [track['id'] for track in recently_played[:20]]
        audio_features = get_audio_features(access_token, track_ids)
        
        # Match tracks to our target mood
        for i, features in enumerate(audio_features):
            if features:
                energy_diff = abs(features['energy'] - target_energy)
                valence_diff = abs(features['valence'] - target_valence)
                danceability_diff = abs(features['danceability'] - target_danceability)
                
                # Calculate a similarity score
                similarity = energy_diff + valence_diff + danceability_diff
                
                # Add track ID and similarity score
                seed_tracks.append((track_ids[i], similarity))
        
        # Sort by similarity and take the top 2
        seed_tracks.sort(key=lambda x: x[1])
        seed_tracks = [track[0] for track in seed_tracks[:2]]
    
    # Prepare seed genres (use top 3)
    seed_genres = top_genres[:3] if top_genres else ['pop', 'rock', 'indie']
    
    # Get recommendations
    recommendations = get_recommendations(
        access_token=access_token,
        seed_genres=seed_genres,
        seed_tracks=seed_tracks,
        limit=num_tracks,
        target_energy=target_energy,
        target_valence=target_valence,
        target_danceability=target_danceability,
        target_instrumentalness=target_instrumentalness
    )
    
    return recommendations
import logging
import random
from collections import Counter

# Configure logging
logger = logging.getLogger(__name__)

# Define mood category mappings to audio features
# These are initial defaults that will be adjusted by the app based on detected mood
MOOD_AUDIO_FEATURES = {
    "happy": {
        "energy": 0.7,
        "valence": 0.8,  # High valence = positive/happy
        "danceability": 0.7,
        "tempo": 120,
        "mode": 1,  # Major key
        "instrumentalness": 0.2
    },
    "sad": {
        "energy": 0.4,
        "valence": 0.3,  # Low valence = negative/sad
        "danceability": 0.5,
        "tempo": 90,  
        "mode": 0,  # Minor key
        "instrumentalness": 0.3
    },
    "angry": {
        "energy": 0.8,
        "valence": 0.3,
        "danceability": 0.6,
        "tempo": 140,
        "mode": 0,  # Minor key
        "instrumentalness": 0.2
    },
    "relaxed": {
        "energy": 0.3,
        "valence": 0.6,
        "danceability": 0.4,
        "tempo": 80,
        "instrumentalness": 0.5,
        "acousticness": 0.6
    },
    "energetic": {
        "energy": 0.9,
        "valence": 0.7,
        "danceability": 0.8,
        "tempo": 130,
        "instrumentalness": 0.1
    },
    "focused": {
        "energy": 0.5,
        "valence": 0.5,
        "danceability": 0.4,
        "tempo": 110,
        "instrumentalness": 0.7
    }
}

def generate_playlist_based_on_mood(spotify, mood_params, top_genres=None, recently_played=None, limit=30):
    """
    Generate a playlist based on mood parameters, user's top genres, and recently played tracks
    
    Args:
        spotify: Initialized Spotify client
        mood_params: Dictionary of mood parameters (energy, valence, etc.)
        top_genres: List of user's top genres (optional)
        recently_played: List of recently played tracks (optional)
        limit: Maximum number of tracks to include in the playlist
        
    Returns:
        Dictionary with playlist information, including tracks
    """
    logger.info(f"Generating playlist with mood parameters: {mood_params}")
    
    # Prepare seeds for recommendations
    seed_artists = []
    seed_tracks = []
    seed_genres = []
    
    # Extract seeds from recently played tracks
    if recently_played:
        # Get unique artists from recently played
        recent_artists = {}
        for track in recently_played[:10]:  # Use only first 10 tracks
            for artist in track.get("artists", []):
                if isinstance(artist, dict) and "id" in artist:
                    recent_artists[artist["id"]] = artist["name"]
                elif isinstance(artist, str):
                    # If artist is already a string name
                    pass
        
        # Add track seeds (up to 2)
        recent_track_ids = [track["id"] for track in recently_played[:5] if "id" in track]
        if recent_track_ids:
            # Randomly select up to 2 tracks
            seed_tracks = random.sample(recent_track_ids, min(2, len(recent_track_ids)))
        
        # Add artist seeds (up to 2)
        if recent_artists:
            # Randomly select up to 2 artists
            seed_artist_ids = random.sample(list(recent_artists.keys()), min(2, len(recent_artists)))
            seed_artists = seed_artist_ids
    
    # Add genre seeds
    if top_genres:
        # Get available genre seeds from Spotify
        try:
            available_genres_response = spotify.get_available_genres()
            available_genres = available_genres_response.get("genres", [])
            
            # Filter top genres to only include available ones
            valid_genres = [genre for genre in top_genres if genre in available_genres]
            
            # Add up to 5 - (len of artists + tracks) genre seeds
            remaining_seeds = 5 - len(seed_artists) - len(seed_tracks)
            if remaining_seeds > 0 and valid_genres:
                seed_genres = valid_genres[:remaining_seeds]
                
        except Exception as e:
            logger.error(f"Error getting available genres: {str(e)}")
    
    # Ensure we have at least one seed
    if not any([seed_artists, seed_genres, seed_tracks]):
        logger.warning("No seeds available, using general popular genres")
        seed_genres = ["pop", "rock"]
    
    # Prepare audio feature parameters for recommendation
    recommendation_params = {}
    
    # Convert mood parameters to Spotify recommendation parameters
    for feature, value in mood_params.items():
        # Add target parameter (e.g., target_energy, target_valence)
        recommendation_params[f"target_{feature}"] = value
        
        # Add min/max ranges to increase variety but still match the mood
        # For example, if target_energy is 0.7, set min_energy to 0.5 and max_energy to 0.9
        range_size = 0.2  # This allows for some variation but keeps within the mood
        
        if feature != "tempo":  # Handle tempo separately since it's not 0-1 scale
            recommendation_params[f"min_{feature}"] = max(0.0, value - range_size)
            recommendation_params[f"max_{feature}"] = min(1.0, value + range_size)
        else:
            # For tempo, use a wider range (±20 BPM)
            recommendation_params[f"min_{feature}"] = max(40, value - 20)
            recommendation_params[f"max_{feature}"] = min(200, value + 20)
    
    logger.info(f"Using seeds - Artists: {seed_artists}, Tracks: {seed_tracks}, Genres: {seed_genres}")
    
    # Get recommendations
    try:
        recommendations = spotify.get_recommendations(
            seed_artists=seed_artists,
            seed_tracks=seed_tracks,
            seed_genres=seed_genres,
            limit=min(limit * 2, 100),  # Request more tracks than needed for filtering
            **recommendation_params
        )
        
        recommended_tracks = recommendations.get("tracks", [])
        logger.info(f"Received {len(recommended_tracks)} recommended tracks")
        
        # Extract track details
        tracks = []
        for track in recommended_tracks:
            tracks.append({
                "id": track["id"],
                "uri": track["uri"],
                "name": track["name"],
                "artists": [artist["name"] for artist in track["artists"]],
                "album": track["album"]["name"],
                "popularity": track["popularity"],
                "preview_url": track.get("preview_url"),
                "explicit": track.get("explicit", False),
                "duration_ms": track.get("duration_ms", 0)
            })
        
        # Filter and score tracks
        scored_tracks = score_tracks_for_mood(spotify, tracks, mood_params)
        
        # Sort by score (descending) and take top tracks
        final_tracks = [track for score, track in sorted(scored_tracks, key=lambda x: x[0], reverse=True)][:limit]
        
        # Create playlist response
        playlist = {
            "name": f"Mood-based Recommendations",
            "description": f"Generated based on your mood and preferences",
            "tracks": final_tracks,
            "track_count": len(final_tracks),
            "mood_params": mood_params,
            "seeds": {
                "artists": seed_artists,
                "tracks": seed_tracks,
                "genres": seed_genres
            }
        }
        
        return playlist
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return {
            "name": "Error generating recommendations",
            "description": "There was an error generating your playlist",
            "tracks": [],
            "track_count": 0,
            "error": str(e)
        }

def score_tracks_for_mood(spotify, tracks, mood_params, audio_features=None):
    """
    Score tracks based on how well they match the mood parameters
    
    Args:
        spotify: Initialized Spotify client
        tracks: List of track objects
        mood_params: Dictionary of mood parameters (energy, valence, etc.)
        audio_features: Pre-fetched audio features (optional)
        
    Returns:
        List of (score, track) tuples sorted by score
    """
    if not tracks:
        return []
    
    # Get track IDs for audio features
    track_ids = [track["id"] for track in tracks if "id" in track]
    
    # Fetch audio features if not provided
    if not audio_features:
        try:
            # Get audio features in batches (Spotify API limit)
            features_by_id = {}
            
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i:i+100]
                
                response = spotify.get_audio_features(batch)
                if response and "audio_features" in response:
                    for feature in response["audio_features"]:
                        if feature and "id" in feature:
                            features_by_id[feature["id"]] = feature
                else:
                    audio_features_list = response  # If response is directly the list
                    for feature in audio_features_list:
                        if feature and "id" in feature:
                            features_by_id[feature["id"]] = feature
                            
            audio_features = features_by_id
                
        except Exception as e:
            logger.error(f"Error fetching audio features: {str(e)}")
            return [(0, track) for track in tracks]  # Return tracks with zero score
    
    # Weight factors for scoring
    feature_weights = {
        "energy": 1.0,
        "valence": 1.0,
        "danceability": 0.7,
        "instrumentalness": 0.5,
        "acousticness": 0.3,
        "tempo": 0.3,
        "mode": 0.2,
        "popularity": 0.5
    }
    
    # Score each track
    scored_tracks = []
    
    for track in tracks:
        if "id" not in track or track["id"] not in audio_features:
            continue
            
        features = audio_features[track["id"]]
        
        # Calculate feature-based score
        score = 0
        feature_count = 0
        
        for feature, target in mood_params.items():
            if feature in features and feature in feature_weights:
                feature_count += 1
                
                # For tempo, normalize the difference
                if feature == "tempo":
                    # Convert the difference to 0-1 scale (0 = perfect match, 1 = far off)
                    normalized_diff = min(1.0, abs(features[feature] - target) / 50)
                    # Invert so 1 = perfect match, 0 = far off
                    feature_score = 1.0 - normalized_diff
                else:
                    # Calculate how close the feature is to the target (0-1)
                    feature_score = 1.0 - min(1.0, abs(features[feature] - target))
                
                # Add weighted score
                score += feature_score * feature_weights[feature]
        
        # Add popularity bonus if available
        if "popularity" in track:
            popularity_score = track["popularity"] / 100 * feature_weights["popularity"]
            score += popularity_score
            feature_count += 1
        
        # Normalize score by number of features
        if feature_count > 0:
            score = score / (sum(feature_weights.values()) * feature_count / len(feature_weights))
        
        # Add track with its score
        scored_tracks.append((score, track))
    
    return scored_tracks

def diversify_playlist(tracks, max_tracks_per_artist=2):
    """
    Ensure playlist has variety by limiting tracks per artist
    
    Args:
        tracks: List of track objects
        max_tracks_per_artist: Maximum number of tracks allowed per artist
        
    Returns:
        Filtered list of tracks
    """
    if not tracks:
        return []
    
    # Count tracks per artist
    artist_counts = Counter()
    filtered_tracks = []
    
    for track in tracks:
        # Get primary artist
        primary_artist = track["artists"][0] if track.get("artists") else "Unknown"
        
        # Check if we've reached max for this artist
        if artist_counts[primary_artist] < max_tracks_per_artist:
            filtered_tracks.append(track)
            artist_counts[primary_artist] += 1
    
    return filtered_tracks

def add_transition_logic(tracks, mood_params, target_mood_params=None):
    """
    Reorder tracks to create a smooth transition in the playlist
    
    Args:
        tracks: List of track objects
        mood_params: Starting mood parameters
        target_mood_params: Target mood parameters (for transition playlists)
        
    Returns:
        Reordered list of tracks
    """
    if not tracks or len(tracks) <= 1:
        return tracks
    
    # If target mood is not specified, just organize by energy/valence
    if not target_mood_params:
        # Sort by combination of energy and valence
        # This creates a nicer flow than random ordering
        return sorted(tracks, key=lambda t: t.get("energy", 0.5) + t.get("valence", 0.5))
    
    # For mood transition playlists (e.g., relaxed → energetic)
    # Calculate distance of each track to starting and ending moods
    track_positions = []
    
    for track in tracks:
        # Calculate distance to starting mood
        start_distance = 0
        for feature, value in mood_params.items():
            if feature in track:
                start_distance += abs(track[feature] - value)
        
        # Calculate distance to target mood
        target_distance = 0
        for feature, value in target_mood_params.items():
            if feature in track:
                target_distance += abs(track[feature] - value)
        
        # Use ratio of distances to position in playlist (0=start, 1=end)
        if start_distance + target_distance > 0:
            position = target_distance / (start_distance + target_distance)
        else:
            position = 0.5  # Middle if we can't determine
        
        track_positions.append((position, track))
    
    # Sort by position
    sorted_tracks = [track for pos, track in sorted(track_positions, key=lambda x: x[0])]
    return sorted_tracks

def create_mood_transition_playlist(spotify, start_mood, target_mood, user_genres=None, duration_minutes=30):
    """
    Create a playlist that transitions from one mood to another
    
    Args:
        spotify: Initialized Spotify client
        start_mood: Starting mood (e.g., "relaxed")
        target_mood: Target mood (e.g., "energetic")
        user_genres: List of user's preferred genres
        duration_minutes: Approximate duration in minutes
        
    Returns:
        Playlist with tracks ordered to create a mood transition
    """
    # Get audio feature mappings for start and target moods
    if isinstance(start_mood, str) and start_mood in MOOD_AUDIO_FEATURES:
        start_params = MOOD_AUDIO_FEATURES[start_mood]
    else:
        start_params = start_mood  # Assume it's already a params dict
    
    if isinstance(target_mood, str) and target_mood in MOOD_AUDIO_FEATURES:
        target_params = MOOD_AUDIO_FEATURES[target_mood]
    else:
        target_params = target_mood  # Assume it's already a params dict
    
    # Calculate number of tracks needed (assuming ~3.5 min average track length)
    avg_track_length_min = 3.5
    num_tracks = int(duration_minutes / avg_track_length_min) + 2  # Add buffer tracks
    
    # Generate recommendations for both moods
    start_playlist = generate_playlist_based_on_mood(
        spotify=spotify,
        mood_params=start_params,
        top_genres=user_genres,
        limit=num_tracks // 2
    )
    
    target_playlist = generate_playlist_based_on_mood(
        spotify=spotify,
        mood_params=target_params,
        top_genres=user_genres,
        limit=num_tracks // 2
    )
    
    # Combine tracks
    all_tracks = start_playlist.get("tracks", []) + target_playlist.get("tracks", [])
    
    # Remove duplicates (by ID)
    unique_tracks = []
    track_ids = set()
    for track in all_tracks:
        if track["id"] not in track_ids:
            unique_tracks.append(track)
            track_ids.add(track["id"])
    
    # Order tracks to create transition
    ordered_tracks = add_transition_logic(
        tracks=unique_tracks,
        mood_params=start_params,
        target_mood_params=target_params
    )
    
    # Create result playlist
    transition_name = f"Transition: {start_mood.capitalize()} to {target_mood.capitalize()}"
    
    transition_playlist = {
        "name": transition_name,
        "description": f"A transition playlist from {start_mood} to {target_mood}",
        "tracks": ordered_tracks,
        "track_count": len(ordered_tracks),
        "start_mood": start_mood,
        "target_mood": target_mood,
        "start_params": start_params,
        "target_params": target_params
    }
    
    return transition_playlist

def adapt_playlist_to_context(tracks, context, intensity=1.0):
    """
    Adapt a playlist for a specific context
    
    Args:
        tracks: List of track objects with audio features
        context: Context string (e.g., "workout", "study", "relax")
        intensity: How strongly to apply the adaptation (0.0-1.0)
        
    Returns:
        Filtered and reordered list of tracks
    """
    if not tracks:
        return []
    
    # Context-specific adaptations
    context_adaptations = {
        "workout": {
            "min_energy": 0.6 * intensity,
            "min_tempo": 100,
            "sort_by": lambda t: (t.get("energy", 0) * 2 + t.get("tempo", 0) / 200),
            "max_instrumentalness": 0.4
        },
        "study": {
            "max_energy": 0.6,
            "max_speechiness": 0.3 * intensity,
            "min_instrumentalness": 0.3 * intensity,
            "sort_by": lambda t: t.get("valence", 0)
        },
        "relax": {
            "max_energy": 0.5 * intensity,
            "max_tempo": 100,
            "min_acousticness": 0.3 * intensity,
            "sort_by": lambda t: -t.get("energy", 0)
        },
        "focus": {
            "max_speechiness": 0.3 * intensity,
            "min_instrumentalness": 0.3 * intensity,
            "sort_by": lambda t: t.get("energy", 0)
        },
        "party": {
            "min_danceability": 0.6 * intensity,
            "min_energy": 0.6 * intensity,
            "sort_by": lambda t: t.get("danceability", 0) + t.get("popularity", 0) / 100
        },
        "sleep": {
            "max_energy": 0.4 * intensity,
            "max_tempo": 80,
            "min_instrumentalness": 0.5 * intensity,
            "max_loudness": -10,
            "sort_by": lambda t: -t.get("energy", 0)
        }
    }
    
    # Use general filtering if context not found
    adaptation = context_adaptations.get(context.lower(), {
        "sort_by": lambda t: t.get("energy", 0) + t.get("valence", 0)
    })
    
    # Filter tracks based on context
    filtered_tracks = []
    for track in tracks:
        # Skip tracks missing audio features
        if not any(k in track for k in ["energy", "tempo", "danceability"]):
            continue
            
        match = True
        
        # Check min constraints
        for feature, min_val in [(k, v) for k, v in adaptation.items() if k.startswith("min_")]:
            feature_name = feature[4:]  # Remove "min_"
            if feature_name in track and track[feature_name] < min_val:
                match = False
                break
                
        # Check max constraints
        for feature, max_val in [(k, v) for k, v in adaptation.items() if k.startswith("max_")]:
            feature_name = feature[4:]  # Remove "max_"
            if feature_name in track and track[feature_name] > max_val:
                match = False
                break
                
        if match:
            filtered_tracks.append(track)
    
    # If filtering removed too many tracks, add back some of the originals
    if len(filtered_tracks) < max(3, len(tracks) * 0.3):
        logger.warning(f"Context filtering removed too many tracks, restoring some")
        remaining = [t for t in tracks if t not in filtered_tracks]
        # Add back tracks up to at least 30% of original
        filtered_tracks.extend(remaining[:max(3, len(tracks) // 3)])
    
    # Sort by context-specific criteria
    if "sort_by" in adaptation:
        filtered_tracks.sort(key=adaptation["sort_by"], reverse=True)
    
    return filtered_tracks
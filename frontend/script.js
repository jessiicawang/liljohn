// DOM Elements
const sensorModal = document.getElementById('sensor-modal');
const startSensorsBtn = document.getElementById('start-sensors');
const heartRateStatus = document.getElementById('heart-rate-status');
const cameraStatus = document.getElementById('camera-status');
const detectedMood = document.getElementById('detected-mood');
const moodEmoji = document.getElementById('mood-emoji');
const differentMoodBtn = document.getElementById('different-mood-btn');
const contextForm = document.getElementById('context-form');
const moodDetection = document.getElementById('mood-detection');
const playlistFull = document.getElementById('playlist-full');
const moodButtons = document.querySelectorAll('.mood-btn');
const userContextForm = document.getElementById('user-context-form');
const desiredMoodInput = document.getElementById('desired-mood');
const playlistContainer = document.getElementById('playlist-container');
const trackList = document.getElementById('track-list');
const refreshPlaylistBtn = document.getElementById('refresh-playlist');
const openSpotifyBtn = document.getElementById('open-spotify');

// Global Variables
let currentMood = null;
let sensorData = {
    heartRate: null,
    facialExpression: null
};
let userContext = {
    activity: null,
    desiredMood: null
};
let currentPlaylist = null;

// Emotion mapping
const emotions = {
    happy: {
        emoji: "😊",
        spotifyParams: { min_valence: 0.7, target_energy: 0.8 },
        description: "happy"
    },
    sad: {
        emoji: "😔",
        spotifyParams: { max_valence: 0.4, target_energy: 0.4 },
        description: "sad"
    },
    angry: {
        emoji: "😠",
        spotifyParams: { target_energy: 0.9, target_tempo: 140 },
        description: "angry"
    },
    relaxed: {
        emoji: "😌",
        spotifyParams: { max_energy: 0.4, target_acousticness: 0.8 },
        description: "relaxed"
    },
    energetic: {
        emoji: "⚡",
        spotifyParams: { min_energy: 0.8, target_tempo: 130 },
        description: "energetic"
    },
    focused: {
        emoji: "🧠",
        spotifyParams: { target_instrumentalness: 0.7, max_energy: 0.6 },
        description: "focused"
    },
    stressed: {
        emoji: "😰",
        spotifyParams: { max_energy: 0.4, target_acousticness: 0.7 },
        description: "stressed"
    },
    neutral: {
        emoji: "😐",
        spotifyParams: { target_valence: 0.5, target_energy: 0.5 },
        description: "neutral"
    }
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Show sensor modal on start
    sensorModal.classList.remove('hidden');
    
    // Set up event listeners
    setupEventListeners();
});

// Set up all event listeners
function setupEventListeners() {
    // Start sensors button
    startSensorsBtn.addEventListener('click', () => {
        sensorModal.classList.add('hidden');
        initializeSensors();
    });
    
    // Different mood button
    differentMoodBtn.addEventListener('click', () => {
        moodDetection.classList.add('hidden');
        contextForm.classList.remove('hidden');
    });
    
    // Mood selection buttons
    moodButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove selected class from all buttons
            moodButtons.forEach(btn => btn.classList.remove('selected'));
            
            // Add selected class to clicked button
            button.classList.add('selected');
            
            // Update hidden input value
            desiredMoodInput.value = button.dataset.mood;
        });
    });
    
    // Context form submission
    userContextForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Get form values
        const activity = document.getElementById('activity').value;
        const desiredMood = desiredMoodInput.value;
        
        if (!activity || !desiredMood) {
            alert('Please complete all fields');
            return;
        }
        
        // Save user context
        userContext.activity = activity;
        userContext.desiredMood = desiredMood;
        
        // Generate recommendations based on context
        generateContextBasedRecommendations();
        
        // Hide form, show playlist
        contextForm.classList.add('hidden');
        playlistFull.classList.remove('hidden');
    });
    
    // Refresh playlist button
    refreshPlaylistBtn.addEventListener('click', () => {
        if (userContext.activity && userContext.desiredMood) {
            generateContextBasedRecommendations();
        } else {
            generateMoodBasedRecommendations();
        }
    });
    
    // Open Spotify button (placeholder functionality)
    openSpotifyBtn.addEventListener('click', () => {
        alert('This would open the playlist in Spotify. Integration with Spotify API required.');
    });
}

// Initialize sensors
function initializeSensors() {
    // Update sensor status
    heartRateStatus.textContent = 'Connecting...';
    cameraStatus.textContent = 'Connecting...';
    
    // Simulate heart rate sensor connection (would be replaced with actual sensor API)
    setTimeout(() => {
        heartRateStatus.textContent = 'Connected';
        simulateHeartRateSensor();
    }, 1500);
    
    // Simulate camera connection (would be replaced with actual camera API)
    setTimeout(() => {
        cameraStatus.textContent = 'Connected';
        simulateCameraCapture();
    }, 2000);
}

// Simulate heart rate sensor data
function simulateHeartRateSensor() {
    // Simulate heart rate between 60-100 BPM
    const heartRate = Math.floor(Math.random() * 40) + 60;
    sensorData.heartRate = heartRate;
    
    // Check if both sensors have data
    checkSensorData();
    
    // Continue simulation (in real app, this would be continuous monitoring)
    setTimeout(simulateHeartRateSensor, 5000);
}

// Simulate camera capture for facial expression
function simulateCameraCapture() {
    // Simulate facial expression detection
    const expressions = ['happy', 'sad', 'angry', 'relaxed', 'energetic', 'focused', 'stressed', 'neutral'];
    const expression = expressions[Math.floor(Math.random() * expressions.length)];
    
    sensorData.facialExpression = expression;
    
    // Check if both sensors have data
    checkSensorData();
    
    // In a real app, this would be triggered by the camera API
}

// Check if both sensors have data and determine mood
function checkSensorData() {
    if (sensorData.heartRate && sensorData.facialExpression) {
        determineMood();
    }
}

// Determine mood based on sensor data
function determineMood() {
    // In a real app, this would use ML to combine heart rate and facial expression
    // For this demo, we'll just use the facial expression
    const mood = sensorData.facialExpression;
    
    // Update UI with mood
    updateMoodDisplay(mood);
    
    // Generate recommendations based on mood
    generateMoodBasedRecommendations();
}

// Update mood display
function updateMoodDisplay(mood) {
    currentMood = mood;
    detectedMood.textContent = emotions[mood].description;
    moodEmoji.textContent = emotions[mood].emoji;
}

// Generate recommendations based on detected mood
function generateMoodBasedRecommendations() {
    // Show loading state
    playlistContainer.innerHTML = `
        <div class="loader"></div>
        <p class="loading-text">Creating your personalized playlist...</p>
    `;
    
    // Simulate API call delay
    setTimeout(() => {
        // This would be replaced with actual Spotify API calls
        currentPlaylist = generateMockPlaylist(currentMood);
        
        // Display preview in the mood detection card
        displayPlaylistPreview();
    }, 2000);
}

// Generate recommendations based on user context
function generateContextBasedRecommendations() {
    // Update playlist title based on context
    const playlistTitle = document.getElementById('playlist-title');
    
    switch(userContext.desiredMood) {
        case 'energized':
            playlistTitle.textContent = `Music to energize your ${userContext.activity}`;
            break;
        case 'calm':
            playlistTitle.textContent = `Music to calm your ${userContext.activity}`;
            break;
        case 'same':
            playlistTitle.textContent = `Music to match your ${userContext.activity}`;
            break;
    }
    
    // Would adjust mood parameters based on user context
    let adjustedMood = currentMood;
    
    if (userContext.desiredMood === 'energized') {
        // Adjust towards more energetic regardless of current mood
        adjustedMood = 'energetic';
    } else if (userContext.desiredMood === 'calm') {
        // Adjust towards more relaxed regardless of current mood
        adjustedMood = 'relaxed';
    }
    
    // Generate playlist with adjusted parameters
    currentPlaylist = generateMockPlaylist(adjustedMood);
    
    // Display the full playlist
    displayFullPlaylist();
}

// Display playlist preview in the mood detection card
function displayPlaylistPreview() {
    // Show just the first 3 tracks in preview
    const previewTracks = currentPlaylist.slice(0, 3);
    
    let previewHTML = `
        <h3>Suggested Playlist</h3>
        <ul class="preview-tracks">
    `;
    
    previewTracks.forEach(track => {
        previewHTML += `
            <li class="track-item">
                <img src="${track.image}" alt="${track.title}" class="track-image">
                <div class="track-info">
                    <div class="track-title">${track.title}</div>
                    <div class="track-artist">${track.artist}</div>
                </div>
            </li>
        `;
    });
    
    previewHTML += `</ul>`;
    
    playlistContainer.innerHTML = previewHTML;
}

// Display full playlist
function displayFullPlaylist() {
    let playlistHTML = '';
    
    currentPlaylist.forEach(track => {
        playlistHTML += `
            <li class="track-item">
                <img src="${track.image}" alt="${track.title}" class="track-image">
                <div class="track-info">
                    <div class="track-title">${track.title}</div>
                    <div class="track-artist">${track.artist}</div>
                </div>
                <div class="track-controls">
                    <button class="icon-btn">
                        <i class="fas fa-play"></i>
                    </button>
                </div>
            </li>
        `;
    });
    
    trackList.innerHTML = playlistHTML;
}

// Generate mock playlist based on mood
function generateMockPlaylist(mood) {
    // This would be replaced with actual Spotify API integration
    const mockPlaylists = {
        happy: [
            { title: "Happy", artist: "Pharrell Williams", image: "/api/placeholder/50/50" },
            { title: "Good as Hell", artist: "Lizzo", image: "/api/placeholder/50/50" },
            { title: "Walking on Sunshine", artist: "Katrina & The Waves", image: "/api/placeholder/50/50" },
            { title: "Can't Stop the Feeling!", artist: "Justin Timberlake", image: "/api/placeholder/50/50" },
            { title: "Uptown Funk", artist: "Mark Ronson ft. Bruno Mars", image: "/api/placeholder/50/50" }
        ],
        sad: [
            { title: "Someone Like You", artist: "Adele", image: "/api/placeholder/50/50" },
            { title: "Fix You", artist: "Coldplay", image: "/api/placeholder/50/50" },
            { title: "When the Party's Over", artist: "Billie Eilish", image: "/api/placeholder/50/50" },
            { title: "Skinny Love", artist: "Bon Iver", image: "/api/placeholder/50/50" },
            { title: "All I Want", artist: "Kodaline", image: "/api/placeholder/50/50" }
        ],
        angry: [
            { title: "Break Stuff", artist: "Limp Bizkit", image: "/api/placeholder/50/50" },
            { title: "Bulls on Parade", artist: "Rage Against the Machine", image: "/api/placeholder/50/50" },
            { title: "Master of Puppets", artist: "Metallica", image: "/api/placeholder/50/50" },
            { title: "Killing in the Name", artist: "Rage Against the Machine", image: "/api/placeholder/50/50" },
            { title: "Gives You Hell", artist: "The All-American Rejects", image: "/api/placeholder/50/50" }
        ],
        relaxed: [
            { title: "Weightless", artist: "Marconi Union", image: "/api/placeholder/50/50" },
            { title: "Strawberry Swing", artist: "Coldplay", image: "/api/placeholder/50/50" },
            { title: "Gymnopédie No.1", artist: "Erik Satie", image: "/api/placeholder/50/50" },
            { title: "Holocene", artist: "Bon Iver", image: "/api/placeholder/50/50" },
            { title: "Pure Shores", artist: "All Saints", image: "/api/placeholder/50/50" }
        ],
        energetic: [
            { title: "Can't Hold Us", artist: "Macklemore & Ryan Lewis", image: "/api/placeholder/50/50" },
            { title: "Don't Stop Me Now", artist: "Queen", image: "/api/placeholder/50/50" },
            { title: "Levels", artist: "Avicii", image: "/api/placeholder/50/50" },
            { title: "Titanium", artist: "David Guetta ft. Sia", image: "/api/placeholder/50/50" },
            { title: "Shake It Off", artist: "Taylor Swift", image: "/api/placeholder/50/50" }
        ],
        focused: [
            { title: "Experience", artist: "Ludovico Einaudi", image: "/api/placeholder/50/50" },
            { title: "Night Mist", artist: "Brian Eno", image: "/api/placeholder/50/50" },
            { title: "Metamorphosis One", artist: "Philip Glass", image: "/api/placeholder/50/50" },
            { title: "Divenire", artist: "Ludovico Einaudi", image: "/api/placeholder/50/50" },
            { title: "Tuesday", artist: "Busted", image: "/api/placeholder/50/50" }
        ],
        stressed: [
            { title: "Breathe Me", artist: "Sia", image: "/api/placeholder/50/50" },
            { title: "Orinoco Flow", artist: "Enya", image: "/api/placeholder/50/50" },
            { title: "Warm Foothills", artist: "Alt-J", image: "/api/placeholder/50/50" },
            { title: "The Scientist", artist: "Coldplay", image: "/api/placeholder/50/50" },
            { title: "Ocean", artist: "John Butler", image: "/api/placeholder/50/50" }
        ],
        neutral: [
            { title: "Clocks", artist: "Coldplay", image: "/api/placeholder/50/50" },
            { title: "Crystalised", artist: "The xx", image: "/api/placeholder/50/50" },
            { title: "Teardrop", artist: "Massive Attack", image: "/api/placeholder/50/50" },
            { title: "Starlight", artist: "Muse", image: "/api/placeholder/50/50" },
            { title: "Digital Love", artist: "Daft Punk", image: "/api/placeholder/50/50" }
        ]
    };
    
    return mockPlaylists[mood];
}
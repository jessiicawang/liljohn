document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const startBtn = document.getElementById('start-btn');
    const spotifyLoginBtn = document.getElementById('spotify-login-btn');
    const captureBtn = document.getElementById('capture-btn');
    const skipCameraBtn = document.getElementById('skip-camera-btn');
    const approvePermissionsBtn = document.getElementById('approve-permissions');
    const openInSpotifyBtn = document.getElementById('open-in-spotify');
    const startOverBtn = document.getElementById('start-over');
    const goalButtons = document.querySelectorAll('.goal-btn');
    const authModal = document.getElementById('auth-modal');
    const closeModal = document.querySelector('.close-modal');
    
    // Video elements
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const cameraStatus = document.getElementById('camera-status');
    
    // App state
    const state = {
        detectedEmotion: null,
        selectedGoal: null,
        accessToken: null,
        refreshToken: null,
        playlistId: null,
        cameraReady: false,
        userSkippedCamera: false
    };
    
    // Navigation between screens
    function showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
    }
    
    // Initialize the camera
    async function initCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'user',
                    width: { ideal: 640 },
                    height: { ideal: 480 } 
                } 
            });
            
            video.srcObject = stream;
            state.cameraReady = true;
            captureBtn.disabled = false;
            cameraStatus.textContent = 'Click "Capture" to detect your mood.';
        } catch (err) {
            console.error('Error accessing camera:', err);
            cameraStatus.textContent = 'Could not access camera. Please ensure permissions are granted.';
            skipCameraBtn.textContent = 'Continue without camera';
        }
    }
    
    // Capture image from camera
    function captureImage() {
        return new Promise((resolve) => {
            const context = canvas.getContext('2d');
            // Set canvas dimensions to match video
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            // Draw the current video frame onto the canvas
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            // Convert canvas to data URL (base64 encoded image)
            const imageData = canvas.toDataURL('image/jpeg');
            resolve(imageData);
        });
    }
    
    // Send image to backend for emotion detection
    async function detectEmotion(imageData) {
        try {
            const response = await fetch('/detect-emotion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ image: imageData })
            });
            
            if (!response.ok) {
                throw new Error('Failed to detect emotion');
            }
            
            const data = await response.json();
            return data.emotion;
        } catch (error) {
            console.error('Error detecting emotion:', error);
            return 'neutral'; // Default fallback emotion
        }
    }
    
    // Update the UI based on detected emotion
    function updateMoodUI(emotion) {
        const detectedMoodElement = document.getElementById('detected-mood');
        const moodEmojiElement = document.getElementById('mood-emoji');
        
        detectedMoodElement.textContent = emotion;
        
        // Map emotions to emojis
        const emojiMap = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😠',
            'surprised': '😮',
            'fearful': '😨',
            'disgusted': '🤢',
            'contempt': '😒',
            'neutral': '😐'
        };
        
        moodEmojiElement.textContent = emojiMap[emotion] || '😐';
    }

    // Add this to your frontend main JavaScript file
    window.addEventListener('load', function() {
        // Clear any stored tokens from localStorage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('token_expiry');
        
        // Remove any other auth-related items you might be storing
        sessionStorage.clear();
    });
    
    // Authenticate with Spotify
    function authenticateWithSpotify() {
        // Instead of creating your own auth flow here, use the backend endpoint
        window.location.href = '/login';
    }
    
    // Check if we're returning from Spotify auth
    function checkForSpotifyCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const accessToken = urlParams.get('access_token');
        const refreshToken = urlParams.get('refresh_token');
    
        if (accessToken && refreshToken) {
            // Store the tokens
            state.accessToken = accessToken;
            state.refreshToken = refreshToken;
            
            // Remove tokens from URL without refreshing the page
            window.history.replaceState({}, document.title, window.location.pathname);
            
            // Continue to creating playlist
            showScreen('loading-screen');
            createPlaylist();
            return true;
        }
        
        return false;
    }
    
    // Create a playlist based on mood and goal
    async function createPlaylist() {
        try {
            console.log("Creating playlist with:", {
                emotion: state.detectedEmotion || 'neutral',
                goal: state.selectedGoal || 'maintain',
                access_token: state.accessToken ? "Token exists (not showing for security)" : "No token!"
            });
            
            const response = await fetch('/create-playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    emotion: state.detectedEmotion || 'neutral',
                    goal: state.selectedGoal || 'maintain',
                    access_token: state.accessToken
                })
            });
            
            // Get the text response for debugging
            const responseText = await response.text();
            
            // Try to parse it as JSON
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (e) {
                console.error("Failed to parse response as JSON:", responseText);
                throw new Error('Server returned invalid JSON');
            }
            
            if (!response.ok) {
                console.error('Server error:', data);
                throw new Error(data.error || 'Failed to create playlist');
            }
            
            state.playlistId = data.playlist_id;
            
            // Display the playlist
            displayPlaylist(data);
            showScreen('result-screen');
        } catch (error) {
            console.error('Error creating playlist:', error);
            alert('Failed to create playlist. Please try again. Error: ' + error.message);
            showScreen('mood-detected-screen');
        }
    }
    
    // Display the created playlist
    function displayPlaylist(playlistData) {
        const playlistName = document.getElementById('playlist-name');
        const playlistDescription = document.getElementById('playlist-description');
        const playlistCover = document.getElementById('playlist-cover');
        const trackList = document.getElementById('track-list');
        
        playlistName.textContent = playlistData.name || 'Mood Playlist';
        playlistDescription.textContent = playlistData.description || '';
        
        // Safely check if images exist and handle if they don't
        if (playlistData.images && playlistData.images.length > 0) {
            playlistCover.src = playlistData.images[0].url;
            playlistCover.onerror = function() {
                // If image loading fails, use a placeholder
                this.src = '/img/placeholder.png';
                console.log('Failed to load playlist cover, using placeholder');
            };
        } else {
            playlistCover.src = '/img/placeholder.png';
        }
        
        // Clear previous tracks
        trackList.innerHTML = '';
        
        // Handle case where tracks might not be available
        if (!playlistData.tracks || playlistData.tracks.length === 0) {
            const noTracksMessage = document.createElement('div');
            noTracksMessage.className = 'no-tracks-message';
            noTracksMessage.textContent = 'No tracks found in this playlist.';
            trackList.appendChild(noTracksMessage);
            return;
        }
        
        // Add tracks to the list
        playlistData.tracks.forEach((track, index) => {
            const trackItem = document.createElement('div');
            trackItem.className = 'track-item';
            
            // Make sure album images exist
            let albumImageUrl = '/img/placeholder.png';
            if (track.album && track.album.images && track.album.images.length > 0) {
                albumImageUrl = track.album.images[track.album.images.length-1].url; // Use smallest image
            }
            
            trackItem.innerHTML = `
                <div class="track-number">${index + 1}</div>
                <div class="track-image">
                    <img src="${albumImageUrl}" alt="${track.album ? track.album.name : 'Album'}" 
                         onerror="this.src='/img/placeholder.png'">
                </div>
                <div class="track-info">
                    <div class="track-name">${track.name || 'Unknown Track'}</div>
                    <div class="track-artist">${track.artists ? track.artists.map(artist => artist.name).join(', ') : 'Unknown Artist'}</div>
                </div>
            `;
            
            trackList.appendChild(trackItem);
        });
        
        // Update the "Open in Spotify" button
        if (playlistData.external_url) {
            openInSpotifyBtn.onclick = () => {
                window.open(playlistData.external_url, '_blank');
            };
            openInSpotifyBtn.style.display = 'block';
        } else {
            openInSpotifyBtn.style.display = 'none';
        }
    }
    
    // Event Listeners
    startBtn.addEventListener('click', () => {
        authModal.classList.add('show');
    });
    
    approvePermissionsBtn.addEventListener('click', () => {
        authModal.classList.remove('show');
        showScreen('camera-screen');
        initCamera();
    });
    
    closeModal.addEventListener('click', () => {
        authModal.classList.remove('show');
    });
    
    captureBtn.addEventListener('click', async () => {
        if (state.cameraReady) {
            // Show loading state
            captureBtn.disabled = true;
            cameraStatus.textContent = 'Analyzing your expression...';
            
            // Capture and analyze the image
            const imageData = await captureImage();
            const emotion = await detectEmotion(imageData);
            
            // Stop the camera stream
            const stream = video.srcObject;
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            // Update app state and UI
            state.detectedEmotion = emotion;
            updateMoodUI(emotion);
            showScreen('mood-detected-screen');
        }
    });
    
    skipCameraBtn.addEventListener('click', () => {
        // Stop the camera if it's running
        const stream = video.srcObject;
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        
        state.userSkippedCamera = true;
        state.detectedEmotion = 'neutral';
        updateMoodUI('neutral');
        showScreen('mood-detected-screen');
    });
    
    goalButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove selection from all buttons
            goalButtons.forEach(btn => btn.classList.remove('selected'));
            
            // Add selection to clicked button
            button.classList.add('selected');
            
            // Update state
            state.selectedGoal = button.dataset.goal;
            
            // Continue to Spotify login
            showScreen('login-screen');
        });
    });
    
    spotifyLoginBtn.addEventListener('click', authenticateWithSpotify);
    
    startOverBtn.addEventListener('click', () => {
        // Reset state
        state.detectedEmotion = null;
        state.selectedGoal = null;
        state.playlistId = null;
        state.cameraReady = false;
        state.userSkippedCamera = false;
        
        // Remove selection from goal buttons
        goalButtons.forEach(btn => btn.classList.remove('selected'));
        
        // Go back to start
        showScreen('welcome-screen');
    });
    
    // Check if returning from Spotify auth
    if (checkForSpotifyCallback()) {
        showScreen('loading-screen');
    }
});
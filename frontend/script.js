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
    
    // Authenticate with Spotify
    function authenticateWithSpotify() {
        // Instead of creating your own auth flow here, use the backend endpoint
        window.location.href = '/login';
    }
    
    // Generate a random string for state parameter
    /* function generateRandomString(length) {
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let text = '';
        
        for (let i = 0; i < length; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        
        return text;
    } */
    
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
    
    // Exchange authorization code for access and refresh tokens
    /* async function exchangeCodeForTokens(code) {
        try {
            const response = await fetch('/exchange-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code })
            });
            
            if (!response.ok) {
                throw new Error('Failed to exchange code for tokens');
            }
            
            const data = await response.json();
            state.accessToken = data.access_token;
            state.refreshToken = data.refresh_token;
            
            // Remove code and state from URL without refreshing the page
            window.history.replaceState({}, document.title, window.location.pathname);
            
            // Continue to creating playlist
            showScreen('loading-screen');
            createPlaylist();
        } catch (error) {
            console.error('Error exchanging code for tokens:', error);
            alert('Failed to authenticate with Spotify. Please try again.');
            showScreen('login-screen');
        }
    } */
    
    // Create a playlist based on mood and goal
    async function createPlaylist() {
        try {
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
            
            if (!response.ok) {
                throw new Error('Failed to create playlist');
            }
            
            const data = await response.json();
            state.playlistId = data.playlist_id;
            
            // Display the playlist
            displayPlaylist(data);
            showScreen('result-screen');
        } catch (error) {
            console.error('Error creating playlist:', error);
            alert('Failed to create playlist. Please try again.');
            showScreen('mood-detected-screen');
        }
    }
    
    // Display the created playlist
    function displayPlaylist(playlistData) {
        const playlistName = document.getElementById('playlist-name');
        const playlistDescription = document.getElementById('playlist-description');
        const playlistCover = document.getElementById('playlist-cover');
        const trackList = document.getElementById('track-list');
        
        playlistName.textContent = playlistData.name;
        playlistDescription.textContent = playlistData.description;
        
        if (playlistData.images && playlistData.images.length > 0) {
            playlistCover.src = playlistData.images[0].url;
        }
        
        // Clear previous tracks
        trackList.innerHTML = '';
        
        // Add tracks to the list
        playlistData.tracks.forEach((track, index) => {
            const trackItem = document.createElement('div');
            trackItem.className = 'track-item';
            
            trackItem.innerHTML = `
                <div class="track-number">${index + 1}</div>
                <div class="track-image">
                    <img src="${track.album.images[2].url}" alt="${track.album.name}">
                </div>
                <div class="track-info">
                    <div class="track-name">${track.name}</div>
                    <div class="track-artist">${track.artists.map(artist => artist.name).join(', ')}</div>
                </div>
            `;
            
            trackList.appendChild(trackItem);
        });
        
        // Update the "Open in Spotify" button
        openInSpotifyBtn.onclick = () => {
            window.open(playlistData.external_url, '_blank');
        };
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
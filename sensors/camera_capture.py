import os
import cv2
import time
import threading
import logging
import numpy as np
from datetime import datetime
from PIL import Image
import io

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../data/logs/camera_capture.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('camera_capture')

class CameraCapture:
    def __init__(self, camera_id=0, resolution=(640, 480), fps=30, use_mock=False):
        """
        Initialize the camera capture system
        
        Args:
            camera_id (int): Camera device ID (typically 0 for built-in webcam)
            resolution (tuple): Desired resolution as (width, height)
            fps (int): Desired frames per second
            use_mock (bool): If True, use mock images instead of camera
        """
        self.camera_id = camera_id
        self.resolution = resolution
        self.fps = fps
        self.use_mock = use_mock
        
        # Camera state
        self.camera = None
        self.is_capturing = False
        self.capture_thread = None
        self.last_frame = None
        self.last_capture_time = None
        
        # Face detection
        self.face_cascade = None
        self.enable_face_detection = True
        
        # Storage directory for captures
        self.storage_dir = os.path.join("..", "data", "captures")
        os.makedirs(self.storage_dir, exist_ok=True)
        
        logger.info(f"Camera Capture initialized (Camera ID: {camera_id}, Mock: {use_mock})")
        
        # Initialize face detection if needed
        if self.enable_face_detection:
            self._init_face_detection()
    
    def _init_face_detection(self):
        """Initialize OpenCV face detector"""
        try:
            # Load OpenCV's pre-trained face detector
            cascades_dir = cv2.data.haarcascades
            cascade_file = os.path.join(cascades_dir, 'haarcascade_frontalface_default.xml')
            
            if os.path.exists(cascade_file):
                self.face_cascade = cv2.CascadeClassifier(cascade_file)
                logger.info("Face detection initialized successfully")
            else:
                # Try alternative approach if cascade file not found
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                logger.info("Face detection initialized with alternative path")
        except Exception as e:
            logger.error(f"Error initializing face detection: {str(e)}")
            self.face_cascade = None
    
    def start(self):
        """
        Start the camera capture session
        
        Returns:
            bool: Success status
        """
        if self.is_capturing:
            logger.warning("Camera is already running")
            return True
            
        if self.use_mock:
            logger.info("Starting in mock mode (no camera required)")
            self.is_capturing = True
            return True
            
        try:
            # Initialize camera
            self.camera = cv2.VideoCapture(self.camera_id)
            
            # Set resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            # Set FPS
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Check if camera opened successfully
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                return False
                
            # Start capture thread
            self.is_capturing = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            logger.info(f"Camera started successfully (Resolution: {self.resolution}, FPS: {self.fps})")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera: {str(e)}")
            return False
    
    def stop(self):
        """Stop the camera capture session"""
        self.is_capturing = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
            
        if self.camera and not self.use_mock:
            self.camera.release()
            self.camera = None
            
        logger.info("Camera stopped")
    
    def capture_image(self, ensure_face=True, max_retries=3):
        """
        Capture a still image from the camera
        
        Args:
            ensure_face (bool): If True, will attempt to capture until a face is detected
            max_retries (int): Maximum number of capture attempts when ensure_face is True
            
        Returns:
            tuple: (image_bytes, metadata) or (None, error_dict) if failed
        """
        if self.use_mock:
            return self._generate_mock_image()
            
        if not self.is_capturing:
            started = self.start()
            if not started:
                return None, {"error": "Failed to start camera"}
                
        # Use most recent frame if available
        if self.last_frame is not None:
            image = self.last_frame.copy()
        else:
            # Or capture a new frame
            success, image = self.camera.read()
            if not success:
                return None, {"error": "Failed to capture image"}
        
        # Check for face if requested
        if ensure_face and self.face_cascade is not None:
            face_found = False
            retries = 0
            
            while not face_found and retries < max_retries:
                # Convert to grayscale for face detection
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = self.face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=1.1, 
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                if len(faces) > 0:
                    face_found = True
                    logger.info(f"Face detected in image (size: {faces[0][2]}x{faces[0][3]})")
                else:
                    retries += 1
                    logger.warning(f"No face detected, retrying ({retries}/{max_retries})")
                    time.sleep(0.5)  # Short delay before retry
                    success, image = self.camera.read()
                    if not success:
                        return None, {"error": "Failed to capture image during retry"}
            
            if not face_found:
                logger.warning("Failed to detect a face after maximum retries")
                # Continue anyway, but include warning in metadata
        
        # Convert image to bytes
        timestamp = datetime.now()
        image_bytes = self._convert_to_bytes(image)
        
        # Create metadata
        metadata = {
            "timestamp": timestamp.isoformat(),
            "resolution": image.shape[1::-1],  # Width x Height
            "format": "jpeg"
        }
        
        logger.info(f"Image captured successfully ({len(image_bytes)} bytes)")
        return image_bytes, metadata
    
    def start_emotion_capture_session(self, interval_seconds=3.0, duration_seconds=15, callback=None):
        """
        Start a session to capture multiple images for emotion analysis
        
        Args:
            interval_seconds (float): Time between captures
            duration_seconds (int): Total duration of session
            callback (function): Callback for each capture (receives image_bytes, metadata)
            
        Returns:
            list: List of (image_bytes, metadata) tuples
        """
        captures = []
        end_time = time.time() + duration_seconds
        
        logger.info(f"Starting emotion capture session ({duration_seconds}s, interval: {interval_seconds}s)")
        
        try:
            # Start camera if not already running
            if not self.is_capturing:
                started = self.start()
                if not started:
                    logger.error("Failed to start camera for capture session")
                    return []
            
            # Capture loop
            while time.time() < end_time:
                image_bytes, metadata = self.capture_image(ensure_face=True)
                
                if image_bytes:
                    captures.append((image_bytes, metadata))
                    
                    # Call callback if provided
                    if callback and callable(callback):
                        callback(image_bytes, metadata)
                
                # Wait for next interval
                time.sleep(interval_seconds)
        
        except Exception as e:
            logger.error(f"Error in emotion capture session: {str(e)}")
        
        finally:
            logger.info(f"Emotion capture session completed ({len(captures)} images)")
            return captures
    
    def save_image(self, image_bytes, filename=None):
        """
        Save captured image to disk
        
        Args:
            image_bytes (bytes): Image data
            filename (str): Optional filename, if None generates timestamp-based name
            
        Returns:
            str: Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
        
        file_path = os.path.join(self.storage_dir, filename)
        
        try:
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            logger.info(f"Image saved to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            return None
    
    def _capture_loop(self):
        """Internal method for continuous frame capture"""
        while self.is_capturing:
            try:
                # Read frame from camera
                ret, frame = self.camera.read()
                
                if ret:
                    self.last_frame = frame
                    self.last_capture_time = datetime.now()
                else:
                    logger.warning("Failed to capture frame")
                    time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Error in capture loop: {str(e)}")
                time.sleep(0.5)  # Delay after error
    
    def _convert_to_bytes(self, image, format='jpeg', quality=95):
        """Convert OpenCV image to bytes"""
        try:
            # Convert from BGR to RGB (OpenCV uses BGR)
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image)
            
            # Save to bytes
            img_bytes = io.BytesIO()
            pil_image.save(img_bytes, format=format, quality=quality)
            return img_bytes.getvalue()
            
        except Exception as e:
            logger.error(f"Error converting image to bytes: {str(e)}")
            return None
    
    def _generate_mock_image(self):
        """Generate a mock image for testing without camera hardware"""
        try:
            # Create a blank colored image with a "face-like" shape
            image = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Background color - light blue
            image[:, :] = [230, 200, 150]  # BGR format
            
            # Draw a simple face
            # Face oval
            cv2.ellipse(image, (320, 240), (120, 150), 0, 0, 360, (200, 160, 130), -1)
            
            # Eyes
            cv2.circle(image, (280, 200), 20, (255, 255, 255), -1)  # Left eye white
            cv2.circle(image, (360, 200), 20, (255, 255, 255), -1)  # Right eye white
            cv2.circle(image, (280, 200), 8, (80, 80, 80), -1)      # Left pupil
            cv2.circle(image, (360, 200), 8, (80, 80, 80), -1)      # Right pupil
            
            # Generate different expressions randomly
            expression = int(time.time()) % 3  # 0, 1, or 2
            
            if expression == 0:
                # Happy face - smile
                cv2.ellipse(image, (320, 280), (60, 30), 0, 0, 180, (80, 80, 80), 2)
            elif expression == 1:
                # Sad face - frown
                cv2.ellipse(image, (320, 310), (60, 30), 0, 180, 360, (80, 80, 80), 2)
            else:
                # Neutral face - straight line
                cv2.line(image, (260, 280), (380, 280), (80, 80, 80), 2)
            
            # Convert to bytes
            image_bytes = self._convert_to_bytes(image)
            
            # Create metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "resolution": (640, 480),
                "format": "jpeg",
                "mock": True,
                "expression": ["happy", "sad", "neutral"][expression]
            }
            
            return image_bytes, metadata
            
        except Exception as e:
            logger.error(f"Error generating mock image: {str(e)}")
            return None, {"error": str(e)}

# Usage example
if __name__ == "__main__":
    # Example usage
    camera = CameraCapture(use_mock=True)  # Set to False to use actual camera
    
    try:
        camera.start()
        print("Camera started")
        
        # Capture single image
        print("Capturing single image...")
        image_bytes, metadata = camera.capture_image()
        
        if image_bytes:
            # Save the image
            file_path = camera.save_image(image_bytes)
            print(f"Image saved to: {file_path}")
            print(f"Metadata: {metadata}")
        
        # Capture session example
        print("\nStarting capture session (3 seconds)...")
        
        def image_callback(img_bytes, meta):
            print(f"Captured image: {len(img_bytes)} bytes at {meta['timestamp']}")
        
        captures = camera.start_emotion_capture_session(
            interval_seconds=1.0, 
            duration_seconds=3,
            callback=image_callback
        )
        
        print(f"Capture session complete: {len(captures)} images")
        
    finally:
        # Clean up
        camera.stop()
        print("Camera stopped")
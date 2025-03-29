import cv2
import base64
import numpy as np
import os
import time

class CameraCapture:
    """Class to handle webcam access and image capture."""
    
    def __init__(self):
        self.camera = None
    
    def initialize_camera(self, camera_index=0):
        """
        Initialize the webcam.
        
        Args:
            camera_index: Index of the camera to use (default is 0)
        
        Returns:
            Boolean indicating if initialization was successful
        """
        try:
            self.camera = cv2.VideoCapture(camera_index)
            
            # Check if camera opened successfully
            if not self.camera.isOpened():
                print("Failed to open camera")
                return False
                
            return True
        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            return False
    
    def capture_image(self):
        """
        Capture an image from the webcam.
        
        Returns:
            Base64 encoded image string or None if capture failed
        """
        if not self.camera or not self.camera.isOpened():
            print("Camera not initialized")
            return None
        
        try:
            # Capture frame-by-frame
            ret, frame = self.camera.read()
            
            if not ret:
                print("Failed to capture image")
                return None
            
            # Convert to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            
            if not ret:
                print("Failed to encode image")
                return None
            
            # Convert to base64
            base64_image = base64.b64encode(buffer).decode('utf-8')
            
            return base64_image
        except Exception as e:
            print(f"Error capturing image: {str(e)}")
            return None
    
    def release_camera(self):
        """Release the camera."""
        if self.camera and self.camera.isOpened():
            self.camera.release()
            print("Camera released")

# Example usage (for testing)
if __name__ == "__main__":
    camera = CameraCapture()
    
    if camera.initialize_camera():
        print("Camera initialized. Capturing image in 3 seconds...")
        time.sleep(3)
        
        image_data = camera.capture_image()
        
        if image_data:
            # Save the captured image to a file for testing
            image_bytes = base64.b64decode(image_data)
            with open("test_capture.jpg", "wb") as f:
                f.write(image_bytes)
            print("Test image saved to test_capture.jpg")
        
        camera.release_camera()
    else:
        print("Failed to initialize camera")
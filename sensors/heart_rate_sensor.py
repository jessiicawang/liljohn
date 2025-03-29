import os
import time
import threading
import logging
import random
import json
import serial
import numpy as np
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../data/logs/heart_rate_sensor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('heart_rate_sensor')

class HeartRateSensor:
    def __init__(self, use_mock=False, port=None, baudrate=9600):
        """
        Initialize the heart rate sensor interface
        
        Args:
            use_mock (bool): If True, generate mock data instead of using real sensor
            port (str): Serial port for the sensor (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate (int): Baud rate for serial communication
        """
        self.use_mock = use_mock
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self.is_reading = False
        self.reading_thread = None
        self.callback = None
        
        # Data storage
        self.current_bpm = 0
        self.hr_history = []
        self.last_reading_time = None
        
        # Constants for analysis
        self.RESTING_HR_BASELINE = 70  # Default resting heart rate
        self.user_baselines = {}
        
        logger.info(f"Heart Rate Sensor initialized (Mock Mode: {use_mock})")
        
        # Try to load user baselines from file
        self._load_user_baselines()
    
    def connect(self):
        """Connect to the heart rate sensor or initialize mock mode"""
        if self.use_mock:
            logger.info("Using mock heart rate data")
            self.is_connected = True
            return True
            
        try:
            logger.info(f"Connecting to heart rate sensor on port {self.port}")
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Allow time for connection to establish
            self.is_connected = True
            logger.info("Successfully connected to heart rate sensor")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to heart rate sensor: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the sensor and clean up resources"""
        self.stop_reading()
        
        if self.serial_conn and not self.use_mock:
            try:
                self.serial_conn.close()
                logger.info("Disconnected from heart rate sensor")
            except Exception as e:
                logger.error(f"Error disconnecting from sensor: {str(e)}")
        
        self.is_connected = False
    
    def start_reading(self, callback=None):
        """
        Start continuous reading from the heart rate sensor
        
        Args:
            callback (function): Optional callback function to receive heart rate updates
        """
        if not self.is_connected:
            success = self.connect()
            if not success:
                logger.error("Cannot start reading: not connected to sensor")
                return False
        
        if self.is_reading:
            logger.warning("Already reading from sensor")
            return True
            
        self.callback = callback
        self.is_reading = True
        self.reading_thread = threading.Thread(target=self._reading_loop)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        
        logger.info("Started heart rate reading")
        return True
    
    def stop_reading(self):
        """Stop the continuous reading process"""
        self.is_reading = False
        if self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=2.0)
            logger.info("Stopped heart rate reading")
    
    def get_current_heart_rate(self):
        """
        Get the most recent heart rate measurement
        
        Returns:
            dict: Heart rate data including BPM and timestamp
        """
        if self.last_reading_time is None:
            # If no reading available, take one reading now
            if not self.is_reading:
                self._take_single_reading()
        
        return {
            'bpm': self.current_bpm,
            'timestamp': self.last_reading_time.isoformat() if self.last_reading_time else None,
            'status': 'valid' if self.current_bpm > 0 else 'invalid'
        }
    
    def get_heart_rate_stats(self, minutes=5):
        """
        Get heart rate statistics over the specified time period
        
        Args:
            minutes (int): Number of minutes of history to analyze
            
        Returns:
            dict: Heart rate statistics
        """
        if not self.hr_history:
            return {
                'average': 0,
                'min': 0,
                'max': 0,
                'variability': 0,
                'samples': 0,
                'duration_seconds': 0
            }
        
        # Filter history for the requested time period
        if minutes > 0:
            cutoff_time = datetime.now().timestamp() - (minutes * 60)
            recent_history = [hr for hr, ts in self.hr_history if ts > cutoff_time]
        else:
            recent_history = [hr for hr, _ in self.hr_history]
        
        if not recent_history:
            return {
                'average': 0,
                'min': 0,
                'max': 0,
                'variability': 0,
                'samples': 0,
                'duration_seconds': 0
            }
        
        # Calculate statistics
        avg_hr = sum(recent_history) / len(recent_history)
        min_hr = min(recent_history)
        max_hr = max(recent_history)
        variability = np.std(recent_history) if len(recent_history) > 1 else 0
        
        # Calculate duration
        if len(self.hr_history) > 1:
            oldest_timestamp = min(ts for _, ts in self.hr_history)
            newest_timestamp = max(ts for _, ts in self.hr_history)
            duration = newest_timestamp - oldest_timestamp
        else:
            duration = 0
        
        return {
            'average': round(avg_hr, 1),
            'min': min_hr,
            'max': max_hr,
            'variability': round(variability, 2),
            'samples': len(recent_history),
            'duration_seconds': round(duration)
        }
    
    def calibrate_resting_hr(self, user_id='default', duration_seconds=60):
        """
        Calibrate the resting heart rate baseline for a user
        
        Args:
            user_id (str): Identifier for the user
            duration_seconds (int): Duration of calibration in seconds
            
        Returns:
            dict: Calibration results
        """
        logger.info(f"Starting resting HR calibration for user {user_id} ({duration_seconds}s)")
        
        # Clear previous history for clean calibration
        self.hr_history = []
        
        # Ensure we're reading
        was_already_reading = self.is_reading
        if not was_already_reading:
            self.start_reading()
        
        # Wait for calibration period
        time.sleep(duration_seconds)
        
        # Calculate baseline from gathered data
        stats = self.get_heart_rate_stats(minutes=0)  # Use all gathered data
        
        if stats['samples'] > 0:
            # Store the new baseline
            baseline = round(stats['average'])
            self.user_baselines[user_id] = {
                'resting_hr': baseline,
                'calibrated_at': datetime.now().isoformat(),
                'samples': stats['samples']
            }
            self._save_user_baselines()
            
            logger.info(f"Calibrated resting HR for user {user_id}: {baseline} BPM")
            
            # Stop reading if we started it for calibration
            if not was_already_reading:
                self.stop_reading()
                
            return {
                'user_id': user_id,
                'resting_hr': baseline,
                'samples': stats['samples'],
                'success': True
            }
        else:
            logger.error("Calibration failed: No valid heart rate readings")
            
            # Stop reading if we started it for calibration
            if not was_already_reading:
                self.stop_reading()
                
            return {
                'user_id': user_id,
                'success': False,
                'error': 'No valid readings'
            }
    
    def get_user_baseline(self, user_id='default'):
        """
        Get the stored baseline for a specific user
        
        Args:
            user_id (str): Identifier for the user
            
        Returns:
            dict: User's baseline information or None if not calibrated
        """
        return self.user_baselines.get(user_id, None)
    
    def get_heart_rate_zone(self, bpm, user_id='default'):
        """
        Determine the heart rate zone based on user's baseline
        
        Args:
            bpm (int): Current heart rate in BPM
            user_id (str): Identifier for the user
            
        Returns:
            str: Heart rate zone ('rest', 'low', 'moderate', 'high', 'max')
        """
        # Get user baseline or use default
        user_baseline = self.get_user_baseline(user_id)
        rest_hr = user_baseline['resting_hr'] if user_baseline else self.RESTING_HR_BASELINE
        
        # Calculate max HR using common formula
        max_hr = 220 - 30  # Assuming 30 years old; should be personalized
        heart_rate_reserve = max_hr - rest_hr
        
        # Define zones based on heart rate reserve (Karvonen method)
        if bpm < rest_hr + 0.3 * heart_rate_reserve:
            return 'low'
        elif bpm < rest_hr + 0.5 * heart_rate_reserve:
            return 'moderate'
        elif bpm < rest_hr + 0.7 * heart_rate_reserve:
            return 'high'
        else:
            return 'max'
    
    def _reading_loop(self):
        """Internal method for continuous reading from the sensor"""
        while self.is_reading:
            try:
                self._take_single_reading()
                
                # Call callback if provided
                if self.callback and callable(self.callback) and self.current_bpm > 0:
                    self.callback(self.current_bpm)
                
                # Short sleep to avoid overwhelming the CPU
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in heart rate reading loop: {str(e)}")
                time.sleep(2.0)  # Longer sleep after error
    
    def _take_single_reading(self):
        """Take a single reading from the sensor"""
        if self.use_mock:
            # Generate realistic mock data
            self.current_bpm = self._generate_mock_heart_rate()
            self.last_reading_time = datetime.now()
            
            # Store in history
            self.hr_history.append((self.current_bpm, self.last_reading_time.timestamp()))
            
            # Limit history size
            if len(self.hr_history) > 300:  # Keep ~5 minutes at 1Hz
                self.hr_history.pop(0)
                
            return self.current_bpm
            
        elif self.serial_conn:
            try:
                # Read line from serial port
                line = self.serial_conn.readline().decode('utf-8').strip()
                
                # Parse heart rate data - format depends on your specific sensor
                # Common format example: "BPM:75" or just "75"
                if line:
                    if line.startswith("BPM:"):
                        bpm_str = line[4:]
                    else:
                        bpm_str = line
                        
                    try:
                        bpm = int(bpm_str)
                        
                        # Validate reading (typical human range)
                        if 30 <= bpm <= 220:
                            self.current_bpm = bpm
                            self.last_reading_time = datetime.now()
                            
                            # Store in history
                            self.hr_history.append((bpm, self.last_reading_time.timestamp()))
                            
                            # Limit history size
                            if len(self.hr_history) > 300:
                                self.hr_history.pop(0)
                            
                            return bpm
                    except ValueError:
                        logger.warning(f"Invalid heart rate value: '{bpm_str}'")
            
            except Exception as e:
                logger.error(f"Error reading from sensor: {str(e)}")
        
        return 0  # Return 0 for invalid reading
    
    def _generate_mock_heart_rate(self):
        """Generate realistic mock heart rate data for testing"""
        if not self.hr_history:
            # First reading - start with resting heart rate
            return self.RESTING_HR_BASELINE
        
        # Get previous reading
        last_hr = self.hr_history[-1][0]
        
        # Random walk with constraints to simulate realistic heart rate
        change = random.uniform(-2, 2)  # Small random changes
        
        # Occasionally add bigger changes to simulate activity changes
        if random.random() < 0.05:  # 5% chance of bigger change
            change += random.uniform(-10, 10)
        
        # Calculate new heart rate
        new_hr = last_hr + change
        
        # Ensure it stays in realistic bounds
        new_hr = max(40, min(180, new_hr))
        
        return round(new_hr)
    
    def _load_user_baselines(self):
        """Load user baselines from file"""
        try:
            file_path = os.path.join("..", "data", "user_hr_baselines.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.user_baselines = json.load(f)
                logger.info(f"Loaded baselines for {len(self.user_baselines)} users")
        except Exception as e:
            logger.error(f"Error loading user baselines: {str(e)}")
            self.user_baselines = {}
    
    def _save_user_baselines(self):
        """Save user baselines to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.join("..", "data"), exist_ok=True)
            
            file_path = os.path.join("..", "data", "user_hr_baselines.json")
            with open(file_path, 'w') as f:
                json.dump(self.user_baselines, f, indent=2)
            logger.info(f"Saved baselines for {len(self.user_baselines)} users")
        except Exception as e:
            logger.error(f"Error saving user baselines: {str(e)}")

# Usage example
if __name__ == "__main__":
    # Example of how this could be used
    sensor = HeartRateSensor(use_mock=True)  # Use mock data for testing
    
    # Define callback for real-time updates
    def hr_callback(bpm):
        print(f"Current heart rate: {bpm} BPM")
    
    # Start reading with callback
    sensor.start_reading(callback=hr_callback)
    
    try:
        # Run for 30 seconds
        print("Reading heart rate for 30 seconds...")
        time.sleep(30)
        
        # Get stats
        stats = sensor.get_heart_rate_stats(minutes=1)
        print(f"Heart rate stats: {stats}")
        
        # Calibrate (for demonstration)
        print("Calibrating resting heart rate...")
        calibration = sensor.calibrate_resting_hr(user_id="test_user", duration_seconds=10)
        print(f"Calibration result: {calibration}")
        
    finally:
        # Clean up
        sensor.disconnect()
        print("Sensor disconnected")
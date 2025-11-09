"""Facial recognition service with person switching logic."""

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from typing import Optional, Dict, Any, List
import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech.conversation.database import DatabaseManager

# Initialize InsightFace model globally
print("[FacialRecognition] Initializing InsightFace Model...")
FACE_APP = FaceAnalysis()
FACE_APP.prepare(ctx_id=-1)  # CPU
print("[FacialRecognition] InsightFace Model Ready.")

# Match threshold for face recognition
MATCH_THRESHOLD = 0.2  # Cosine Similarity

# Detection confidence threshold for face detection
DETECTION_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence score for face detection


class FacialRecognitionService:
    """Service for facial recognition with person switching logic."""
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None):
        """Initialize facial recognition service.
        
        Args:
            database_manager: Database manager instance (creates new one if not provided)
        """
        self.database_manager = database_manager
        if self.database_manager is None:
            try:
                self.database_manager = DatabaseManager()
            except Exception as e:
                print(f"[FacialRecognition] Warning: Database not available: {e}")
                self.database_manager = None
        
        # Person switching state
        self.frame_history: List[Optional[str]] = []  # Frame results (person_id or None)
        self.current_person_id: Optional[str] = None
        
        # FPS tracking for dynamic thresholds
        self.frame_timestamps: List[float] = []  # Timestamps of recent frames for FPS calculation
        self.fps_window_size = 30  # Number of frames to use for FPS calculation
        self.current_fps = 10.0  # Default to 10 FPS, will be updated dynamically
        self.history_size = 10  # Will be adjusted based on FPS
        
        # Base thresholds at 10 FPS (target: 0.5s for person, 0.7s for no-person)
        self.base_person_threshold = 5  # 5/10 frames at 10 FPS = 0.5s
        self.base_no_person_threshold = 7  # 7/10 frames at 10 FPS = 0.7s
        
        # Embedding averaging: person_id -> (averaged_embedding, count)
        self.embedding_averages: Dict[str, tuple[np.ndarray, int]] = {}
        
        # Cache face database to avoid reloading on every frame
        self._face_database_cache: Optional[Dict[str, np.ndarray]] = None
        self._face_database_cache_time: float = 0.0
        self._face_database_cache_ttl: float = 5.0  # Reload cache every 5 seconds
        
        # Cache person names to avoid repeated database queries
        self._person_name_cache: Dict[str, str] = {}
    
    def get_embedding_from_image_data(self, image_data: bytes) -> Optional[np.ndarray]:
        """Extract face embedding from image bytes.
        
        Args:
            image_data: Binary image data (JPEG/PNG)
            
        Returns:
            Face embedding array or None if no face found
        """
        if not image_data or len(image_data) == 0:
            print("[FacialRecognition] ❌ Empty image data provided")
            return None
        
        try:
            # Decode image from bytes
            try:
                nparr = np.frombuffer(image_data, np.uint8)
                if len(nparr) == 0:
                    print("[FacialRecognition] ❌ Empty image buffer")
                    return None
            except (ValueError, TypeError) as e:
                print(f"[FacialRecognition] ❌ Error creating numpy array from image data: {e}")
                return None
            except Exception as e:
                print(f"[FacialRecognition] ❌ Unexpected error creating numpy array: {e}")
                return None
            
            try:
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                print(f"[FacialRecognition] ❌ Error decoding image with OpenCV: {e}")
                return None
            
            if img is None:
                print("[FacialRecognition] ❌ Failed to decode image")
                return None
            
            if img.size == 0:
                print("[FacialRecognition] ❌ Decoded image is empty")
                return None
            
            # Detect faces and get embedding
            try:
                faces = FACE_APP.get(img)
            except Exception as e:
                print(f"[FacialRecognition] ❌ Error detecting faces: {e}")
                import traceback
                traceback.print_exc()
                return None
            
            if faces and len(faces) > 0:
                try:
                    # Check detection confidence score
                    det_score = faces[0].det_score
                    
                    # Filter by confidence threshold
                    if det_score < DETECTION_CONFIDENCE_THRESHOLD:
                        return None
                    
                    embedding = faces[0].embedding
                    if embedding is None or len(embedding) == 0:
                        return None
                    
                    return embedding
                except (AttributeError, IndexError) as e:
                    print(f"[FacialRecognition] ❌ Error accessing face data: {e}")
                    return None
                except Exception as e:
                    print(f"[FacialRecognition] ❌ Error processing face: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
            else:
                return None
        except Exception as e:
            print(f"[FacialRecognition] ❌ Unexpected error extracting embedding: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def load_face_database_from_db(self, force_reload: bool = False) -> Dict[str, np.ndarray]:
        """Load face embeddings from PostgreSQL database (with caching).
        
        Args:
            force_reload: If True, bypass cache and reload from database
        
        Returns:
            Dictionary mapping person_id to embedding array
        """
        import time
        
        # Check cache first (unless force_reload is True)
        current_time = time.time()
        if not force_reload and self._face_database_cache is not None:
            cache_age = current_time - self._face_database_cache_time
            if cache_age < self._face_database_cache_ttl:
                # Cache is still valid
                return self._face_database_cache
        
        # Cache miss or expired - load from database
        load_start_time = time.time()
        database = {}
        
        if not self.database_manager:
            print("[FacialRecognition] No database manager available")
            return database
        
        conn = None
        try:
            # Get all faces from database
            try:
                conn = self.database_manager._get_connection()
            except Exception as e:
                print(f"[FacialRecognition] Error getting database connection: {e}")
                return database
            
            try:
                with conn.cursor() as cur:
                    try:
                        cur.execute("SELECT person_id, embedding FROM faces WHERE embedding IS NOT NULL")
                    except Exception as e:
                        print(f"[FacialRecognition] Error executing database query: {e}")
                        return database
                    
                    try:
                        rows = cur.fetchall()
                    except Exception as e:
                        print(f"[FacialRecognition] Error fetching database rows: {e}")
                        return database
                    
                    for person_id, embedding_bytes in rows:
                        if not person_id:
                            continue
                        
                        if embedding_bytes:
                            try:
                                # Convert bytes back to numpy array
                                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                                if len(embedding) > 0:
                                    database[person_id] = embedding
                                else:
                                    print(f"[FacialRecognition] Warning: Empty embedding for person_id {person_id}")
                            except (ValueError, TypeError) as e:
                                print(f"[FacialRecognition] Error converting embedding bytes for person_id {person_id}: {e}")
                                continue
                            except Exception as e:
                                print(f"[FacialRecognition] Unexpected error processing embedding for person_id {person_id}: {e}")
                                continue
            finally:
                if conn:
                    try:
                        self.database_manager._return_connection(conn)
                    except Exception as e:
                        print(f"[FacialRecognition] Error returning database connection: {e}")
        except Exception as e:
            print(f"[FacialRecognition] Error loading face database: {e}")
            import traceback
            traceback.print_exc()
        
        # Update cache
        load_end_time = time.time()
        load_duration = (load_end_time - load_start_time) * 1000
        if load_duration > 100:  # Only log if slow (>100ms)
            print(f"[FacialRecognition] load_face_database_from_db() took {load_duration:.1f}ms (loaded {len(database)} embeddings)")
        
        self._face_database_cache = database
        self._face_database_cache_time = current_time
        
        return database
    
    def find_best_match(self, new_embedding: np.ndarray, database: Dict[str, np.ndarray]) -> tuple[Optional[str], float]:
        """Find best matching person in database.
        
        Args:
            new_embedding: Face embedding to match
            database: Dictionary of person_id -> embedding
            
        Returns:
            Tuple of (best_match_person_id, similarity_score) or (None, -1) if no match
        """
        best_match_id = None
        best_score = -1.0
        
        if not database:
            return None, -1.0
        
        if new_embedding is None or len(new_embedding) == 0:
            print("[FacialRecognition] Warning: Empty embedding provided for matching")
            return None, -1.0
        
        try:
            new_norm = np.linalg.norm(new_embedding)
            if new_norm == 0:
                print("[FacialRecognition] Warning: Zero-norm embedding provided")
                return None, -1.0
        except Exception as e:
            print(f"[FacialRecognition] Error calculating embedding norm: {e}")
            return None, -1.0
        
        for person_id, db_embedding in database.items():
            if db_embedding is None or len(db_embedding) == 0:
                continue
            
            try:
                # Calculate cosine similarity
                db_norm = np.linalg.norm(db_embedding)
                if db_norm == 0:
                    continue
                
                dot_product = np.dot(new_embedding, db_embedding)
                score = dot_product / (new_norm * db_norm)
                
                if score > best_score:
                    best_score = score
                    best_match_id = person_id
            except (ValueError, TypeError) as e:
                print(f"[FacialRecognition] Error calculating similarity for person_id {person_id}: {e}")
                continue
            except Exception as e:
                print(f"[FacialRecognition] Unexpected error matching person_id {person_id}: {e}")
                continue
        
        return best_match_id, float(best_score)
    
    def recognize_person(self, image_data: bytes) -> Optional[str]:
        """Recognize person from image data. Auto-creates new person if face detected but not matched.
        
        Args:
            image_data: Binary image data (JPEG/PNG)
            
        Returns:
            person_id if recognized or newly created, None if no face detected
        """
        if not image_data or len(image_data) == 0:
            print("[FacialRecognition] Warning: Empty image data in recognize_person")
            return None
        
        # Extract embedding
        try:
            embedding = self.get_embedding_from_image_data(image_data)
        except Exception as e:
            print(f"[FacialRecognition] Error getting embedding: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        if embedding is None:
            return None
        
        # Load database (with caching - won't reload every frame)
        try:
            database = self.load_face_database_from_db(force_reload=False)
        except Exception as e:
            print(f"[FacialRecognition] Error loading face database: {e}")
            database = {}
        
        # Find best match
        try:
            best_match_id, best_score = self.find_best_match(embedding, database)
        except Exception as e:
            print(f"[FacialRecognition] Error finding best match: {e}")
            import traceback
            traceback.print_exc()
            best_match_id = None
            best_score = -1.0
        
        # Check if match is above threshold
        if best_match_id and best_score >= MATCH_THRESHOLD:
            try:
                # Update running average for this person
                if best_match_id in self.embedding_averages:
                    avg_embedding, count = self.embedding_averages[best_match_id]
                    # Weighted average: new_avg = (old_avg * count + new_embedding) / (count + 1)
                    new_count = count + 1
                    new_avg = (avg_embedding * count + embedding) / new_count
                    self.embedding_averages[best_match_id] = (new_avg, new_count)
                else:
                    # First time seeing this person in this session, initialize with current embedding
                    self.embedding_averages[best_match_id] = (embedding.copy(), 1)
            except Exception as e:
                print(f"[FacialRecognition] Error updating embedding average: {e}")
                # Continue anyway - return the matched person_id
            
            return best_match_id
        
        # No match found - create new person entry
        if not database or best_score < MATCH_THRESHOLD:
            import uuid
            try:
                new_person_id = f"Unnamed_{uuid.uuid4().hex[:8]}"
            except Exception as e:
                print(f"[FacialRecognition] Error generating UUID: {e}")
                return None
            
            # Save image to tmp directory
            try:
                # Decode image from bytes again to save
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is not None:
                    try:
                        # Create tmp directory in back_end
                        back_end_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        tmp_dir = os.path.join(back_end_dir, "tmp")
                        os.makedirs(tmp_dir, exist_ok=True)
                        
                        # Create filename with timestamp and person_id
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                        filename = f"{new_person_id}_{timestamp}.jpg"
                        filepath = os.path.join(tmp_dir, filename)
                        
                        # Save image
                        cv2.imwrite(filepath, img)
                    except OSError as e:
                        print(f"[FacialRecognition] Error creating tmp directory or saving image: {e}")
                    except Exception as e:
                        print(f"[FacialRecognition] Error saving image: {e}")
            except Exception as e:
                print(f"[FacialRecognition] Error decoding image for saving: {e}")
                # Continue - image saving is optional
            
            # Save to database (async/non-blocking - don't wait for completion)
            if self.database_manager:
                try:
                    # Convert embedding to bytes for database storage
                    embedding_bytes = embedding.tobytes()
                    
                    # Invalidate cache so next load will get the new person
                    self._face_database_cache = None
                    
                    # Create face record in database (this is still blocking, but necessary for new person)
                    # TODO: Could make this async in the future
                    self.database_manager.create_or_update_face(
                        person_id=new_person_id,
                        embedding=embedding_bytes,
                        count=1,
                        person_name="Unknown"
                    )
                    
                    # Initialize average for this new person
                    self.embedding_averages[new_person_id] = (embedding.copy(), 1)
                except Exception as e:
                    print(f"[FacialRecognition] Error saving new person to database: {e}")
                    # Continue - return the new person_id anyway
            
            return new_person_id
        
        # No match found and couldn't create new person
        return None
    
    def _update_fps(self) -> None:
        """Update FPS calculation from recent frame timestamps."""
        current_time = time.time()
        self.frame_timestamps.append(current_time)
        
        # Keep only recent timestamps for FPS calculation
        if len(self.frame_timestamps) > self.fps_window_size:
            self.frame_timestamps.pop(0)
        
        # Calculate FPS if we have at least 2 timestamps
        if len(self.frame_timestamps) >= 2:
            time_span = self.frame_timestamps[-1] - self.frame_timestamps[0]
            if time_span > 0:
                self.current_fps = (len(self.frame_timestamps) - 1) / time_span
            else:
                self.current_fps = 10.0  # Default fallback
        else:
            self.current_fps = 10.0  # Default until we have enough data
        
        # Adjust history_size based on FPS (target: ~1 second of history)
        # At 10 FPS: 10 frames = 1 second
        # At 30 FPS: 30 frames = 1 second
        self.history_size = max(5, min(30, int(self.current_fps)))
    
    def _get_person_threshold(self) -> int:
        """Get dynamic threshold for person detection based on current FPS.
        
        Returns:
            Number of frames required to detect person switch (target: 0.5s)
        """
        threshold = int(self.base_person_threshold * (self.current_fps / 10.0))
        return max(3, min(threshold, self.history_size - 1))
    
    def _get_no_person_threshold(self) -> int:
        """Get dynamic threshold for no-person detection based on current FPS.
        
        Returns:
            Number of frames required to detect no-person switch (target: 0.7s)
        """
        threshold = int(self.base_no_person_threshold * (self.current_fps / 10.0))
        return max(5, min(threshold, self.history_size - 1))
    
    def update_frame_history(self, person_id: Optional[str]) -> None:
        """Update frame history with new result.
        
        Args:
            person_id: Person ID from current frame (None if no person)
        """
        # Update FPS tracking first
        self._update_fps()
        
        # Update frame history
        self.frame_history.append(person_id)
        
        # Keep only last N frames (history_size is now dynamic)
        if len(self.frame_history) > self.history_size:
            self.frame_history.pop(0)
    
    def should_switch_to_no_person(self) -> bool:
        """Check if should switch from person to no person.
        
        Returns:
            True if threshold number of last frames show no person (target: 0.7s)
        """
        threshold = self._get_no_person_threshold()
        
        if len(self.frame_history) < threshold:
            return False
        
        no_person_count = sum(1 for p in self.frame_history if p is None)
        return no_person_count >= threshold
    
    def should_switch_to_different_person(self, new_person_id: Optional[str]) -> bool:
        """Check if should switch to a different person.
        
        Args:
            new_person_id: Person ID to check switching to
            
        Returns:
            True if threshold number of last frames show the new person (target: 0.5s)
        """
        if new_person_id is None:
            return False
        
        threshold = self._get_person_threshold()
        
        if len(self.frame_history) < threshold:
            return False
        
        new_person_count = sum(1 for p in self.frame_history if p == new_person_id)
        return new_person_count >= threshold
    
    def process_frame(self, image_data: bytes) -> tuple[Optional[str], bool]:
        """Process a frame and return person_id and switch status.
        
        Args:
            image_data: Binary image data (JPEG/PNG)
            
        Returns:
            Tuple of (person_id, switch_detected)
            - person_id: Current person ID (None for no person)
            - switch_detected: True if person switch was detected, False otherwise
        """
        if not image_data or len(image_data) == 0:
            print("[FacialRecognition] Warning: Empty image data in process_frame")
            return (self.current_person_id, False)
        
        try:
            # Recognize person in frame (auto-creates if new face detected)
            try:
                person_id = self.recognize_person(image_data)
            except Exception as e:
                print(f"[FacialRecognition] Error recognizing person: {e}")
                import traceback
                traceback.print_exc()
                return (self.current_person_id, False)
            
            # Update frame history
            try:
                self.update_frame_history(person_id)
            except Exception as e:
                print(f"[FacialRecognition] Error updating frame history: {e}")
                # Continue - history update failure shouldn't stop processing
            
            # Check for person switch
            try:
                # Case 1: Switch from person to no person (threshold-based, target: 0.7s)
                if self.current_person_id is not None and person_id is None:
                    try:
                        if self.should_switch_to_no_person():
                            # Save averaged embedding to database before switching away
                            try:
                                self._save_averaged_embedding(self.current_person_id)
                            except Exception as e:
                                print(f"[FacialRecognition] Error saving averaged embedding: {e}")
                            
                            # Get person name for display
                            try:
                                current_name = self._get_person_name(self.current_person_id) or self.current_person_id
                            except Exception:
                                current_name = self.current_person_id
                            
                            # Person switch: {current_name} -> None
                            self.current_person_id = None
                            return (None, True)  # Switch to no person detected
                    except Exception as e:
                        print(f"[FacialRecognition] Error checking switch to no person: {e}")
                
                # Case 2: Switch to different person (threshold-based, target: 0.5s)
                elif person_id is not None:
                    if self.current_person_id != person_id:
                        try:
                            if self.should_switch_to_different_person(person_id):
                                # Save averaged embedding for previous person before switching
                                if self.current_person_id is not None:
                                    try:
                                        self._save_averaged_embedding(self.current_person_id)
                                    except Exception as e:
                                        print(f"[FacialRecognition] Error saving averaged embedding: {e}")
                                
                                # Get person names for display
                                try:
                                    previous_name = self._get_person_name(self.current_person_id) if self.current_person_id else "None"
                                except Exception:
                                    previous_name = self.current_person_id or "None"
                                
                                try:
                                    new_name = self._get_person_name(person_id) or person_id
                                except Exception:
                                    new_name = person_id
                                
                                # Person switch: {previous_name} -> {new_name}
                                self.current_person_id = person_id
                                return (person_id, True)  # Switch to person detected
                        except Exception as e:
                            print(f"[FacialRecognition] Error checking switch to different person: {e}")
                    elif self.current_person_id is None and person_id is not None:
                        # Switch from no person to person (threshold-based, target: 0.5s)
                        try:
                            if self.should_switch_to_different_person(person_id):
                                try:
                                    new_name = self._get_person_name(person_id) or person_id
                                except Exception:
                                    new_name = person_id
                                
                                # Person switch: None -> {new_name}
                                self.current_person_id = person_id
                                return (person_id, True)  # Switch to person detected
                        except Exception as e:
                            print(f"[FacialRecognition] Error checking switch from no person: {e}")
            except Exception as e:
                print(f"[FacialRecognition] Error in person switch logic: {e}")
                import traceback
                traceback.print_exc()
            
            # No switch detected
            return (self.current_person_id, False)
        except Exception as e:
            print(f"[FacialRecognition] Fatal error in process_frame: {e}")
            import traceback
            traceback.print_exc()
            return (self.current_person_id, False)
    
    def _get_person_name(self, person_id: Optional[str]) -> Optional[str]:
        """Get person name from database (with caching).
        
        Args:
            person_id: Person ID
            
        Returns:
            Person name if found, None otherwise
        """
        if not person_id or not self.database_manager:
            return None
        
        # Check cache first
        if person_id in self._person_name_cache:
            return self._person_name_cache[person_id]
        
        # Cache miss - query database
        try:
            person_name = self.database_manager.get_person_name(person_id)
            if person_name:
                # Cache the result
                self._person_name_cache[person_id] = person_name
            return person_name
        except Exception:
            return None
    
    def invalidate_person_name_cache(self, person_id: Optional[str] = None) -> None:
        """Invalidate person name cache.
        
        Args:
            person_id: Specific person ID to invalidate, or None to clear all
        """
        if person_id:
            self._person_name_cache.pop(person_id, None)
        else:
            self._person_name_cache.clear()
    
    def _save_averaged_embedding(self, person_id: str) -> None:
        """Save the averaged embedding for a person to the database.
        
        Args:
            person_id: Person ID to save averaged embedding for
        """
        if not person_id:
            return
        
        if person_id not in self.embedding_averages:
            return
        
        try:
            avg_embedding, count = self.embedding_averages[person_id]
        except (KeyError, ValueError) as e:
            print(f"[FacialRecognition] Error accessing embedding average: {e}")
            return
        
        if avg_embedding is None or len(avg_embedding) == 0:
            print(f"[FacialRecognition] Warning: Empty embedding for person_id {person_id}")
            return
        
        if self.database_manager:
            try:
                # Convert averaged embedding to bytes
                embedding_bytes = avg_embedding.tobytes()
                
                if not embedding_bytes or len(embedding_bytes) == 0:
                    print(f"[FacialRecognition] Warning: Empty embedding bytes for person_id {person_id}")
                    return
                
                # Update face record in database with averaged embedding
                self.database_manager.create_or_update_face(
                    person_id=person_id,
                    embedding=embedding_bytes,
                    count=count
                )
            except Exception as e:
                print(f"[FacialRecognition] Error saving averaged embedding to database: {e}")
                import traceback
                traceback.print_exc()


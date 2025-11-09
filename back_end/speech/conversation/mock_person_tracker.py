"""Mock person tracker for testing person switching logic.

Cycles through fake people names on a 30-second interval.
"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable


class MockPersonTracker:
    """Mock person tracker that cycles through fake people names.
    
    Similar to ESP32 processing logic, runs in an independent thread
    and cycles between "Amy", "Bob", and "Charlie" every 30 seconds.
    """
    
    def __init__(
        self,
        on_person_changed: Optional[Callable[[Optional[str], datetime], None]] = None,
        interval_seconds: float = 30.0
    ):
        """Initialize mock person tracker.
        
        Args:
            on_person_changed: Callback called when person changes (person_id, timestamp)
            interval_seconds: Time interval between person switches (default: 30 seconds)
        """
        self.fake_people = ["Amy", "Bob", "Charlie"]
        self.on_person_changed = on_person_changed
        self.interval_seconds = interval_seconds
        
        self._stop_event = threading.Event()
        self._tracker_thread: Optional[threading.Thread] = None
        self._current_person_index = -1  # Start at -1 so first person is index 0
        self._is_running = False
    
    def start(self) -> None:
        """Start the person tracker thread."""
        if self._is_running:
            return  # Already running
        
        self._stop_event.clear()
        self._tracker_thread = threading.Thread(target=self._run_cycle, daemon=True)
        self._tracker_thread.start()
        self._is_running = True
        print(f"[MockPersonTracker] Started - cycling every {self.interval_seconds} seconds")
    
    def stop(self) -> None:
        """Stop the person tracker thread."""
        if not self._is_running:
            return
        
        self._stop_event.set()
        if self._tracker_thread and self._tracker_thread.is_alive():
            self._tracker_thread.join(timeout=2.0)
        self._is_running = False
        print("[MockPersonTracker] Stopped")
    
    def _run_cycle(self) -> None:
        """Main cycle loop running in separate thread."""
        try:
            while not self._stop_event.is_set():
                # Cycle to next person
                self._current_person_index = (self._current_person_index + 1) % len(self.fake_people)
                current_person = self.fake_people[self._current_person_index]
                timestamp = datetime.now()
                
                # Call callback with current person
                if self.on_person_changed:
                    try:
                        self.on_person_changed(current_person, timestamp)
                    except Exception as e:
                        print(f"[MockPersonTracker] Error in callback: {e}")
                
                print(f"[MockPersonTracker] Current person: {current_person}")
                
                # Wait for interval, checking stop event periodically
                elapsed = 0.0
                check_interval = 0.5  # Check every 0.5 seconds
                while elapsed < self.interval_seconds and not self._stop_event.is_set():
                    time.sleep(check_interval)
                    elapsed += check_interval
                
        except Exception as e:
            print(f"[MockPersonTracker] Error in cycle loop: {e}")
            import traceback
            traceback.print_exc()
    
    def get_current_person(self) -> Optional[str]:
        """Get the current person being tracked.
        
        Returns:
            Current person name or None if not started
        """
        if not self._is_running or self._current_person_index < 0:
            return None
        return self.fake_people[self._current_person_index]


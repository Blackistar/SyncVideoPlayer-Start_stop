import redis
import time
import json
from flask_socketio import emit

class VideoScheduler:
    def __init__(self, redis_client, socket_io, team_id="3"):
        self.redis = redis_client
        self.socket_io = socket_io
        self.scheduler_key = f"{team_id}:sc"

    def toggle_playback(self, song_name, current_time):
        """
        Toggle between play and stop states, tracking video progress.
        """
        scheduler_data = self._get_scheduler_data()
        sync_timestamp = time.time() + 10  # 10 second delay for synchronization
        
        if scheduler_data and scheduler_data.get("st") == "Play":
            # If currently playing, prepare to stop
            current_position = float(scheduler_data.get("c", 0))
            duration = float(scheduler_data.get("d", 0))
            
            # Update position and check for video completion
            if current_position < duration:
                new_position = str(current_time)
                if float(new_position) >= duration:
                    new_position = str(duration)
                    print(f"{song_name} has finished playing.")
            else:
                new_position = str(duration)
            
            new_state = {
                "song_name": song_name,
                "t": f"{int(sync_timestamp)}",
                "d": scheduler_data.get("d", "300.0"),
                "c": new_position,
                "st": "Stop"
            }
        else:
            # If currently stopped, prepare to play
            new_state = {
                "song_name": song_name,
                "t": f"{int(sync_timestamp)}",
                "d": scheduler_data.get("d", "300.0"),
                "c": scheduler_data.get("c", "0.0"),
                "st": "Play"
            }
        
        # Update Redis and notify all clients
        self._update_state(new_state)
        
    def get_playback_state(self):
        """
        Check current playback state and handle synchronization.
        Returns dict with current state and actions to take.
        """
        scheduler_data = self._get_scheduler_data()
        if not scheduler_data:
            return None
            
        current_time = time.time()
        sync_time = float(scheduler_data["t"])
        
        # If we haven't reached the sync point yet, wait
        if current_time < sync_time:
            return {
                "action": "wait", 
                "wait_time": sync_time - current_time
            }
            
        return {
            "action": scheduler_data["st"], #action = "st" -> depends on the rest of the code
            "position": float(scheduler_data["c"]), #position = "c" -> depends on the rest of code
            "song_name": scheduler_data["song_name"]
        }
    
    def _get_scheduler_data(self):
        """Helper to get and parse scheduler data from Redis"""
        data = self.redis.get(self.scheduler_key)
        return json.loads(data) if data else None
    
    def _update_state(self, new_state):
        """Helper to update Redis and notify clients"""
        # Update Redis
        self.redis.set(self.scheduler_key, json.dumps(new_state))
        
        # Notify all clients through Socket.IO
        self.socket_io.emit("sync_state", new_state, broadcast=True)

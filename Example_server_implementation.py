from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)
redis_client = redis.Redis(host='localhost', port=6379)
scheduler = VideoScheduler(redis_client, socketio)

@socketio.on('playback_toggle')
def handle_playback_toggle(data):
    """Handle play/stop button clicks from clients"""
    scheduler.toggle_playback(data['song_name'], data['current_time'])

# Example client-side implementation
class VideoClient:
    def __init__(self, video_element):
        self.video = video_element
        self.socket = socketio.connect()
        
        # Listen for sync updates from server
        self.socket.on('sync_state', self.handle_sync_state)
        
        # Start polling for state (backup for missed socket events)
        self.start_state_polling()
    
    def handle_sync_state(self, state):
        """Handle incoming sync state from server"""
        if state['st'] == 'Play':
            self.video.currentTime = float(state['c'])
            self.video.play()
        else:
            self.video.pause()
            self.video.currentTime = float(state['c'])
    
    def toggle_playback(self):
        """Handle play/stop button click"""
        self.socket.emit('playback_toggle', {
            'song_name': self.video.dataset.songName,
            'current_time': self.video.currentTime
        })
    
    def start_state_polling(self):
        """Backup polling for state updates"""
        def poll():
            state = scheduler.get_playback_state()
            if state:
                if state['action'] == 'wait':
                    time.sleep(state['wait_time'])
                else:
                    self.handle_sync_state(state)
            time.sleep(1)  # Poll every second
        
        import threading
        threading.Thread(target=poll, daemon=True).start()
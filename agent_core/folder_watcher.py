import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PortfolioHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.last_triggered = 0
        
    def on_any_event(self, event):
        if event.is_directory:
            return
            
        # Ignore agent directories and outputs
        path = event.src_path.replace("\\", "/")
        if "agent_core" in path or "templates" in path or "_site" in path or "/." in path:
            return
            
        # Debounce multiple rapid events (1 second)
        current = time.time()
        if current - self.last_triggered > 1.0:
            self.last_triggered = current
            self.callback()

def start_watching(root_dir, callback):
    event_handler = PortfolioHandler(callback)
    observer = Observer()
    observer.schedule(event_handler, root_dir, recursive=True)
    observer.start()
    print(f"[*] Watching for changes in {root_dir}")
    return observer

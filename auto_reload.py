#!/usr/bin/env python3
"""
Auto-reload script for AI POS Cash Flow Assistant
Watches for changes in Python files and automatically restarts the Gradio app
"""

import subprocess
import sys
import time
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AppHandler(FileSystemEventHandler):
    def __init__(self, watch_paths=None, app_script="src/app.py"):
        self.process = None
        self.app_script = app_script
        self.watch_paths = watch_paths or ["."]
        self.last_restart = 0
        self.min_restart_interval = 2  # Minimum seconds between restarts
        
        # Ensure app script exists
        if not Path(self.app_script).exists():
            print(f"❌ App script not found: {self.app_script}")
            sys.exit(1)
            
        print(f"🎯 Watching app: {self.app_script}")
        self.restart_app()
    
    def should_restart(self, event_path):
        """Determine if we should restart based on the file that changed"""
        # Only restart for Python files
        if not event_path.endswith('.py'):
            return False
            
        # Ignore this auto-reload script itself
        if event_path.endswith('auto_reload.py'):
            return False
            
        # Ignore common non-essential paths
        ignore_patterns = [
            '/.git/',
            '__pycache__',
            '.pytest_cache',
            '/venv/',
            '/.venv/',
            '/env/',
            '.pyc',
            '~'
        ]
        
        for pattern in ignore_patterns:
            if pattern in event_path:
                return False
                
        return True
    
    def on_modified(self, event):
        if not self.should_restart(event.src_path):
            return
            
        # Prevent rapid restarts
        current_time = time.time()
        if current_time - self.last_restart < self.min_restart_interval:
            return
            
        filename = os.path.basename(event.src_path)
        print(f"\n🔄 File {filename} changed, restarting app...")
        
        # Small delay to ensure file is fully written
        time.sleep(0.5)
        self.restart_app()
        self.last_restart = current_time
    
    def restart_app(self):
        # Kill existing process
        if self.process:
            print("⏹️  Stopping previous app...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing previous app...")
                self.process.kill()
                self.process.wait()
        
        # Start new process
        print("🚀 Starting app...")
        try:
            self.process = subprocess.Popen(
                [sys.executable, self.app_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=Path(self.app_script).parent.parent  # Run from project root
            )
            
            # Print the app output in real-time
            self._start_output_thread()
            
        except Exception as e:
            print(f"❌ Failed to start app: {e}")
    
    def _start_output_thread(self):
        """Start a thread to print app output in real-time"""
        import threading
        
        def print_output():
            while self.process and self.process.poll() is None:
                try:
                    line = self.process.stdout.readline()
                    if line:
                        # Add timestamp and formatting
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"[{timestamp}] {line.rstrip()}")
                except Exception:
                    break
        
        output_thread = threading.Thread(target=print_output, daemon=True)
        output_thread.start()

def main():
    """Main function to start the auto-reload watcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-reload for AI POS app")
    parser.add_argument(
        "--app", 
        default="src/app.py", 
        help="Path to the app script (default: src/app.py)"
    )
    parser.add_argument(
        "--watch", 
        nargs="+", 
        default=["src/", "data/"], 
        help="Directories to watch (default: src/ data/)"
    )
    
    args = parser.parse_args()
    
    # Validate watch paths
    valid_paths = []
    for path in args.watch:
        if Path(path).exists():
            valid_paths.append(path)
        else:
            print(f"⚠️  Watch path doesn't exist: {path}")
    
    if not valid_paths:
        print("❌ No valid watch paths found")
        sys.exit(1)
    
    print("📁 Starting AI POS Auto-Reload Watcher")
    print("=" * 50)
    print(f"🎯 App script: {args.app}")
    print(f"🔍 Watching: {', '.join(valid_paths)}")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 50)
    
    event_handler = AppHandler(valid_paths, args.app)
    observer = Observer()
    
    # Watch each specified directory
    for path in valid_paths:
        observer.schedule(event_handler, path=path, recursive=True)
        print(f"👁️  Watching {path}")
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping file watcher...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
            try:
                event_handler.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                event_handler.process.kill()
                event_handler.process.wait()
        print("✅ Auto-reload stopped.")
    
    observer.join()

if __name__ == "__main__":
    main()
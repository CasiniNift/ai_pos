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

# Check for watchdog dependency
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("❌ Installing watchdog dependency...")
    subprocess.run([sys.executable, "-m", "pip", "install", "watchdog"])
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("❌ Failed to install watchdog. Please install manually: pip install watchdog")
        sys.exit(1)

class AppHandler(FileSystemEventHandler):
    def __init__(self, watch_paths=None, app_script="src/app.py"):
        self.process = None
        self.app_script = Path(app_script).resolve()
        self.watch_paths = watch_paths or ["."]
        self.last_restart = 0
        self.min_restart_interval = 2  # Minimum seconds between restarts
        
        # Ensure app script exists
        if not self.app_script.exists():
            print(f"❌ App script not found: {self.app_script}")
            print(f"Current working directory: {Path.cwd()}")
            print("Available files in src/:")
            src_dir = Path("src")
            if src_dir.exists():
                for file in src_dir.glob("*.py"):
                    print(f"  - {file}")
            sys.exit(1)
            
        print(f"🎯 Watching app: {self.app_script}")
        self.restart_app()
    
    def should_restart(self, event_path):
        """Determine if we should restart based on the file that changed"""
        # Convert to Path object for easier handling
        path = Path(event_path)
        
        # Only restart for Python files
        if path.suffix != '.py':
            return False
            
        # Ignore this auto-reload script itself
        if path.name == 'auto_reload.py':
            return False
            
        # Ignore common non-essential paths
        ignore_patterns = [
            '.git',
            '__pycache__',
            '.pytest_cache',
            'venv',
            '.venv',
            'env',
            '.env'
        ]
        
        # Check if any part of the path contains ignore patterns
        path_parts = str(path).split(os.sep)
        for pattern in ignore_patterns:
            if any(pattern in part for part in path_parts):
                return False
        
        # Also ignore temporary files
        if path.name.endswith(('.pyc', '.pyo', '.tmp', '~')):
            return False
                
        return True
    
    def on_modified(self, event):
        # Skip directory events
        if event.is_directory:
            return
            
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
                print("✅ Previous app stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing previous app...")
                self.process.kill()
                self.process.wait()
        
        # Start new process
        print("🚀 Starting app...")
        try:
            # Use the project root as working directory
            project_root = self.app_script.parent.parent
            
            self.process = subprocess.Popen(
                [sys.executable, str(self.app_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=project_root
            )
            
            print(f"✅ App started with PID: {self.process.pid}")
            
            # Print the app output in real-time
            self._start_output_thread()
            
        except Exception as e:
            print(f"❌ Failed to start app: {e}")
            import traceback
            traceback.print_exc()
    
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
                        # Filter out some noise
                        if not any(noise in line.lower() for noise in ['warning', 'deprecated']):
                            print(f"[{timestamp}] {line.rstrip()}")
                except Exception as e:
                    print(f"Error reading output: {e}")
                    break
            
            # Check if process ended unexpectedly
            if self.process and self.process.poll() is not None:
                return_code = self.process.returncode
                if return_code != 0:
                    print(f"⚠️  App process ended with return code: {return_code}")
        
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
        default=["src/"], 
        help="Directories to watch (default: src/)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate watch paths
    valid_paths = []
    for path in args.watch:
        path_obj = Path(path)
        if path_obj.exists():
            valid_paths.append(str(path_obj.resolve()))
            if args.verbose:
                print(f"✅ Valid watch path: {path_obj.resolve()}")
        else:
            print(f"⚠️  Watch path doesn't exist: {path}")
    
    if not valid_paths:
        print("❌ No valid watch paths found")
        print("Current directory contents:")
        for item in Path.cwd().iterdir():
            print(f"  {item}")
        sys.exit(1)
    
    print("📁 Starting AI POS Auto-Reload Watcher")
    print("=" * 50)
    print(f"🎯 App script: {Path(args.app).resolve()}")
    print(f"🔍 Watching: {', '.join(valid_paths)}")
    print(f"📂 Working directory: {Path.cwd()}")
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
        print("🔄 File watcher is running...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping file watcher...")
        observer.stop()
        if event_handler.process:
            print("⏹️  Terminating app process...")
            event_handler.process.terminate()
            try:
                event_handler.process.wait(timeout=3)
                print("✅ App process terminated")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing app process...")
                event_handler.process.kill()
                event_handler.process.wait()
                print("✅ App process killed")
        print("✅ Auto-reload stopped.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    observer.join()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Development helper script for AI POS Cash Flow Assistant
Provides convenient commands for development tasks
"""

import subprocess
import sys
import argparse
from pathlib import Path
import os

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"

def run_app():
    """Run the app directly without auto-reload"""
    print("🚀 Starting AI POS app...")
    app_path = SRC_DIR / "app.py"
    if not app_path.exists():
        print(f"❌ App not found at {app_path}")
        return
    subprocess.run([sys.executable, str(app_path)])

def run_with_reload():
    """Run the app with auto-reload"""
    print("🔄 Starting AI POS app with auto-reload...")
    auto_reload_path = PROJECT_ROOT / "auto_reload.py"
    
    if not auto_reload_path.exists():
        print("📝 Creating auto_reload.py...")
        create_auto_reload_file()
    
    subprocess.run([sys.executable, str(auto_reload_path)])

def create_auto_reload_file():
    """Create the auto_reload.py file in project root"""
    auto_reload_content = '''#!/usr/bin/env python3
"""
Auto-reload script for AI POS Cash Flow Assistant
Watches for changes in Python files and automatically restarts the Gradio app
"""

import subprocess
import sys
import time
import os
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("❌ watchdog not installed. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "watchdog"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
APP_SCRIPT = SRC_DIR / "app.py"

class AppHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.last_restart = 0
        self.min_restart_interval = 2  # Minimum seconds between restarts
        
        # Ensure app script exists
        if not APP_SCRIPT.exists():
            print(f"❌ App script not found: {APP_SCRIPT}")
            sys.exit(1)
            
        print(f"🎯 Watching app: {APP_SCRIPT}")
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
        print(f"\\n🔄 File {filename} changed, restarting app...")
        
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
                [sys.executable, str(APP_SCRIPT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
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
    print("📁 Starting AI POS Auto-Reload Watcher")
    print("=" * 50)
    print(f"🎯 App script: {APP_SCRIPT}")
    print("🔍 Watching: src/ and project root")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 50)
    
    event_handler = AppHandler()
    observer = Observer()
    
    # Watch both src directory and project root
    observer.schedule(event_handler, path=str(SRC_DIR), recursive=True)
    observer.schedule(event_handler, path=str(PROJECT_ROOT), recursive=False)
    
    print(f"👁️  Watching {SRC_DIR}")
    print(f"👁️  Watching {PROJECT_ROOT}")
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\\n⏹️  Stopping file watcher...")
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
'''
    
    auto_reload_path = PROJECT_ROOT / "auto_reload.py"
    with open(auto_reload_path, 'w') as f:
        f.write(auto_reload_content)
    print("✅ Created auto_reload.py in project root")

def generate_sample_data():
    """Generate sample data for testing"""
    print("📊 Generating sample data...")
    generate_script = PROJECT_ROOT / "generate_sample_data.py"
    if generate_script.exists():
        subprocess.run([sys.executable, str(generate_script)])
    else:
        print("❌ generate_sample_data.py not found in project root")

def install_deps():
    """Install project dependencies"""
    print("📦 Installing dependencies...")
    requirements_file = PROJECT_ROOT / "requirements.txt"
    if requirements_file.exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
    else:
        print("❌ requirements.txt not found in project root")
        print("Installing basic requirements...")
        subprocess.run([sys.executable, "-m", "pip", "install", "gradio", "pandas", "numpy", "watchdog"])

def setup_project():
    """Set up the project for development"""
    print("🛠️  Setting up AI POS development environment...")
    
    # Create necessary directories
    directories = [DATA_DIR, SRC_DIR]
    for directory in directories:
        directory.mkdir(exist_ok=True)
        print(f"📁 Created/verified directory: {directory}")
    
    # Install dependencies
    install_deps()
    
    # Generate sample data if it doesn't exist
    if not (DATA_DIR / "pos_transactions_week.csv").exists():
        generate_sample_data()
    
    print("✅ Setup complete!")
    print("\\nNext steps:")
    print("  python3 dev.py run      # Start the app")
    print("  python3 dev.py reload   # Start with auto-reload")

def check_requirements():
    """Check if all requirements are installed"""
    print("🔍 Checking requirements...")
    
    required_packages = [
        "gradio", "pandas", "numpy", "watchdog"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\\n📦 Missing packages: {', '.join(missing)}")
        print("Run: python3 dev.py install")
    else:
        print("\\n✅ All requirements satisfied!")

def show_status():
    """Show project status"""
    print("📊 AI POS Project Status")
    print("=" * 30)
    
    # Check key files
    key_files = [
        (SRC_DIR / "app.py", "Main application"),
        (SRC_DIR / "analysis.py", "Analysis functions"),
        (SRC_DIR / "utils.py", "Utility functions"),
        (DATA_DIR / "pos_transactions_week.csv", "Sample transaction data"),
        (PROJECT_ROOT / "requirements.txt", "Dependencies file"),
        (PROJECT_ROOT / "generate_sample_data.py", "Data generator"),
    ]
    
    for file_path, description in key_files:
        status = "✅" if file_path.exists() else "❌"
        print(f"{status} {description}: {file_path}")
    
    print("\\n📁 Directory structure:")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Source code:  {SRC_DIR}")
    print(f"  Data files:   {DATA_DIR}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="AI POS Development Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 dev.py setup        # Set up development environment
  python3 dev.py run          # Start the app
  python3 dev.py reload       # Start with auto-reload (recommended)
  python3 dev.py data         # Generate sample data
  python3 dev.py check        # Check requirements
  python3 dev.py status       # Show project status
        """
    )
    
    parser.add_argument(
        "command",
        choices=["setup", "run", "reload", "data", "install", "check", "status"],
        help="Command to execute"
    )
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    commands = {
        "setup": setup_project,
        "run": run_app,
        "reload": run_with_reload,
        "data": generate_sample_data,
        "install": install_deps,
        "check": check_requirements,
        "status": show_status,
        "italian": run_italian,
        "spanish": run_spanish,
    }
    
    command_func = commands.get(args.command)
    if command_func:
        command_func()
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()

if __name__ == "__main__":
    main()
# run_servers.py
import subprocess
import time
import os
import sys
import signal
import threading

def run_server(module_name, port):
    """Run a server in a separate process"""
    process = subprocess.Popen(
        [sys.executable, "-m", module_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return process

def log_output(process, server_name):
    """Log the output from a server process"""
    for line in process.stdout:
        print(f"[{server_name}] {line.strip()}")

def start_servers():
    """Start all server processes"""
    servers = [
        ("server.weather_server", "Weather Server", 50052),
        ("server.todo_server", "Todo Server", 50053),
        ("server.calendar_server", "Calendar Server", 50054)
    ]
    
    processes = []
    threads = []
    
    print("Starting servers...")
    
    for module_name, server_name, port in servers:
        print(f"Starting {server_name} on port {port}...")
        process = run_server(module_name, port)
        processes.append((process, server_name))
        
        # Create a thread to log server output
        thread = threading.Thread(
            target=log_output, 
            args=(process, server_name),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        
        # Give each server a moment to start
        time.sleep(2)
    
    print("All servers started.")
    
    try:
        # Keep the script running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        
        # Terminate all processes
        for process, server_name in processes:
            print(f"Stopping {server_name}...")
            process.terminate()
        
        # Wait for processes to exit
        for process, server_name in processes:
            process.wait()
        
        print("All servers stopped.")

if __name__ == "__main__":
    start_servers()
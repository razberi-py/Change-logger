import sys
import time
import os
import difflib
from datetime import datetime
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box

console = Console()

class ChangeLogger:
    def __init__(self, watch_dir, event_callback=None):
        self.watch_dir = os.path.abspath(watch_dir)
        self.file_cache = {}
        self.log_file = os.path.join(self.watch_dir, "CHANGELOG_AUTO.md")
        self.event_callback = event_callback
        self.load_initial_state()

    def read_file_safe(self, file_path, retries=5, delay=0.5):
        """Attempts to read a file with retries to handle locking issues."""
        for i in range(retries):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.readlines()
            except PermissionError:
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    raise
            except Exception:
                raise
        return []

    def load_initial_state(self):
        """Reads all files in the directory to establish a baseline."""
        # Initialize the log file with a header if it doesn't exist
        if not os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Change Log\nStarted watching at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            except PermissionError:
                pass # Can't write log, skip initialization
        else:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n---\n\n## Session Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            except PermissionError:
                pass

        for root, dirs, files in os.walk(self.watch_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path == self.log_file:
                    continue
                try:
                    self.file_cache[file_path] = self.read_file_safe(file_path, retries=1)
                except Exception as e:
                    if self.event_callback:
                        self.event_callback(f"[yellow]Could not read {file_path}: {e}[/yellow]")


    def get_diff_stats(self, file_path, new_lines):
        old_lines = self.file_cache.get(file_path, [])
        
        diff = list(difflib.unified_diff(
            old_lines, 
            new_lines, 
            fromfile='Before', 
            tofile='After', 
            lineterm=''
        ))
        
        added = 0
        removed = 0
        modified_content = []

        for line in diff:
            if line.startswith('---') or line.startswith('+++'):
                continue
            if line.startswith('+'):
                added += 1
                modified_content.append(f"ADDED: {line[1:].strip()}")
            elif line.startswith('-'):
                removed += 1
                modified_content.append(f"REMOVED: {line[1:].strip()}")
        
        return {
            'added': added,
            'removed': removed,
            'diff_text': diff,
            'details': modified_content
        }

    def log_change(self, file_path, change_type, stats=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rel_path = os.path.relpath(file_path, self.watch_dir)
        
        # Use emoji for different change types
        icon = "📝"
        color = "blue"
        if change_type == "CREATED":
            icon = "🆕"
            color = "green"
        elif change_type == "DELETED":
            icon = "🗑️"
            color = "red"

        log_entry = f"\n### {icon} [{timestamp}] {change_type}: `{rel_path}`\n"
        
        summary_text = f"[{color}]{icon} {change_type}: {rel_path}[/{color}]"
        
        if stats:
            log_entry += f"- **Lines Added**: {stats['added']}\n"
            log_entry += f"- **Lines Removed**: {stats['removed']}\n"
            
            summary_text += f" (+{stats['added']} / -{stats['removed']})"

            if stats['diff_text']:
                log_entry += "\n<details>\n<summary>View Changes</summary>\n\n"
                log_entry += "```diff\n"
                for line in stats['diff_text']:
                    log_entry += line
                log_entry += "\n```\n"
                log_entry += "\n</details>\n"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            if self.event_callback:
                self.event_callback(summary_text)

        except Exception as e:
            if self.event_callback:
                self.event_callback(f"[red]Failed to write log: {e}[/red]")

    def update_cache(self, file_path, new_lines):
        self.file_cache[file_path] = new_lines

    def remove_from_cache(self, file_path):
        if file_path in self.file_cache:
            del self.file_cache[file_path]

class Handler(FileSystemEventHandler):
    def __init__(self, logger):
        self.logger = logger

    def on_modified(self, event):
        if event.is_directory: return
        if os.path.abspath(event.src_path) == os.path.abspath(self.logger.log_file): return
        
        try:
            # Wait briefly to ensure write is complete
            time.sleep(0.1)
            new_lines = self.logger.read_file_safe(event.src_path)
            
            stats = self.logger.get_diff_stats(event.src_path, new_lines)
            
            # Only log if there are actual changes
            if stats['added'] > 0 or stats['removed'] > 0:
                self.logger.log_change(event.src_path, "MODIFIED", stats)
                self.logger.update_cache(event.src_path, new_lines)
                
        except Exception as e:
            pass

    def on_created(self, event):
        if event.is_directory: return
        if os.path.abspath(event.src_path) == os.path.abspath(self.logger.log_file): return
        
        try:
            # Give OS time to release handle on new files
            time.sleep(0.1)
            new_lines = self.logger.read_file_safe(event.src_path)
            
            self.logger.update_cache(event.src_path, new_lines)
            self.logger.log_change(event.src_path, "CREATED", {'added': len(new_lines), 'removed': 0, 'details': [], 'diff_text': []})
        except Exception as e:
            if self.logger.event_callback:
                self.logger.event_callback(f"[red]Error processing creation for {event.src_path}: {e}[/red]")

    def on_deleted(self, event):
        if event.is_directory: return
        if os.path.abspath(event.src_path) == os.path.abspath(self.logger.log_file): return
        
        self.logger.remove_from_cache(event.src_path)
        self.logger.log_change(event.src_path, "DELETED")

def start_watching(path, event_callback):
    logger = ChangeLogger(path, event_callback)
    event_handler = Handler(logger)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    return observer

def make_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    return layout

def main():
    console.clear()
    console.print(Panel.fit("Python Batch Change Logger", style="bold blue"))
    
    watch_path = os.getcwd()
    
    while True:
        console.clear()
        console.print(Panel("Python Batch Change Logger", style="bold blue"))
        console.print(f"\nCurrent Watch Path: [cyan]{watch_path}[/cyan]\n")
        
        console.print("1. [green]Select Folder and Watch[/green]")
        console.print("2. [blue]Exit[/blue]")
        
        choice = Prompt.ask("Enter your choice", choices=["1", "2"], default="1")

        if choice == "1":
            new_path = Prompt.ask("Enter absolute path to watch", default=watch_path)
            if os.path.isdir(new_path):
                watch_path = new_path
                
                # Setup Event Tracking
                events = deque(maxlen=20)
                
                def add_event(event_text):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    events.appendleft(f"[{timestamp}] {event_text}")

                # Start Watching
                observer = start_watching(watch_path, add_event)
                
                try:
                    layout = make_layout()
                    layout["header"].update(Panel(f"Watching: {watch_path}", style="bold green"))
                    layout["footer"].update(Panel("Press Ctrl+C to stop watching", style="bold red"))
                    
                    with Live(layout, refresh_per_second=4, screen=True) as live:
                        while True:
                            # Update Body with Table of Events
                            table = Table(box=box.SIMPLE, show_header=False, expand=True)
                            table.add_column("Event")
                            
                            if not events:
                                table.add_row("[dim]Waiting for changes...[/dim]")
                            else:
                                for event in events:
                                    table.add_row(event)
                            
                            layout["body"].update(Panel(table, title="Live Change Log", border_style="blue"))
                            time.sleep(0.25)
                            
                except KeyboardInterrupt:
                    observer.stop()
                    observer.join()
                    console.print("[red]Stopped watching.[/red]")
                    time.sleep(1) # Let user see message
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    if observer:
                        observer.stop()
                        observer.join()
            else:
                console.print("[red]Invalid directory![/red]")
                time.sleep(2)

        elif choice == "2":
            console.print("Goodbye!")
            break

if __name__ == "__main__":
    main()

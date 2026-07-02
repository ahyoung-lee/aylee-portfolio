import os
import sys
import time
from folder_watcher import start_watching
from tree_parser import build_full_tree
from html_generator import generate_site

class PortfolioAgent:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.state = "IDLE"
        
    def transition(self, new_state):
        print(f"[STATE] {self.state} -> {new_state}")
        self.state = new_state
        
    def trigger_build(self):
        if self.state != "IDLE":
            print("[Warning] Build already in progress. Skipping.")
            return
            
        self.transition("TRIGGERED")
        
        try:
            # 1. Tree Parsing
            self.transition("TREE_PARSING")
            tree_data = build_full_tree(self.root_dir)
            
            # 2. Context Parsing implicitly happens in generation or can be pre-fetched
            # (We do it during html_generator for simplicity and isolation)
            self.transition("CONTEXT_PARSING & BUILDING")
            generate_site(tree_data, self.root_dir)
            
            self.transition("DEPLOYED")
            print("[Success] Build pipeline completed successfully.")
            
        except Exception as e:
            print(f"[ERROR] Pipeline failed: {e}")
        finally:
            self.transition("IDLE")

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    agent = PortfolioAgent(root_dir)
    
    print("="*50)
    print(" Portfolio Auto-Agent System Initialized ")
    print("="*50)
    
    # Initial build
    agent.trigger_build()
    
    # Start watching
    observer = start_watching(root_dir, agent.trigger_build)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[Shutdown] Agent stopped.")
        
    observer.join()

if __name__ == "__main__":
    main()

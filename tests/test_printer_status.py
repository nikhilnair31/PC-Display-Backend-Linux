import os
import json
import sys
import time

# Add the parent directory to sys.path so we can import functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions import get_printer_status, PRINTER_STATE_PATH

def run_test(name, mock_data):
    print(f"--- Testing: {name} ---")
    # Write the mock state to the json file
    with open(PRINTER_STATE_PATH, "w") as f:
        json.dump(mock_data, f)
    
    # Run the function
    try:
        result = get_printer_status(480, 100, 0)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    print("\n")

if __name__ == "__main__":
    # Test 1: Active Print (The 'UPDATE' state usually sent by OctoPrint)
    run_test("Active Printing (UPDATE event)", {
        "state": "UPDATE",
        "progress": 45,
        "time_remaining": 3665, # 1h 1m 5s
        "updated_at": time.time()
    })

    # Test 2: Just Started
    run_test("Started State", {
        "state": "STARTED",
        "progress": 0,
        "time_remaining": 0,
        "updated_at": time.time()
    })

    # Test 3: Completed (Recent)
    run_test("Just Completed", {
        "state": "COMPLETED",
        "progress": 100,
        "updated_at": time.time()
    })

    # Test 4: Completed (Old - should show IDLE)
    run_test("Completed long ago", {
        "state": "COMPLETED",
        "progress": 100,
        "updated_at": time.time() - 600 # 10 mins ago
    })

    # Test 5: Error State
    run_test("Printer Error", {
        "state": "ERROR",
        "updated_at": time.time()
    })
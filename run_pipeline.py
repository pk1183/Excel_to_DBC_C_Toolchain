import json
import os
import subprocess
import sys

def load_config(config_path):
    print(f"Loading configuration from {config_path}...")
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in config.json.")
        sys.exit(1)

def main():
    # Use absolute paths based on the script location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    
    config = load_config(config_path)
    
    # Resolve paths relative to base_dir
    excel_file = os.path.join(base_dir, config.get("excel_file", ""))
    dbc_output = os.path.join(base_dir, config.get("dbc_output", ""))
    c_output_dir = os.path.join(base_dir, config.get("c_output_dir", ""))
    
    print("toolchain started.")
    
    # Check if input Excel exists
    if not os.path.exists(excel_file):
        print(f"Error: Input Excel file not found at {excel_file}")
        print("Please ensure the file exists and is specified correctly in config.json.")
        sys.exit(1)

    # 1. Execute excel_to_dbc.py
    print("\n" + "=" * 40)
    print("Step 1: Converting Excel to DBC")
    print("=" * 40)
    script_excel_to_dbc = os.path.join(base_dir, "scripts", "excel_to_dbc.py")
    
    try:
        # We allow stdout to pass through so the user sees the script's reporting
        result_dbc = subprocess.run(
            [sys.executable, script_excel_to_dbc, excel_file, dbc_output],
            check=True
        )
    except subprocess.CalledProcessError:
        print("\nPipeline failed at Step 1 (Excel conversion).")
        sys.exit(1)

    # 2. Execute generate_code.py
    print("\n" + "=" * 40)
    print("Step 2: Generating C Code")
    print("=" * 40)
    script_generate_code = os.path.join(base_dir, "scripts", "generate_code.py")
    
    try:
        result_code = subprocess.run(
            [sys.executable, script_generate_code, dbc_output, c_output_dir],
            check=True
        )
    except subprocess.CalledProcessError:
        print("\nPipeline failed at Step 2 (Code generation).")
        sys.exit(1)
        
    print("\n" + "=" * 40)
    print("Pipeline Execution Complete")
    print("=" * 40)
    print(f"Status Report:")
    print(f" - DBC file generated: {dbc_output}")
    print(f" - C source files output to: {c_output_dir}")
    print("Check the console output above for detailed message/signal counts.")

if __name__ == "__main__":
    main()

import subprocess
import sys
import os

def generate_c_code(dbc_path, output_dir):
    """
    Generates C source code from a DBC file using cantools command line utility.
    Creates separate files for BMS (sender) and VCU (receiver) with clear naming.
    """
    if not os.path.exists(dbc_path):
        print(f"Error: DBC file not found at {dbc_path}")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating C code from {dbc_path} into {output_dir}...")
    
    # ==================== Generate VCU Code (Receiver - Unpack) ====================
    print("\n  [INFO] Generating VCU code (receiver/unpack functions)...")
    vcu_output = os.path.join(output_dir, "vcu_can_rx.c")
    vcu_header = os.path.join(output_dir, "vcu_can_rx.h")
    
    cmd_vcu = [
        "cantools", "generate_c_source",
        "--node", "VCU",
        "--database-name", "vcu_can_rx",  # Custom name for VCU files
        "--output-directory", output_dir,
        dbc_path
    ]
    
    try:
        result = subprocess.run(cmd_vcu, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"     {result.stdout.strip()}")
        
        # Verify files were created
        if os.path.exists(vcu_output) and os.path.exists(vcu_header):
            print(f"     [OK] Created: vcu_can_rx.h")
            print(f"     [OK] Created: vcu_can_rx.c")
        else:
            print(f"     [WARN] Expected files not found")
            
    except subprocess.CalledProcessError as e:
        print(f"     [ERROR] Error generating VCU code: {e}")
        if e.stderr:
            print(f"     Error details: {e.stderr}")
    except FileNotFoundError:
        print("Error: 'cantools' command not found.")
        print("Please install cantools: pip install cantools")
        sys.exit(1)
    
    # ==================== Generate BMS Code (Sender - Pack) ====================
    print("\n  [INFO] Generating BMS code (sender/pack functions)...")
    bms_output = os.path.join(output_dir, "bms_can_tx.c")
    bms_header = os.path.join(output_dir, "bms_can_tx.h")
    
    cmd_bms = [
        "cantools", "generate_c_source",
        "--node", "BMS",
        "--database-name", "bms_can_tx",  # Custom name for BMS files
        "--output-directory", output_dir,
        dbc_path
    ]
    
    try:
        result = subprocess.run(cmd_bms, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"     {result.stdout.strip()}")
        
        # Verify files were created
        if os.path.exists(bms_output) and os.path.exists(bms_header):
            print(f"     [OK] Created: bms_can_tx.h")
            print(f"     [OK] Created: bms_can_tx.c")
        else:
            print(f"     [WARN] Expected files not found")
            
    except subprocess.CalledProcessError as e:
        print(f"     [ERROR] Error generating BMS code: {e}")
        if e.stderr:
            print(f"     Error details: {e.stderr}")
    
    # ==================== Cleanup Old Files ====================
    print("\n  [INFO] Cleaning up old generated files...")
    old_files = [
        os.path.join(output_dir, "generated.h"),
        os.path.join(output_dir, "generated.c"),
        os.path.join(output_dir, "bms", "generated.h"),
        os.path.join(output_dir, "bms", "generated.c")
    ]
    
    removed_count = 0
    for old_file in old_files:
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
                removed_count += 1
                print(f"     [OK] Removed: {os.path.basename(old_file)}")
            except Exception as e:
                print(f"     [WARN] Could not remove {os.path.basename(old_file)}: {e}")
    
    # Remove old bms directory if empty
    old_bms_dir = os.path.join(output_dir, "bms")
    if os.path.exists(old_bms_dir):
        try:
            if not os.listdir(old_bms_dir):  # Check if empty
                os.rmdir(old_bms_dir)
                print(f"     [OK] Removed empty directory: bms/")
        except:
            pass
    
    if removed_count > 0:
        print(f"     Cleaned up {removed_count} old file(s)")
    else:
        print(f"     No old files to clean")
    
    # ==================== Summary ====================
    print(f"\n{'='*60}")
    print(f"[DONE] C Code Generation Complete")
    print(f"{'='*60}")
    print(f"  Output Directory: {output_dir}")
    print(f"  ")
    print(f"  VCU Files (Receiver - Unpack):")
    print(f"    - vcu_can_rx.h  (header)")
    print(f"    - vcu_can_rx.c  (implementation)")
    print(f"  ")
    print(f"  BMS Files (Sender - Pack):")
    print(f"    - bms_can_tx.h  (header)")
    print(f"    - bms_can_tx.c  (implementation)")
    print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_code.py <dbc_path> <output_dir>")
        sys.exit(1)
        
    generate_c_code(sys.argv[1], sys.argv[2])

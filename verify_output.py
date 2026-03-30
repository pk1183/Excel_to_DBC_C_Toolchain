"""
Verification script to check if the generated C code is correct.
This script checks for the "dummy signal" issue.
"""

import os
import sys

def check_generated_files():
    """Check if generated C files have proper signal definitions."""
    
    base_dir = r"c:\Users\4pkon\Documents\Excel to dbc\Excel_to_C_Toolchain"
    h_file = os.path.join(base_dir, "output", "generated", "generated.h")
    c_file = os.path.join(base_dir, "output", "generated", "generated.c")
    
    print("=" * 60)
    print("VERIFICATION: Checking Generated C Code")
    print("=" * 60)
    
    issues = []
    successes = []
    
    # Check .h file
    if os.path.exists(h_file):
        with open(h_file, 'r') as f:
            h_content = f.read()
            
        # Check for dummy signal (BAD)
        if "Dummy signal" in h_content:
            issues.append("❌ FAIL: Found 'Dummy signal' in .h file")
        else:
            successes.append("✅ PASS: No dummy signal in .h file")
            
        # Check for actual signal fields (GOOD)
        if "batt_voltage" in h_content.lower() or "battvoltage" in h_content.lower():
            successes.append("✅ PASS: Found BattVoltage field in struct")
        else:
            issues.append("❌ FAIL: BattVoltage field not found in struct")
            
        if "batt_temp" in h_content.lower() or "batttemp" in h_content.lower():
            successes.append("✅ PASS: Found BattTemp field in struct")
        else:
            issues.append("❌ FAIL: BattTemp field not found in struct")
    else:
        issues.append(f"❌ FAIL: .h file not found at {h_file}")
    
    # Check .c file
    if os.path.exists(c_file):
        with open(c_file, 'r') as f:
            c_content = f.read()
            
        # Check for void casts (BAD - indicates empty implementation)
        if "(void)src_p;" in c_content and "memset(&dst_p[0], 0," in c_content:
            issues.append("❌ FAIL: Found void cast pattern - empty pack implementation")
        else:
            successes.append("✅ PASS: No void cast pattern - proper pack implementation")
            
        # Check for bit manipulation (GOOD)
        if "<<" in c_content or ">>" in c_content:
            successes.append("✅ PASS: Found bit-shifting operations")
        else:
            issues.append("❌ FAIL: No bit-shifting operations found")
    else:
        issues.append(f"❌ FAIL: .c file not found at {c_file}")
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    for success in successes:
        print(success)
    
    for issue in issues:
        print(issue)
    
    print("\n" + "=" * 60)
    if len(issues) == 0:
        print("🎉 SUCCESS: All checks passed! C code is properly generated.")
        print("=" * 60)
        return 0
    else:
        print(f"⚠️  ISSUES FOUND: {len(issues)} problem(s) detected.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(check_generated_files())

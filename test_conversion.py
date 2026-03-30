import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, r'c:\Users\4pkon\Documents\Excel to dbc\Excel_to_C_Toolchain\scripts')

# Import and run the conversion
from excel_to_dbc import convert_excel_to_dbc

excel_path = r'c:\Users\4pkon\Documents\Excel to dbc\Excel_to_C_Toolchain\input\CAN_Matrix.xlsx'
dbc_path = r'c:\Users\4pkon\Documents\Excel to dbc\Excel_to_C_Toolchain\output\generated.dbc'

print("Testing Excel to DBC conversion...")
convert_excel_to_dbc(excel_path, dbc_path)
print("\nTest complete!")

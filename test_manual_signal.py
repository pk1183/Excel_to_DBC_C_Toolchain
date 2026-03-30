import cantools
from cantools.database.can import Database, Message, Signal
from cantools.database.conversion import BaseConversion

# Create a manual DB
db = Database()

# Create conversion objects
v_conversion = BaseConversion.factory(scale=0.01, offset=0)
t_conversion = BaseConversion.factory(scale=1, offset=-40)

# Create Signals with conversion parameter
v_sig = Signal(
    name='BattVoltage',
    start=0,
    length=16,
    byte_order='little_endian',
    is_signed=False,
    conversion=v_conversion,
    minimum=0,
    maximum=65,
    unit='V'
)

t_sig = Signal(
    name='BattTemp',
    start=16,
    length=8,
    byte_order='little_endian',
    is_signed=True,
    conversion=t_conversion,
    minimum=-40,
    maximum=125,
    unit='C'
)

# Create Message
msg = Message(
    frame_id=0x100,
    name='BatteryStatus',
    length=8,
    signals=[v_sig, t_sig]
)

db.messages.append(msg)

# Write DBC
with open('test_manual.dbc', 'w') as f:
    f.write(db.as_dbc_string())

print("Manual DBC created: test_manual.dbc")

# Try to generate C code
try:
    import subprocess
    result = subprocess.run(
        ['cantools', 'generate_c_source', '--output-directory', 'test_manual_output', 'test_manual.dbc'],
        capture_output=True,
        text=True
    )
    print("\nC Code Generation Output:")
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    print("\nCheck test_manual_output directory for generated files")
except Exception as e:
    print(f"Error: {e}")

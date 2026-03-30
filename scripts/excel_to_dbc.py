import pandas as pd
import cantools
from cantools.database.can import Database, Message, Signal, Node
from cantools.database.conversion import BaseConversion
import sys
import os

def convert_excel_to_dbc(excel_path, dbc_output_path):
    """
    Professional-grade Excel to DBC converter with full automotive feature support.
    Handles: Flexible headers, Extended IDs, Multiplexing, Value Descriptions, and Node binding.
    """
    print(f"Reading Excel: {excel_path}")
    
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error: Could not read Excel file. {e}")
        sys.exit(1)
    
    # ==================== STEP 1: HEADER NORMALIZATION ====================
    # Strip spaces and normalize column names
    df.columns = df.columns.str.strip()
    
    # Flexible column mapping - handles variations in Excel headers
    column_map = {
        'Message ID': ['Message ID (Hex)', 'ID (Hex)', 'Message ID', 'ID', 'CAN ID'],
        'Message Name': ['Message Name', 'Message', 'Name'],
        'ID Type': ['ID Type', 'Type', 'Frame Type'],
        'Cycle Time': ['Cycle Time (ms)', 'Cycle Time', 'Period'],
        'Signal Name': ['Signal Name', 'Signal'],
        'Start Bit': ['Start Bit', 'StartBit', 'Pos', 'Position'],
        'Length': ['Length', 'Size', 'Len', 'Bits'],
        'Byte Order': ['Byte Order', 'ByteOrder', 'Endian'],
        'Factor': ['Factor', 'Scale'],
        'Offset': ['Offset'],
        'Min': ['Min', 'Minimum'],
        'Max': ['Max', 'Maximum'],
        'Unit': ['Unit', 'Units'],
        'Multiplex Type': ['Multiplex Type', 'Mux Type', 'Multiplex'],
        'Multiplex Value': ['Multiplex Value', 'Mux Value'],
        'Value Descriptions': ['Value Descriptions', 'Values', 'Choices', 'Enum']
    }
    
    def find_column(target):
        """Find actual column name in DataFrame, handling variations."""
        for candidate in column_map.get(target, [target]):
            if candidate in df.columns:
                return candidate
        return None
    
    # Verify critical columns exist
    id_col = find_column('Message ID')
    name_col = find_column('Message Name')
    sig_name_col = find_column('Signal Name')
    
    if not id_col:
        print(f"CRITICAL ERROR: Could not find Message ID column.")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)
    
    if not name_col:
        print(f"CRITICAL ERROR: Could not find Message Name column.")
        sys.exit(1)
    
    # ==================== STEP 2: DATA CLEANING ====================
    # Convert hex strings (0x100) or integers to standard Python ints
    def safe_parse_id(x):
        try:
            return int(str(x), 16) if isinstance(x, str) and '0x' in str(x).lower() else int(x)
        except (ValueError, TypeError):
            return None

    df[id_col] = df[id_col].apply(safe_parse_id)
    
    # Drop rows where Message ID is invalid or missing
    df = df.dropna(subset=[id_col])
    
    # ==================== STEP 3: CREATE DATABASE & NODES ====================
    db = Database()
    
    # Define ECU nodes - critical for proper C code generation
    sender_node = Node(name='BMS', comment='Battery Management System')
    receiver_node = Node(name='VCU', comment='Vehicle Control Unit')
    db.nodes.append(sender_node)
    db.nodes.append(receiver_node)
    
    # ==================== STEP 4: PROCESS MESSAGES & SIGNALS ====================
    grouped = df.groupby([name_col, id_col])
    message_count = 0
    signal_count = 0
    
    for (msg_name, msg_id), group in grouped:
        signals = []
        
        # Check for Extended ID Type
        is_extended = False
        id_type_col = find_column('ID Type')
        if id_type_col and id_type_col in group.columns:
            id_type_val = str(group[id_type_col].iloc[0]).lower()
            is_extended = 'extended' in id_type_val or '29' in id_type_val
        
        # Get Cycle Time
        cycle_time = None
        cycle_col = find_column('Cycle Time')
        if cycle_col and cycle_col in group.columns:
            cycle_val = group[cycle_col].iloc[0]
            if pd.notna(cycle_val):
                cycle_time = int(cycle_val)
        
        # Process each signal in the message
        signal_bit_map = {}  # Track bit usage for overlap detection
        
        for _, row in group.iterrows():
            try:
                # ==================== VALIDATION 1: Required Fields ====================
                # Extract basic signal parameters with validation
                sig_name = str(row[sig_name_col]).strip()
                
                if not sig_name or sig_name == 'nan':
                    print(f"  ⚠ Warning: Skipping row with empty signal name")
                    continue
                
                # Validate Start Bit
                start_bit_col = find_column('Start Bit')
                if pd.isna(row[start_bit_col]):
                    print(f"  ✗ Error: Signal '{sig_name}' has no Start Bit. Skipping.")
                    continue
                start_bit = int(row[start_bit_col])
                
                # Validate Length
                length_col = find_column('Length')
                if pd.isna(row[length_col]):
                    print(f"  ✗ Error: Signal '{sig_name}' has no Length. Skipping.")
                    continue
                length = int(row[length_col])
                
                # Validate length is reasonable
                if length <= 0 or length > 64:
                    print(f"  ✗ Error: Signal '{sig_name}' has invalid length {length}. Must be 1-64 bits.")
                    continue
                
                # ==================== VALIDATION 2: Safe Defaults for Missing Data ====================
                # Byte order (default to Little Endian if missing)
                byte_order_col = find_column('Byte Order')
                if byte_order_col and pd.notna(row[byte_order_col]):
                    byte_order_val = str(row[byte_order_col]).lower()
                else:
                    byte_order_val = 'littleendian'
                    print(f"  ℹ Info: Signal '{sig_name}' has no Byte Order, defaulting to LittleEndian")
                
                byte_order = 'little_endian' if 'little' in byte_order_val or 'intel' in byte_order_val else 'big_endian'
                
                # Scaling parameters with safe defaults
                factor_col = find_column('Factor')
                if factor_col and pd.notna(row[factor_col]):
                    factor = float(row[factor_col])
                else:
                    factor = 1.0
                    print(f"  ℹ Info: Signal '{sig_name}' has no Factor, defaulting to 1.0")
                
                offset_col = find_column('Offset')
                if offset_col and pd.notna(row[offset_col]):
                    offset = float(row[offset_col])
                else:
                    offset = 0.0
                    print(f"  ℹ Info: Signal '{sig_name}' has no Offset, defaulting to 0.0")
                
                # Min/Max with intelligent defaults based on signal length
                min_col = find_column('Min')
                max_col = find_column('Max')
                
                if min_col and pd.notna(row[min_col]):
                    min_val = float(row[min_col])
                else:
                    min_val = 0.0
                    print(f"  ℹ Info: Signal '{sig_name}' has no Min, defaulting to 0.0")
                
                if max_col and pd.notna(row[max_col]):
                    max_val = float(row[max_col])
                else:
                    # Calculate max based on bit length
                    max_val = float((2 ** length) - 1)
                    print(f"  ℹ Info: Signal '{sig_name}' has no Max, defaulting to {max_val} (2^{length}-1)")
                
                # Validate min < max
                if min_val >= max_val:
                    print(f"  ✗ Error: Signal '{sig_name}' has Min ({min_val}) >= Max ({max_val}). Skipping.")
                    continue
                
                # Unit
                unit_col = find_column('Unit')
                unit = str(row[unit_col]).strip() if unit_col and pd.notna(row[unit_col]) else ""
                
                # Determine if signed
                is_signed = min_val < 0
                
                # ==================== VALIDATION 3: Bit Overlap Detection ====================
                # Check if this signal overlaps with existing signals
                signal_end_bit = start_bit + length - 1
                
                for bit in range(start_bit, signal_end_bit + 1):
                    if bit in signal_bit_map:
                        # Check if this is a multiplexed signal (overlaps are allowed)
                        multiplex_type_col = find_column('Multiplex Type')
                        is_multiplexed = False
                        
                        if multiplex_type_col and multiplex_type_col in row.index:
                            mux_type = str(row[multiplex_type_col]).strip().lower()
                            if mux_type == 'm':
                                is_multiplexed = True
                        
                        if not is_multiplexed:
                            overlapping_signal = signal_bit_map[bit]
                            print(f"  ⚠ Warning: Signal '{sig_name}' (bit {start_bit}-{signal_end_bit}) overlaps with '{overlapping_signal}' at bit {bit}")
                            print(f"     If this is intentional, add 'Multiplex Type' column with 'M' for multiplexer and 'm' for multiplexed signals.")
                
                # Record bit usage (only for non-multiplexed signals)
                multiplex_type_col = find_column('Multiplex Type')
                if not (multiplex_type_col and multiplex_type_col in row.index and str(row[multiplex_type_col]).strip().lower() == 'm'):
                    for bit in range(start_bit, signal_end_bit + 1):
                        signal_bit_map[bit] = sig_name
                
                # Create conversion object (CRITICAL: Use BaseConversion, not direct scale/offset)
                conversion = BaseConversion.factory(
                    scale=factor,
                    offset=offset
                )
                
                # ==================== ADVANCED FEATURES ====================
                
                # 1. Value Descriptions (for enums like "0:Off, 1:On")
                choices = None
                val_desc_col = find_column('Value Descriptions')
                if val_desc_col and val_desc_col in row.index and pd.notna(row[val_desc_col]):
                    try:
                        # Parse format: "0:Off, 1:On, 2:Error"
                        val_desc_str = str(row[val_desc_col])
                        choices = {}
                        for pair in val_desc_str.split(','):
                            if ':' in pair:
                                key, value = pair.split(':', 1)
                                choices[int(key.strip())] = value.strip()
                    except Exception as e:
                        print(f"  Warning: Could not parse value descriptions for {sig_name}: {e}")
                
                # 2. Multiplexing (M = multiplexer, m = multiplexed)
                is_multiplexer = False
                multiplexer_ids = None
                multiplexer_signal_name = None
                multiplex_type_col = find_column('Multiplex Type')
                multiplex_val_col = find_column('Multiplex Value')
                
                if multiplex_type_col and multiplex_type_col in row.index:
                    mux_type = str(row[multiplex_type_col]).strip()
                    if mux_type.upper() == 'M':
                        is_multiplexer = True
                    elif mux_type.lower() == 'm':
                        # This signal is multiplexed
                        if multiplex_val_col and multiplex_val_col in row.index and pd.notna(row[multiplex_val_col]):
                            mux_val = int(row[multiplex_val_col])
                            multiplexer_ids = [mux_val]
                            # Find the multiplexer signal name in this message group
                            # It's the signal with Multiplex Type = 'M'
                            mux_signals = group[group[multiplex_type_col].str.upper() == 'M']
                            if not mux_signals.empty:
                                multiplexer_signal_name = str(mux_signals.iloc[0][sig_name_col])
                
                
                # Create Signal object (without choices and multiplexer params)
                signal = Signal(
                    name=sig_name,
                    start=start_bit,
                    length=length,
                    byte_order=byte_order,
                    is_signed=is_signed,
                    conversion=conversion,
                    minimum=min_val,
                    maximum=max_val,
                    unit=unit,
                    receivers=[receiver_node.name]
                )
                
                # Set choices as attribute if present (not a constructor parameter)
                if choices:
                    signal.choices = choices
                
                # Set multiplexer attributes if present
                if is_multiplexer:
                    signal.is_multiplexer = is_multiplexer
                if multiplexer_ids:
                    signal.multiplexer_ids = multiplexer_ids
                if multiplexer_signal_name:
                    signal.multiplexer_signal = multiplexer_signal_name
                
                
                signals.append(signal)
                signal_count += 1
                print(f"  [OK] Signal: {sig_name} (Start: {start_bit}, Len: {length}, Signed: {is_signed})")
                
            except Exception as e:
                print(f"  [ERROR] Error processing signal {row.get(sig_name_col, 'Unknown')}: {e}")
                continue
        
        # Create Message if we have signals
        if signals:
            # Calculate message length (standard CAN = 8 bytes, but respect actual data)
            max_bit = max([s.start + s.length for s in signals])
            calculated_len = (max_bit + 7) // 8
            msg_len = max(8, calculated_len)  # Use at least 8 bytes for standard CAN
            
            try:
                # Create Message object
                message = Message(
                    frame_id=int(msg_id),
                    name=str(msg_name).replace(" ", "_"),  # Remove spaces from message names
                    length=msg_len,
                    signals=signals,
                    senders=[sender_node.name],
                    is_extended_frame=is_extended,
                    cycle_time=cycle_time
                )
                
                db.messages.append(message)
                message_count += 1
                
                ext_str = " (Extended)" if is_extended else ""
                cycle_str = f", {cycle_time}ms" if cycle_time else ""
                print(f"  [OK] Message: {msg_name} (ID: 0x{msg_id:X}{ext_str}, {len(signals)} signals{cycle_str})")
                
            except Exception as e:
                error_msg = str(e)
                if "overlapping" in error_msg.lower():
                    print(f"  [ERROR] Error: Overlapping signals in message {msg_name}")
                    print(f"     This usually means multiplexed signals need proper 'Multiplex Type' (M/m) and 'Multiplex Value' columns.")
                    print(f"     Details: {error_msg}")
                else:
                    print(f"  [ERROR] Error creating message {msg_name}: {e}")
                continue

    
    # ==================== STEP 5: GENERATE DBC FILE ====================
    os.makedirs(os.path.dirname(dbc_output_path), exist_ok=True)
    
    with open(dbc_output_path, 'w') as f:
        f.write(db.as_dbc_string())
    
    # ==================== SUMMARY ====================
    print(f"\n{'='*60}")
    print(f"[DONE] DBC Generation Complete")
    print(f"{'='*60}")
    print(f"  Messages:  {message_count}")
    print(f"  Signals:   {signal_count}")
    print(f"  Nodes:     {', '.join([n.name for n in db.nodes])}")
    print(f"  Output:    {dbc_output_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python excel_to_dbc.py <input_excel> <output_dbc>")
        sys.exit(1)
    
    convert_excel_to_dbc(sys.argv[1], sys.argv[2])
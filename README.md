# Excel to DBC to C Toolchain 🚗💻

An advanced, GUI-driven toolchain designed to streamline the workflow for automotive embedded software engineers. It effortlessly converts CAN matrix definitions from Excel spreadsheets into `.dbc` (CAN Database) files, and subsequently generates corresponding C code structures and headers. 

Additionally, it supports reverse-engineering existing `.dbc` files back into human-readable Excel formats, all wrapped in a premium PyQt6-based graphical interface inspired by the AUTOSAR Authoring Tool.

## ✨ Features

- **Excel to DBC Conversion**: Robustly transforms standard CAN matrix Excel grids into `.dbc` files.
- **DBC to C Code Generation**: Automatically generates production-ready C data structures and headers based on DBC inputs.
- **DBC to Excel Reverse Engineering**: Accurately unpacks existing `.dbc` databases into easily editable Excel sheets.
- **Premium User Interface**: A modern, interactive PyQt6 UI featuring custom themes, animated progress bars, and a multi-tab workflow.
- **CAN Frame Visualizer**: Real-time visualization of CAN frame layouts directly within the application.
- **Intelligent Input Handling**: Quality-of-life enhancements such as auto-capslock for CAN IDs and dynamic UI validation.
- **Headless Pipeline Mode**: Includes a fully-automated CLI pipeline for CI/CD integration.

## 📦 Requirements

- Python 3.8+
- The tool uses the following pivotal libraries:
  - `pandas`
  - `cantools`
  - `openpyxl`
  - `PyQt6`

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/Excel_to_DBC_C_Toolchain.git
   cd Excel_to_DBC_C_Toolchain
   ```

2. **Install the dependencies:**
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify directory structure:**
   Ensure the following directories exist (they should be present from the repository):
   - `input/` (Place your sample CAN matrices here)
   - `output/` (Generated files will appear here)

## 🛠️ Usage

This toolchain can be operated via the graphical interface or in headless mode using the pipeline script.

### Using the GUI (Recommended)
Launch the graphical interface by running:
```bash
python run_ui.py
```
**Workflow Steps:**
1. Use the **Excel Population** tab to load and configure your CAN matrix.
2. Advance to the **DBC Review / CAN Frame Visualizer** tabs to ensure the data is mapped correctly.
3. Finally, use the **C/H File Review** to generate and inspect the resulting embedded code.

### Using the CLI Pipeline
For batch operations or automation, modify the `config.json` with your desired paths:
```json
{
    "excel_file": "input/CAN_Matrix.xlsx",
    "dbc_output": "output/dbc/generated.dbc",
    "c_output_dir": "output/c_code",
    "bus_name": "CAN1"
}
```
Then execute:
```bash
python run_pipeline.py
```

## 📁 Directory Structure

```text
Excel_to_DBC_C_Toolchain/
├── config.json               # Headless pipeline configuration
├── input/                    # Target directory for input Excel tables and DBC files
├── output/                   # Destination for generated .dbc and .c/.h files
├── requirements.txt          # Python dependencies
├── run_pipeline.py           # CLI automated pipeline entrypoint 
├── run_ui.py                 # PyQt6 GUI application entrypoint
├── scripts/                  # Core Python algorithms
│   ├── dbc_to_excel.py       # DBC to Excel logic
│   ├── excel_to_dbc.py       # Excel to DBC logic
│   └── generate_code.py      # C code generation logic
└── ui/                       # Frontend application modules
```

## 🤝 Contributing
Contributions are welcome! Please feel free to open an issue or submit a pull request if you find bugs or have feature suggestions.

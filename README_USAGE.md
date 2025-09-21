# Stratified Placement System - Quick Start Guide

## 🚀 What Files Should Users Run?

### **Primary Entry Point (Recommended)**
```bash
python3 main.py
```

This is the **main script** users should run. It provides different modes:

| Command | Purpose |
|---------|---------|
| `python3 main.py --help` | for help |
| `python3 main.py --detailed` | + Quality analysis report, can be used with other options |
| `python3 main.py --visualize` | + Interactive multi-panel plots |
| `python3 main.py --trials 5` | Compare multiple random results (each with CSV + plot) |
| `python3 main.py --output-name "custom"` | Custom filename (custom.csv + custom_plot.png) can be used with other options|
| `python3 main.py --config user-config.yaml` | --config option can be used with any of the other options to input user config.yaml file |

### **Combining Options (Examples)**
```bash
# Detailed analysis with custom name and config
python3 main.py --detailed --output-name "room_v2" --config custom.yaml

# Visualization with custom output name
python3 main.py --visualize --output-name "final_design"

# Multiple trials with custom config and detailed analysis
python3 main.py --trials 3 --detailed --config high_density.yaml

# All options combined
python3 main.py --detailed --visualize --output-name "complete_analysis" --config custom.yaml
```

### **Other Entry Points**
- `python3 run_tests.py` - Verify system works correctly
- `python3 examples/example_advanced_placement.py` - Full demo (may pause for plots)
- `python3 examples/generate_random_individual.py` - Original simple version

## 🎲 Randomization & Reproducibility Control

### **Option 1: Edit config.yaml**
```yaml
optimization:
  random_seed: 42        # Fixed seed → same results every time
  # random_seed: null    # Random seed → different results each run
```

### **Option 2: Use multiple trials**
```bash
# Compare 10 different random configurations
python3 main.py --trials 10
```

This will automatically use different random seeds and show statistics.

### **Option 3: Programmatic control**
```python
from src.config_loader import create_placement_engine_from_config, load_config
import yaml

# Load and modify config
config = load_config("config.yaml")
config['optimization']['random_seed'] = 12345  # Your chosen seed
with open("temp_config.yaml", "w") as f:
    yaml.dump(config, f)

# Use modified config
engine = create_placement_engine_from_config("temp_config.yaml")
result = engine.place_all_entities()
```

## 📁 File Structure Overview

### **User Files (Run These)**
- `main.py` ⭐ **Main entry point**
- `run_tests.py` - Test the system
- `config.yaml` - Configuration parameters

### **Core System (src/ directory - Don't need to run directly)**
- `src/stratified_placement.py` - Main algorithm
- `src/placement_metrics.py` - Quality analysis
- `src/visualization.py` - Advanced plots
- `src/config_loader.py` - Configuration handling
- `src/placement_exporter.py` - Export system
- `src/validate_config.py` - Configuration validation

### **Examples (examples/ directory)**
- `examples/example_advanced_placement.py` - Full demo
- `examples/generate_random_individual.py` - Original simple version

### **Documentation**
- `CLAUDE.md` - Comprehensive documentation
- `placement_plan.md` - Algorithm methodology
- `README_USAGE.md` - This quick start guide

## 🎯 Common Use Cases

### **1. Quick placement with default settings**
```bash
python3 main.py
# Generates: placement_TIMESTAMP.csv + placement_TIMESTAMP_plot.png
```

### **2. Analyze placement quality**
```bash
python3 main.py --detailed
# Generates: CSV + plot + detailed quality analysis report
```

### **3. Generate different results each time**
Edit `config.yaml`:
```yaml
optimization:
  random_seed: null  # Enable this line
  # random_seed: 42   # Disable this line
```

Then run:
```bash
python3 main.py
```

### **4. Compare multiple random configurations**
```bash
python3 main.py --trials 10
# Generates: 10 CSV files + 10 plot files + comparison statistics
```

### **5. Modify parameters**
Edit `config.yaml` to change:
- Grid size (`width`, `height`)
- Entity counts and constraints
- Separation distances
- Optimization parameters
- **Complex allowed regions** with flexible exclusions

### **6. Verify everything works**
```bash
python3 run_tests.py
```

## 🗂️ Automatic File Generation

**Every run automatically generates both CSV data files AND visualization plots:**

### **File Generation Commands**
```bash
# Basic run → generates CSV + plot with timestamp names
python3 main.py

# Custom names → generates room_config_v2.csv + room_config_v2_plot.png
python3 main.py --output-name "room_config_v2"

# Multiple trials → generates 5 CSV files + 5 plot files
python3 main.py --trials 5
```

### **Generated Files**
- **CSV file**: `{name}.csv` - Entity coordinates for simulation
- **Plot file**: `{name}_plot.png` - Comprehensive visualization with quality metrics

### **Output File Format**

The system generates a simple **CSV file** with entity names and positions:

| Column | Description | Example |
|--------|-------------|---------|
| **name** | Entity identifier with location | `acinlet_x5_y3` |
| **type** | Entity type | `acinlet` |
| **x** | Grid X coordinate | `5` |
| **y** | Grid Y coordinate | `3` |

### **Example CSV Output**
```csv
name,type,x,y
vinlet_x8_y3,vinlet,8,3
voutlet_x3_y1,voutlet,3,1
acinlet_x5_y4,acinlet,5,4
acoutlet_x2_y7,acoutlet,2,7
```

### **Name Convention**
Each entity gets a unique name following the pattern: `{type}_x{x}_y{y}`

- `vinlet_x8_y3` → Ventilation inlet at grid position (8,3)
- `acinlet_x5_y4` → AC inlet at grid position (5,4)
- `acoutlet_x2_y7` → AC outlet at grid position (2,7)

## 💡 Tips

1. **For reproducible research**: Keep `random_seed: 42` (or any fixed number)
2. **For exploring variations**: Set `random_seed: null` 
3. **For comparisons**: Use `--trials N` to see statistics across multiple runs
4. **If visualization hangs**: Close the plot window to continue, or use `--detailed` instead of `--visualize`
5. **All plots are automatically saved**: Every run saves plots to `output/` directory
6. **For simulation pipelines**: CSV files are automatically generated for your solver
7. **For complex zones**: Use flexible exclusion methods (`exclude_y_list`, `exclude_x_list`) for irregular shapes

## ⚠️ Common Issues

- **Matplotlib hangs**: Close plot windows manually, or use command-line modes
- **Missing dependencies**: Run `pip3 install matplotlib PyYAML`
- **Configuration errors**: Run `python3 -c "from src.validate_config import ConfigValidator; validator = ConfigValidator(); validator.validate_config_file('config.yaml')"` to validate
- **Import errors**: Make sure you're in the correct directory

## 📊 Expected Output

Successful run shows:
```
Total entities placed: 24/24
Quality score: 0.775
Feasibility notes: 0
No separation violations

✓ CSV: output/placement_1757676251.csv
✓ Plot: output/placement_1757676251_plot.png
```

The system places HVAC components optimally across grid bands while maintaining proper separation distances and coverage guarantees.

## 🔧 Integration with Simulation Pipelines

### **Automated Workflow Integration**

```bash
#!/bin/bash
# Example simulation pipeline script

# Generate multiple placement configurations
for i in {1..10}; do
    python3 main.py --output-name "config_$i"
done

# Use in simulation solver (pseudo-code)
for config in output/config_*.csv; do
    simulation_solver --input "$config" --output "results/$(basename $config .csv)"
done
```

### **Python Integration Example**

```python
from src.placement_exporter import create_placement_file
from src.config_loader import create_placement_engine_from_config

# Generate placement
engine = create_placement_engine_from_config()
result = engine.place_all_entities()

# Export for simulation
csv_file = create_placement_file(
    result, engine.grid_region,
    output_name="simulation_config"
)

# Load in your simulation code
import csv
with open(csv_file) as f:
    reader = csv.DictReader(f)
    for row in reader:
        entity_name = row['name']
        entity_type = row['type']
        x = int(row['x'])
        y = int(row['y'])
        
        # Process for your solver
        place_entity(entity_name, entity_type, x, y)
```

### **Common Simulation Software**

- **OpenFOAM**: Parse CSV to set boundary conditions and geometries
- **ANSYS Fluent**: Import CSV for automated boundary condition setup  
- **COMSOL**: Read CSV to place entities in geometry
- **Custom Solvers**: Simple CSV parsing for any language/platform
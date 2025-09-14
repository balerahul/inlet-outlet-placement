# Configuration Parameters Reference

This document provides a comprehensive reference for all parameters available in the YAML configuration file used by the Stratified Placement System.

## 📁 Configuration File

- **`config.yaml`** - Main placement algorithm configuration

---

## 🏗️ Main Configuration (`config.yaml`)

### **Grid Section**
Defines the rectangular grid dimensions for placement.

```yaml
grid:
  width: 12    # Grid width (number of cells in X direction)
  height: 8    # Grid height (number of cells in Y direction)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `width` | integer | ✅ | - | Number of grid cells in X direction (horizontal) |
| `height` | integer | ✅ | - | Number of grid cells in Y direction (vertical) |

**Valid Values:**
- `width`: 1-100 (practical range)
- `height`: 1-100 (practical range)

**Examples:**
```yaml
grid:
  width: 15    # 15x10 room grid
  height: 10

grid:
  width: 8     # 8x8 square room
  height: 8
```

---

### **Stratification Section**
Controls the band-based stratification algorithm.

```yaml
stratification:
  num_bands: 4        # Number of horizontal bands
  anisotropy_y: 1.2   # Y-axis weighting factor
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `num_bands` | integer | ❌ | auto | Number of horizontal bands for stratification |
| `anisotropy_y` | float | ❌ | 1.0 | Y-axis distance weighting (>1 emphasizes vertical separation) |

**Parameter Details:**

**`num_bands`:**
- **Auto mode** (default): Uses number of distinct usable rows
- **Manual mode**: Specify exact number of bands
- **Range**: 1 to `grid.height`
- **Impact**: More bands = finer control, fewer bands = simpler distribution

**`anisotropy_y`:**
- **1.0**: Isotropic (equal weighting in X and Y)
- **>1.0**: Emphasizes vertical (Y-axis) separation
- **<1.0**: Emphasizes horizontal (X-axis) separation
- **Typical range**: 0.5 - 3.0

**Examples:**
```yaml
# Fine-grained control with strong vertical emphasis
stratification:
  num_bands: 8
  anisotropy_y: 2.0

# Coarse control with isotropic spacing  
stratification:
  num_bands: 2
  anisotropy_y: 1.0

# Auto bands with horizontal emphasis
stratification:
  anisotropy_y: 0.8
```

---

### **Entities Section**
Defines the types of entities to place and their constraints.

```yaml
entities:
  vinlet:
    count: 4
    intra_radius: 1.5
    color: "orange"
    allowed_region:
      x_min: 1
      x_max: 12
      y_min: 3
      y_max: 6
```

#### **Entity Types**
Standard entity types supported:
- `vinlet` - Ventilation supply inlets
- `voutlet` - Ventilation supply outlets  
- `acinlet` - Air conditioning inlets
- `acoutlet` - Air conditioning outlets

#### **Entity Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `count` | integer | ✅ | - | Number of entities to place |
| `intra_radius` | float | ❌ | 1.0 | Minimum distance between same-type entities |
| `color` | string | ❌ | "blue" | Color for visualization |
| `allowed_region` | object | ❌ | all cells | Region where entity can be placed |

#### **Allowed Region Specifications**

**Method 1: Rectangular Bounds**
```yaml
allowed_region:
  x_min: 2      # Minimum X coordinate (inclusive)
  x_max: 11     # Maximum X coordinate (inclusive)
  y_min: 3      # Minimum Y coordinate (inclusive)  
  y_max: 6      # Maximum Y coordinate (inclusive)
```

**Method 2: Y-Range Exclusion**
```yaml
allowed_region:
  exclude_y_range: [3, 6]  # Exclude Y coordinates 3-6 (use all others)
```

**Method 3: Y-List Exclusion**
```yaml
allowed_region:
  exclude_y_list: [2, 4, 7, 8]  # Exclude specific Y coordinates (more flexible)
```

**Method 4: X-Range Exclusion**
```yaml
allowed_region:
  exclude_x_range: [5, 8]  # Exclude X coordinates 5-8
```

**Method 5: X-List Exclusion**
```yaml
allowed_region:
  exclude_x_list: [1, 3, 9, 12]  # Exclude specific X coordinates
```

**Method 6: Explicit Cell List**
```yaml
allowed_region:
  cells:
    - [1, 1]    # Explicit (x,y) coordinates
    - [2, 3]
    - [5, 5]
```

#### **Entity Examples**

**Supply Air System:**
```yaml
entities:
  vinlet:
    count: 6
    intra_radius: 2.0      # Large separation for main inlets
    color: "red"
    allowed_region:        # Ceiling zone only
      x_min: 2
      x_max: 10
      y_min: 4
      y_max: 6
      
  voutlet:
    count: 4  
    intra_radius: 1.5
    color: "blue"
    allowed_region:        # Perimeter walls only
      exclude_y_range: [4, 6]
```

**Complex Zone Configuration:**
```yaml
entities:
  acinlet:
    count: 8
    allowed_region:        # Avoid specific problem areas
      exclude_y_list: [2, 5, 8]  # Avoid rows with obstacles
      exclude_x_list: [1, 12]    # Avoid edge columns
      
  acoutlet:
    count: 6
    allowed_region:        # Scattered placement avoiding center
      exclude_x_range: [5, 8]    # Avoid center columns
      exclude_y_list: [4]        # Avoid center row
```

**Equipment Avoidance:**
```yaml
entities:
  vinlet:
    count: 4
    allowed_region:
      # Complex exclusion: avoid equipment locations
      exclude_x_list: [6, 7]     # Equipment columns
      exclude_y_list: [3, 5, 7]  # Equipment rows
```

**Air Conditioning System:**
```yaml
entities:
  acinlet:
    count: 12
    intra_radius: 0.8      # Smaller units, closer spacing OK
    color: "orange"
    allowed_region:
      x_min: 1
      x_max: 12
      y_min: 2
      y_max: 7
```

---

### **Separation Section**
Controls minimum distances between different entity types.

```yaml
separation:
  cross_entity_radius: 1.0   # Min distance between different entity types
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cross_entity_radius` | float | ❌ | 1.0 | Minimum distance between different entity types |

**Examples:**
```yaml
# Tight spacing for small room
separation:
  cross_entity_radius: 0.5

# Generous spacing for large room  
separation:
  cross_entity_radius: 2.0
```

---

### **Optimization Section**
Controls the placement algorithm parameters.

```yaml
optimization:
  max_iterations: 100
  random_seed: 42
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `max_iterations` | integer | ❌ | 100 | Maximum iterations for blue-noise optimization |
| `random_seed` | integer/null | ❌ | 0 | Random seed for reproducibility |

**`random_seed` Options:**
- **Integer (e.g., 42)**: Fixed seed for reproducible results
- **null**: Generate random seed each run (different results)
- **"random"**: Same as null

**Examples:**
```yaml
# Reproducible results  
optimization:
  max_iterations: 200
  random_seed: 12345

# Random results each run
optimization:
  max_iterations: 50
  random_seed: null

# Quick placement (fewer iterations)
optimization:
  max_iterations: 25
  random_seed: 42
```

---

### **Visualization Section**
Controls visualization and output settings.

```yaml
visualization:
  figure_size: [16, 12]
  show_separation_circles: true
  show_band_boundaries: true  
  save_plots: false
  output_directory: "plots"
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `figure_size` | [width, height] | ❌ | [16, 12] | Figure dimensions in inches |
| `show_separation_circles` | boolean | ❌ | true | Draw separation radius circles |
| `show_band_boundaries` | boolean | ❌ | true | Draw stratification band lines |
| `save_plots` | boolean | ❌ | false | Auto-save plots to files |
| `output_directory` | string | ❌ | "plots" | Directory for saved plots |

**Examples:**
```yaml
# Large detailed plots
visualization:
  figure_size: [20, 15]
  show_separation_circles: true
  show_band_boundaries: true
  save_plots: true
  output_directory: "analysis/plots"

# Minimal clean plots
visualization:
  figure_size: [12, 8]
  show_separation_circles: false
  show_band_boundaries: false
```

---

### **Advanced Constraints Section**
Optional advanced features for specialized use cases.

```yaml
# Keep-out zones (optional)
keep_out_zones:
  - x_min: 5
    x_max: 7  
    y_min: 2
    y_max: 4
    description: "Equipment area"

# Advanced constraints (optional)
constraints:
  boundary_clearance: 0.5        # Min distance from grid edges
  prefer_symmetry: false         # Prefer symmetric placement
  symmetry_axis: "vertical"      # "vertical", "horizontal", "both"  
  grid_alignment: false          # Snap to grid intersections
  preferred_rows: [3, 5, 7]      # Preferred Y coordinates
```

**Keep-out Zones:**
Define areas where no entities can be placed (e.g., structural columns, equipment).

**Constraint Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `boundary_clearance` | float | 0.0 | Minimum distance from grid edges |
| `prefer_symmetry` | boolean | false | Attempt symmetric placement |
| `symmetry_axis` | string | "vertical" | Symmetry axis preference |
| `grid_alignment` | boolean | false | Snap entities to grid points |
| `preferred_rows` | [integers] | [] | Preferred Y coordinates for placement |

---

## 📊 Export Output

The system exports placement results as a simple CSV file with the following format:

```csv
name,type,x,y
vinlet_x8_y3,vinlet,8,3
voutlet_x3_y1,voutlet,3,1
acinlet_x5_y4,acinlet,5,4
acoutlet_x2_y7,acoutlet,2,7
```

Each entity gets a unique name following the pattern: `{type}_x{x}_y{y}`

---

## 📋 Configuration Examples

### **Small Room (Office)**
```yaml
grid:
  width: 8
  height: 6

entities:
  vinlet:
    count: 2
    intra_radius: 1.5
    allowed_region:
      y_min: 4
      y_max: 5
      
  voutlet:
    count: 2
    intra_radius: 1.2
    allowed_region:
      exclude_y_range: [4, 5]

separation:
  cross_entity_radius: 1.0

optimization:
  random_seed: 42
```

### **Large Room (Open Plan)**
```yaml
grid:
  width: 20
  height: 15

stratification:
  num_bands: 6
  anisotropy_y: 1.5

entities:
  vinlet:
    count: 8
    intra_radius: 3.0
    allowed_region:
      x_min: 3
      x_max: 18
      y_min: 6
      y_max: 10
      
  voutlet:
    count: 6
    intra_radius: 2.5
    allowed_region:
      exclude_y_range: [6, 10]

  acinlet:
    count: 15
    intra_radius: 1.5
    
  acoutlet:
    count: 12
    intra_radius: 2.0

separation:
  cross_entity_radius: 1.5

optimization:
  max_iterations: 200
  random_seed: null  # Random each time
```

### **Research Study Configuration**
```yaml
# Configuration for systematic parameter study

grid:
  width: 12
  height: 8

stratification:
  num_bands: 4
  anisotropy_y: 1.0

entities:
  vinlet:
    count: 4
    intra_radius: 1.0
    
  acoutlet:
    count: 8
    intra_radius: 1.5

separation:
  cross_entity_radius: 1.2

optimization:
  max_iterations: 150
  random_seed: null

# Generate multiple configurations
# Use with: python3 run_placement.py --trials 50 --export
```

---

## 🔧 Validation Rules

The system validates configurations according to these rules:

### **Required Fields**
- `grid.width` and `grid.height` must be positive integers
- Each entity must have a positive `count`

### **Feasibility Checks**  
- Entity count must not exceed available cells in allowed region
- Allowed region coordinates must be within grid bounds
- Separation radii should be reasonable for grid size

### **Automatic Adjustments**
- `num_bands` defaults to number of usable rows if not specified
- Empty allowed regions default to entire grid
- Missing colors default to standard values

### **Warning Conditions**
- Very small separation radii may cause placement conflicts
- Very large separation radii may make placement infeasible
- Large entity counts in small regions may reduce quality

---

## 🚀 Quick Start Templates

Copy and modify these templates for common scenarios:

### **Template 1: Balanced HVAC System**
```yaml
grid: {width: 12, height: 8}
entities:
  vinlet: {count: 3, intra_radius: 1.5}
  voutlet: {count: 3, intra_radius: 1.5}
  acinlet: {count: 6, intra_radius: 1.0}
  acoutlet: {count: 6, intra_radius: 1.0}
separation: {cross_entity_radius: 1.0}
optimization: {random_seed: 42}
```

### **Template 2: Supply-Heavy System**
```yaml
grid: {width: 15, height: 10}
entities:
  vinlet: {count: 8, intra_radius: 2.0}
  voutlet: {count: 4, intra_radius: 1.5}
separation: {cross_entity_radius: 1.5}
optimization: {random_seed: null}
```

### **Template 3: Research Study**
```yaml
grid: {width: 10, height: 10}
stratification: {num_bands: 5, anisotropy_y: 1.5}
entities:
  acinlet: {count: 12, intra_radius: 0.8}
  acoutlet: {count: 8, intra_radius: 1.2}
optimization: {max_iterations: 200, random_seed: null}
visualization: {save_plots: true}
```

Use these templates as starting points and adjust parameters based on your specific requirements!
"""
Configuration Loading System

Loads YAML configuration files and converts them to the appropriate
data structures for the stratified placement system.
"""

import yaml
from typing import Dict, List, Set, Any, Optional
from pathlib import Path

from .stratified_placement import (
    GridCell, Entity, GridRegion, EntityType, PlacementEngine
)


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")


def parse_allowed_region(region_config: Dict[str, Any], grid_region: GridRegion) -> Set[GridCell]:
    """
    Parse allowed region configuration into a set of grid cells
    
    Args:
        region_config: Region configuration dictionary
        grid_region: The full grid region
    
    Returns:
        Set of allowed grid cells
    """
    all_cells = grid_region.all_cells()
    
    if "exclude_y_range" in region_config:
        # Exclude specific Y range
        y_min, y_max = region_config["exclude_y_range"]
        return {cell for cell in all_cells if not (y_min <= cell.y <= y_max)}
    
    elif "exclude_y_list" in region_config:
        # Exclude specific Y coordinates (list)
        excluded_y = set(region_config["exclude_y_list"])
        return {cell for cell in all_cells if cell.y not in excluded_y}
    
    elif "exclude_x_range" in region_config:
        # Exclude specific X range
        x_min, x_max = region_config["exclude_x_range"]
        return {cell for cell in all_cells if not (x_min <= cell.x <= x_max)}
    
    elif "exclude_x_list" in region_config:
        # Exclude specific X coordinates (list)
        excluded_x = set(region_config["exclude_x_list"])
        return {cell for cell in all_cells if cell.x not in excluded_x}
    
    elif all(key in region_config for key in ["x_min", "x_max", "y_min", "y_max"]):
        # Include specific rectangular region
        x_min = region_config["x_min"]
        x_max = region_config["x_max"]
        y_min = region_config["y_min"]
        y_max = region_config["y_max"]
        
        return {cell for cell in all_cells 
                if x_min <= cell.x <= x_max and y_min <= cell.y <= y_max}
    
    elif "cells" in region_config:
        # Explicitly specified cells
        cells = set()
        for cell_config in region_config["cells"]:
            if isinstance(cell_config, dict):
                cells.add(GridCell(cell_config["x"], cell_config["y"]))
            elif isinstance(cell_config, (list, tuple)) and len(cell_config) == 2:
                cells.add(GridCell(cell_config[0], cell_config[1]))
        return cells
    
    else:
        # Default to all cells if no constraints specified
        return all_cells


def create_entities_from_config(config: Dict[str, Any], grid_region: GridRegion) -> List[Entity]:
    """Create entity list from configuration"""
    entities = []
    entity_config = config.get("entities", {})
    
    for entity_name, entity_data in entity_config.items():
        try:
            entity_type = EntityType(entity_name)
        except ValueError:
            raise ConfigurationError(f"Unknown entity type: {entity_name}")
        
        count = entity_data.get("count", 1)
        intra_radius = entity_data.get("intra_radius", 1.0)
        color = entity_data.get("color", "blue")
        
        # Parse allowed region
        region_config = entity_data.get("allowed_region", {})
        allowed_region = parse_allowed_region(region_config, grid_region)
        
        if count > len(allowed_region):
            raise ConfigurationError(
                f"Entity {entity_name} count ({count}) exceeds allowed region size ({len(allowed_region)})"
            )
        
        entity = Entity(
            entity_type=entity_type,
            count=count,
            allowed_region=allowed_region,
            intra_radius=intra_radius,
            color=color
        )
        
        entities.append(entity)
    
    return entities


def create_placement_engine_from_config(config_path: str = "config.yaml") -> PlacementEngine:
    """
    Create a configured PlacementEngine from YAML configuration
    
    Args:
        config_path: Path to the configuration file
    
    Returns:
        Configured PlacementEngine instance
    """
    config = load_config(config_path)
    
    # Create grid region
    grid_config = config.get("grid", {})
    width = grid_config.get("width", 10)
    height = grid_config.get("height", 8)
    grid_region = GridRegion(width, height)
    
    # Create entities
    entities = create_entities_from_config(config, grid_region)
    
    # Get placement parameters
    separation_config = config.get("separation", {})
    cross_entity_radius = separation_config.get("cross_entity_radius", 1.0)
    
    stratification_config = config.get("stratification", {})
    anisotropy_y = stratification_config.get("anisotropy_y", 1.0)
    num_bands = stratification_config.get("num_bands", None)
    
    optimization_config = config.get("optimization", {})
    random_seed = optimization_config.get("random_seed", 0)
    
    # Handle random seed configuration
    if random_seed is None or random_seed == "random":
        import time
        random_seed = int(time.time() * 1000000) % 2147483647  # Generate random seed
        print(f"Using random seed: {random_seed}")
    elif isinstance(random_seed, str) and random_seed.isdigit():
        random_seed = int(random_seed)
    
    # Create placement engine
    engine = PlacementEngine(
        grid_region=grid_region,
        entities=entities,
        cross_entity_radius=cross_entity_radius,
        anisotropy_y=anisotropy_y,
        num_bands=num_bands,
        random_seed=random_seed
    )
    
    return engine


def get_visualization_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Get visualization configuration"""
    config = load_config(config_path)
    return config.get("visualization", {})


def get_optimization_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Get optimization configuration"""
    config = load_config(config_path)
    return config.get("optimization", {})


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration and return list of issues
    
    Returns:
        List of validation error messages (empty if valid)
    """
    issues = []
    
    # Check required sections
    required_sections = ["grid", "entities"]
    for section in required_sections:
        if section not in config:
            issues.append(f"Missing required section: {section}")
    
    if "grid" in config:
        grid_config = config["grid"]
        width = grid_config.get("width", 0)
        height = grid_config.get("height", 0)
        
        if width <= 0:
            issues.append("Grid width must be positive")
        if height <= 0:
            issues.append("Grid height must be positive")
    
    if "entities" in config:
        entity_config = config["entities"]
        
        if not entity_config:
            issues.append("No entities defined")
        
        for entity_name, entity_data in entity_config.items():
            # Check entity type validity
            try:
                EntityType(entity_name)
            except ValueError:
                issues.append(f"Unknown entity type: {entity_name}")
            
            # Check count
            count = entity_data.get("count", 0)
            if count <= 0:
                issues.append(f"Entity {entity_name} count must be positive")
            
            # Check radius
            radius = entity_data.get("intra_radius", 1.0)
            if radius <= 0:
                issues.append(f"Entity {entity_name} intra_radius must be positive")
    
    return issues


def print_config_summary(config_path: str = "config.yaml"):
    """Print a summary of the configuration"""
    try:
        config = load_config(config_path)
        
        print("=" * 50)
        print("CONFIGURATION SUMMARY")
        print("=" * 50)
        
        # Grid info
        grid_config = config.get("grid", {})
        print(f"Grid Size: {grid_config.get('width', 'N/A')} x {grid_config.get('height', 'N/A')}")
        
        # Stratification info
        strat_config = config.get("stratification", {})
        print(f"Bands: {strat_config.get('num_bands', 'Auto')}")
        print(f"Anisotropy Y: {strat_config.get('anisotropy_y', 1.0)}")
        
        # Entity info
        entity_config = config.get("entities", {})
        print(f"\nEntities ({len(entity_config)}):")
        for name, data in entity_config.items():
            count = data.get("count", 1)
            radius = data.get("intra_radius", 1.0)
            print(f"  {name}: {count} entities, radius={radius}")
        
        # Separation info
        sep_config = config.get("separation", {})
        cross_radius = sep_config.get("cross_entity_radius", 1.0)
        print(f"\nCross-entity radius: {cross_radius}")
        
        # Validation
        issues = validate_config(config)
        if issues:
            print(f"\nValidation Issues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\nConfiguration is valid ✓")
        
        print("=" * 50)
        
    except ConfigurationError as e:
        print(f"Configuration Error: {e}")


if __name__ == "__main__":
    # Example usage
    print_config_summary()
    
    try:
        engine = create_placement_engine_from_config()
        result = engine.place_all_entities()
        
        print(f"\nPlacement completed!")
        print(f"Total placements: {sum(len(p) for p in result.placements.values())}")
        print(f"Feasibility notes: {len(result.feasibility_notes)}")
        
    except ConfigurationError as e:
        print(f"Failed to create placement engine: {e}")
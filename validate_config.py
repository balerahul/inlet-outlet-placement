#!/usr/bin/env python3
"""
Configuration Validation Tool

Validates YAML configuration files for the stratified placement system
and provides detailed feedback about parameter values and potential issues.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from config_loader import load_config, validate_config, ConfigurationError
from stratified_placement import EntityType, GridRegion, GridCell


class ConfigValidator:
    """Advanced configuration validator with detailed feedback"""
    
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.recommendations = []
    
    def validate_comprehensive(self, config_path: str) -> Dict[str, Any]:
        """Perform comprehensive validation with detailed feedback"""
        try:
            config = load_config(config_path)
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Failed to load configuration: {e}"],
                'warnings': [],
                'recommendations': [],
                'summary': {}
            }
        
        self.warnings = []
        self.errors = []
        self.recommendations = []
        
        # Basic validation
        basic_errors = validate_config(config)
        self.errors.extend(basic_errors)
        
        # Advanced validation
        self._validate_grid(config.get('grid', {}))
        self._validate_stratification(config.get('stratification', {}), config.get('grid', {}))
        self._validate_entities(config.get('entities', {}), config.get('grid', {}))
        self._validate_separation(config.get('separation', {}))
        self._validate_optimization(config.get('optimization', {}))
        self._validate_visualization(config.get('visualization', {}))
        
        # Cross-validation
        self._validate_feasibility(config)
        self._validate_performance(config)
        
        # Generate summary
        summary = self._generate_summary(config)
        
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'summary': summary
        }
    
    def _validate_grid(self, grid_config: Dict[str, Any]):
        """Validate grid configuration"""
        if not grid_config:
            self.errors.append("Missing 'grid' section")
            return
        
        width = grid_config.get('width', 0)
        height = grid_config.get('height', 0)
        
        # Size limits
        if width > 50 or height > 50:
            self.warnings.append(f"Large grid size ({width}x{height}) may impact performance")
        elif width > 100 or height > 100:
            self.errors.append(f"Grid size ({width}x{height}) exceeds practical limits")
        
        if width < 3 or height < 3:
            self.warnings.append(f"Small grid size ({width}x{height}) limits placement options")
        
        # Aspect ratio
        if width > 0 and height > 0:
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 5:
                self.warnings.append(f"Extreme aspect ratio ({aspect_ratio:.1f}:1) may affect stratification quality")
        
        # Grid area
        total_cells = width * height
        if total_cells > 2500:
            self.warnings.append(f"Large grid ({total_cells} cells) may require increased separation radii")
    
    def _validate_stratification(self, strat_config: Dict[str, Any], grid_config: Dict[str, Any]):
        """Validate stratification configuration"""
        if not strat_config:
            return  # Optional section
        
        height = grid_config.get('height', 0)
        num_bands = strat_config.get('num_bands')
        anisotropy_y = strat_config.get('anisotropy_y', 1.0)
        
        # Bands validation
        if num_bands is not None:
            if num_bands <= 0:
                self.errors.append("num_bands must be positive")
            elif num_bands > height:
                self.errors.append(f"num_bands ({num_bands}) cannot exceed grid height ({height})")
            elif num_bands > height / 2:
                self.warnings.append(f"Many bands ({num_bands}) for grid height ({height}) may create thin bands")
        
        # Anisotropy validation
        if anisotropy_y <= 0:
            self.errors.append("anisotropy_y must be positive")
        elif anisotropy_y > 5:
            self.warnings.append(f"High anisotropy_y ({anisotropy_y}) strongly favors vertical separation")
        elif anisotropy_y < 0.2:
            self.warnings.append(f"Low anisotropy_y ({anisotropy_y}) strongly favors horizontal separation")
    
    def _validate_entities(self, entities_config: Dict[str, Any], grid_config: Dict[str, Any]):
        """Validate entities configuration"""
        if not entities_config:
            self.errors.append("No entities defined")
            return
        
        width = grid_config.get('width', 0)
        height = grid_config.get('height', 0)
        total_cells = width * height
        
        total_entities = 0
        
        for entity_name, entity_data in entities_config.items():
            # Validate entity type
            try:
                EntityType(entity_name)
            except ValueError:
                self.errors.append(f"Unknown entity type: {entity_name}")
                continue
            
            count = entity_data.get('count', 0)
            intra_radius = entity_data.get('intra_radius', 1.0)
            
            total_entities += count
            
            # Count validation
            if count <= 0:
                self.errors.append(f"{entity_name}: count must be positive")
            elif count > total_cells / 2:
                self.warnings.append(f"{entity_name}: high count ({count}) may cause placement conflicts")
            
            # Radius validation
            if intra_radius <= 0:
                self.errors.append(f"{entity_name}: intra_radius must be positive")
            elif intra_radius > min(width, height):
                self.warnings.append(f"{entity_name}: large intra_radius ({intra_radius}) may prevent placement")
            
            # Region validation
            if 'allowed_region' in entity_data:
                self._validate_allowed_region(entity_name, entity_data['allowed_region'], width, height)
        
        # Overall entity validation
        if total_entities > total_cells * 0.8:
            self.warnings.append(f"High entity density ({total_entities}/{total_cells}) may reduce quality")
        
        if total_entities == 0:
            self.errors.append("No entities to place")
    
    def _validate_allowed_region(self, entity_name: str, region_config: Dict[str, Any], 
                                width: int, height: int):
        """Validate allowed region configuration"""
        if 'x_min' in region_config or 'x_max' in region_config:
            x_min = region_config.get('x_min', 1)
            x_max = region_config.get('x_max', width)
            
            if x_min < 1 or x_max > width or x_min > x_max:
                self.errors.append(f"{entity_name}: invalid x bounds [{x_min}, {x_max}] for grid width {width}")
        
        if 'y_min' in region_config or 'y_max' in region_config:
            y_min = region_config.get('y_min', 1)
            y_max = region_config.get('y_max', height)
            
            if y_min < 1 or y_max > height or y_min > y_max:
                self.errors.append(f"{entity_name}: invalid y bounds [{y_min}, {y_max}] for grid height {height}")
        
        if 'exclude_y_range' in region_config:
            y_range = region_config['exclude_y_range']
            if len(y_range) != 2:
                self.errors.append(f"{entity_name}: exclude_y_range must have exactly 2 values")
            elif y_range[0] > y_range[1]:
                self.errors.append(f"{entity_name}: invalid exclude_y_range {y_range}")
        
        if 'exclude_y_list' in region_config:
            y_list = region_config['exclude_y_list']
            if not isinstance(y_list, list):
                self.errors.append(f"{entity_name}: exclude_y_list must be a list")
            elif any(y < 1 or y > height for y in y_list):
                self.errors.append(f"{entity_name}: exclude_y_list contains invalid coordinates for grid height {height}")
        
        if 'exclude_x_range' in region_config:
            x_range = region_config['exclude_x_range']
            if len(x_range) != 2:
                self.errors.append(f"{entity_name}: exclude_x_range must have exactly 2 values")
            elif x_range[0] > x_range[1]:
                self.errors.append(f"{entity_name}: invalid exclude_x_range {x_range}")
        
        if 'exclude_x_list' in region_config:
            x_list = region_config['exclude_x_list']
            if not isinstance(x_list, list):
                self.errors.append(f"{entity_name}: exclude_x_list must be a list")
            elif any(x < 1 or x > width for x in x_list):
                self.errors.append(f"{entity_name}: exclude_x_list contains invalid coordinates for grid width {width}")
    
    def _validate_separation(self, sep_config: Dict[str, Any]):
        """Validate separation configuration"""
        if not sep_config:
            return  # Optional section
        
        cross_radius = sep_config.get('cross_entity_radius', 1.0)
        
        if cross_radius < 0:
            self.errors.append("cross_entity_radius cannot be negative")
        elif cross_radius > 10:
            self.warnings.append(f"Large cross_entity_radius ({cross_radius}) may make placement difficult")
    
    def _validate_optimization(self, opt_config: Dict[str, Any]):
        """Validate optimization configuration"""
        if not opt_config:
            return  # Optional section
        
        max_iterations = opt_config.get('max_iterations', 100)
        random_seed = opt_config.get('random_seed', 0)
        
        if max_iterations <= 0:
            self.errors.append("max_iterations must be positive")
        elif max_iterations < 10:
            self.warnings.append(f"Low max_iterations ({max_iterations}) may reduce optimization quality")
        elif max_iterations > 1000:
            self.warnings.append(f"High max_iterations ({max_iterations}) may be unnecessary")
        
        if isinstance(random_seed, int) and (random_seed < 0 or random_seed > 2**31):
            self.warnings.append(f"random_seed ({random_seed}) outside typical range")
    
    def _validate_visualization(self, vis_config: Dict[str, Any]):
        """Validate visualization configuration"""
        if not vis_config:
            return  # Optional section
        
        figure_size = vis_config.get('figure_size', [16, 12])
        
        if isinstance(figure_size, list) and len(figure_size) == 2:
            width, height = figure_size
            if width <= 0 or height <= 0:
                self.errors.append("figure_size dimensions must be positive")
            elif width > 30 or height > 30:
                self.warnings.append(f"Large figure_size {figure_size} may cause display issues")
    
    def _validate_feasibility(self, config: Dict[str, Any]):
        """Validate overall feasibility"""
        try:
            grid_config = config.get('grid', {})
            entities_config = config.get('entities', {})
            
            if not grid_config or not entities_config:
                return
            
            # Create grid region
            width = grid_config.get('width', 0)
            height = grid_config.get('height', 0)
            grid_region = GridRegion(width, height)
            
            # Check entity feasibility
            for entity_name, entity_data in entities_config.items():
                try:
                    entity_type = EntityType(entity_name)
                    count = entity_data.get('count', 0)
                    
                    # Simulate allowed region
                    region_config = entity_data.get('allowed_region', {})
                    if region_config:
                        from config_loader import parse_allowed_region
                        allowed_region = parse_allowed_region(region_config, grid_region)
                    else:
                        allowed_region = grid_region.all_cells()
                    
                    if count > len(allowed_region):
                        self.errors.append(f"{entity_name}: count ({count}) exceeds allowed region size ({len(allowed_region)})")
                
                except Exception as e:
                    self.warnings.append(f"{entity_name}: could not validate feasibility - {e}")
        
        except Exception as e:
            self.warnings.append(f"Could not perform feasibility check: {e}")
    
    def _validate_performance(self, config: Dict[str, Any]):
        """Validate performance implications"""
        grid_config = config.get('grid', {})
        entities_config = config.get('entities', {})
        opt_config = config.get('optimization', {})
        
        if not grid_config or not entities_config:
            return
        
        width = grid_config.get('width', 0)
        height = grid_config.get('height', 0)
        total_entities = sum(e.get('count', 0) for e in entities_config.values())
        max_iterations = opt_config.get('max_iterations', 100)
        
        # Performance estimates
        grid_size = width * height
        complexity_score = grid_size * total_entities * max_iterations
        
        if complexity_score > 1000000:
            self.warnings.append("High computational complexity - consider reducing grid size, entities, or iterations")
        
        if total_entities > 100:
            self.recommendations.append("Consider using fewer entities or larger separation radii for better performance")
        
        if grid_size > 1000:
            self.recommendations.append("Large grids may benefit from increased num_bands for better stratification")
    
    def _generate_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration summary"""
        summary = {}
        
        # Grid summary
        grid_config = config.get('grid', {})
        if grid_config:
            width = grid_config.get('width', 0)
            height = grid_config.get('height', 0)
            summary['grid'] = {
                'size': f"{width}x{height}",
                'total_cells': width * height,
                'aspect_ratio': round(max(width, height) / min(width, height) if min(width, height) > 0 else 0, 2)
            }
        
        # Entities summary
        entities_config = config.get('entities', {})
        if entities_config:
            total_entities = sum(e.get('count', 0) for e in entities_config.values())
            entity_types = list(entities_config.keys())
            
            summary['entities'] = {
                'total_count': total_entities,
                'types': entity_types,
                'density': round(total_entities / (width * height) * 100, 1) if width * height > 0 else 0
            }
        
        # Optimization summary
        opt_config = config.get('optimization', {})
        if opt_config:
            summary['optimization'] = {
                'max_iterations': opt_config.get('max_iterations', 100),
                'random_seed': opt_config.get('random_seed', 'default'),
                'reproducible': opt_config.get('random_seed') is not None and opt_config.get('random_seed') != "random"
            }
        
        return summary


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description="Validate YAML configuration files for the stratified placement system",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'config_file',
        nargs='?',
        default='config.yaml',
        help='Configuration file to validate (default: config.yaml)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed validation information'
    )
    
    parser.add_argument(
        '--warnings-only', '-w',
        action='store_true',
        help='Show only warnings and errors (no recommendations)'
    )
    
    args = parser.parse_args()
    
    validator = ConfigValidator()
    result = validator.validate_comprehensive(args.config_file)
    
    # Print results
    print("=" * 60)
    print("CONFIGURATION VALIDATION REPORT")
    print("=" * 60)
    print(f"File: {args.config_file}")
    print(f"Status: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    print()
    
    # Errors
    if result['errors']:
        print("🚨 ERRORS:")
        for error in result['errors']:
            print(f"  • {error}")
        print()
    
    # Warnings
    if result['warnings']:
        print("⚠️  WARNINGS:")
        for warning in result['warnings']:
            print(f"  • {warning}")
        print()
    
    # Recommendations
    if result['recommendations'] and not args.warnings_only:
        print("💡 RECOMMENDATIONS:")
        for rec in result['recommendations']:
            print(f"  • {rec}")
        print()
    
    # Summary
    if result['summary'] and args.verbose:
        print("📊 SUMMARY:")
        for section, data in result['summary'].items():
            print(f"  {section.title()}:")
            for key, value in data.items():
                print(f"    {key}: {value}")
        print()
    
    # Quick stats
    if not args.verbose:
        summary = result['summary']
        if 'grid' in summary and 'entities' in summary:
            grid_info = summary['grid']
            entity_info = summary['entities']
            print(f"Grid: {grid_info['size']}, Entities: {entity_info['total_count']}, Density: {entity_info['density']}%")
    
    print("=" * 60)
    
    # Exit code
    sys.exit(0 if result['valid'] else 1)


if __name__ == "__main__":
    main()
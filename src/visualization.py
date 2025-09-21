"""
Enhanced Visualization for Stratified Placement System

Provides comprehensive visualization capabilities including heatmaps,
band overlays, separation radius visualization, and metrics displays.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

from .stratified_placement import (
    GridCell, Entity, GridRegion, Stratification, PlacementResult,
    EntityType, euclidean_distance
)
from .placement_metrics import PlacementMetrics


class PlacementVisualizer:
    """Enhanced visualization system for stratified placement analysis"""
    
    def __init__(self, 
                 grid_region: GridRegion,
                 stratification: Stratification,
                 entities: List[Entity]):
        self.grid_region = grid_region
        self.stratification = stratification
        self.entities = entities
        self.entity_colors = {
            EntityType.VINLET: "orange",
            EntityType.VOUTLET: "cyan", 
            EntityType.ACINLET: "red",
            EntityType.ACOUTLET: "blue"
        }
    
    def plot_comprehensive_analysis(self, 
                                  result: PlacementResult,
                                  metrics: Dict[str, Any],
                                  figsize: Tuple[int, int] = (16, 12),
                                  save_path: Optional[str] = None):
        """
        Create a comprehensive multi-panel visualization
        
        Args:
            result: Placement result to visualize
            metrics: Analysis metrics from PlacementMetrics
            figsize: Figure size (width, height)
            save_path: Optional path to save the figure
        """
        fig = plt.figure(figsize=figsize)
        
        # Create subplot layout: 2x3 grid
        gs = fig.add_gridspec(3, 3, height_ratios=[2, 1, 1], width_ratios=[2, 1, 1])
        
        # Main placement plot (large, top-left)
        ax_main = fig.add_subplot(gs[0, :2])
        self.plot_placement_with_bands(result, ax_main)
        
        # Band coverage histogram (top-right)
        ax_coverage = fig.add_subplot(gs[0, 2])
        self.plot_coverage_histogram(metrics, ax_coverage)
        
        # Separation distance heatmap (middle-left)
        ax_heatmap = fig.add_subplot(gs[1, :2])
        self.plot_density_heatmap(result, ax_heatmap)
        
        # Separation violations chart (middle-right)
        ax_violations = fig.add_subplot(gs[1, 2])
        self.plot_separation_violations(metrics, ax_violations)
        
        # Y-distribution histograms (bottom row)
        ax_dist = fig.add_subplot(gs[2, :])
        self.plot_y_distribution_histograms(metrics, ax_dist)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_placement_with_bands(self, result: PlacementResult, ax: plt.Axes = None):
        """Plot placement with band boundaries and separation radii"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        # Draw grid
        for x in range(1, self.grid_region.width + 2):
            ax.axvline(x - 0.5, color="lightgray", linewidth=0.5, alpha=0.5)
        for y in range(1, self.grid_region.height + 2):
            ax.axhline(y - 0.5, color="lightgray", linewidth=0.5, alpha=0.5)
        
        # Draw band boundaries
        for band in self.stratification.bands:
            # Horizontal lines for band boundaries
            ax.axhline(band.y_min - 0.5, color="purple", linewidth=2, alpha=0.7, linestyle='--')
            ax.axhline(band.y_max + 0.5, color="purple", linewidth=2, alpha=0.7, linestyle='--')
            
            # Band label
            mid_y = (band.y_min + band.y_max) / 2
            ax.text(0.2, mid_y, f'Band {band.index}', 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
                   fontsize=8, ha='left', va='center')
        
        # Draw entity allowed regions (background shading)
        for entity in self.entities:
            region_cells = list(entity.allowed_region)
            if region_cells:
                xs = [cell.x for cell in region_cells]
                ys = [cell.y for cell in region_cells]
                
                # Create a light background for the allowed region
                color = self.entity_colors.get(entity.entity_type, "gray")
                ax.scatter(xs, ys, c=color, alpha=0.1, s=300, marker='s')
        
        # Plot entity placements
        for entity_type, placements in result.placements.items():
            if not placements:
                continue
            
            color = self.entity_colors.get(entity_type, "gray")
            xs, ys = zip(*[(p.x, p.y) for p in placements])
            
            # Plot with larger markers and edge colors
            ax.scatter(xs, ys, c=color, s=150, marker="s", 
                      label=f"{entity_type.value} ({len(placements)})", 
                      edgecolors="black", linewidth=1.5, alpha=0.9)
            
            # Add separation radius circles for visualization
            entity = next(e for e in self.entities if e.entity_type == entity_type)
            for x, y in zip(xs, ys):
                circle = plt.Circle((x, y), entity.intra_radius, 
                                  fill=False, color=color, alpha=0.3, linewidth=1)
                ax.add_patch(circle)
        
        ax.set_xlim(0.5, self.grid_region.width + 0.5)
        ax.set_ylim(0.5, self.grid_region.height + 0.5)
        ax.set_aspect("equal")
        ax.invert_yaxis()
        ax.set_title("Stratified Placement with Band Boundaries")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
    
    def plot_coverage_histogram(self, metrics: Dict[str, Any], ax: plt.Axes = None):
        """Plot band coverage rates for each entity"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 8))
        
        coverage_data = metrics.get('coverage_metrics', {})
        entities = [name for name in coverage_data.keys() if name != 'union']
        
        if not entities:
            ax.text(0.5, 0.5, "No coverage data", ha='center', va='center', transform=ax.transAxes)
            return
        
        band_rates = [coverage_data[entity]['band_coverage_rate'] for entity in entities]
        row_rates = [coverage_data[entity]['row_coverage_rate'] for entity in entities]
        
        x = np.arange(len(entities))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, band_rates, width, label='Band Coverage', alpha=0.7)
        bars2 = ax.bar(x + width/2, row_rates, width, label='Row Coverage', alpha=0.7)
        
        ax.set_ylabel('Coverage Rate')
        ax.set_title('Coverage Metrics by Entity')
        ax.set_xticks(x)
        ax.set_xticklabels([entity.replace('_', '\n') for entity in entities], rotation=45, ha='right')
        ax.legend()
        ax.set_ylim(0, 1.1)
        
        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                       f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    def plot_density_heatmap(self, result: PlacementResult, ax: plt.Axes = None):
        """Plot density heatmap of all placements"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create a density grid
        density_grid = np.zeros((self.grid_region.height, self.grid_region.width))
        
        # Count placements in each cell
        for placements in result.placements.values():
            for cell in placements:
                # Convert to 0-based indexing for numpy array
                y_idx = cell.y - 1
                x_idx = cell.x - 1
                if 0 <= y_idx < self.grid_region.height and 0 <= x_idx < self.grid_region.width:
                    density_grid[y_idx, x_idx] += 1
        
        # Create heatmap
        im = ax.imshow(density_grid, cmap='YlOrRd', aspect='equal', 
                      extent=[0.5, self.grid_region.width + 0.5, 
                             self.grid_region.height + 0.5, 0.5])
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Entity Count per Cell')
        
        # Add band boundaries
        for band in self.stratification.bands:
            ax.axhline(band.y_min - 0.5, color="white", linewidth=2, alpha=0.8, linestyle='--')
            ax.axhline(band.y_max + 0.5, color="white", linewidth=2, alpha=0.8, linestyle='--')
        
        ax.set_title('Placement Density Heatmap')
        ax.set_xlabel('X Coordinate')
        ax.set_ylabel('Y Coordinate')
    
    def plot_separation_violations(self, metrics: Dict[str, Any], ax: plt.Axes = None):
        """Plot separation violations as a bar chart"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 8))
        
        separation_data = metrics.get('separation_metrics', {})
        
        if not separation_data:
            ax.text(0.5, 0.5, "No separation data", ha='center', va='center', transform=ax.transAxes)
            return
        
        violation_counts = []
        labels = []
        colors = []
        
        for sep_name, sep_metrics in separation_data.items():
            violations = sep_metrics['violations']
            violation_counts.append(violations)
            labels.append(sep_name.replace('_', '\n'))
            
            # Color code by violation severity
            if violations == 0:
                colors.append('green')
            elif violations <= 2:
                colors.append('yellow')
            else:
                colors.append('red')
        
        bars = ax.bar(range(len(labels)), violation_counts, color=colors, alpha=0.7)
        
        ax.set_ylabel('Violation Count')
        ax.set_title('Separation Violations')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        
        # Add value labels on bars
        for bar, count in zip(bars, violation_counts):
            if count > 0:
                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                       str(count), ha='center', va='bottom', fontweight='bold')
    
    def plot_y_distribution_histograms(self, metrics: Dict[str, Any], ax: plt.Axes = None):
        """Plot Y-coordinate distribution histograms for all entities"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 4))
        
        hist_data = metrics.get('distribution_histograms', {})
        
        if not hist_data:
            ax.text(0.5, 0.5, "No distribution data", ha='center', va='center', transform=ax.transAxes)
            return
        
        # Collect all entity histograms (excluding union)
        entity_hists = {name: data for name, data in hist_data.items() 
                       if name != 'union_y' and name.endswith('_y')}
        
        if not entity_hists:
            ax.text(0.5, 0.5, "No entity histograms", ha='center', va='center', transform=ax.transAxes)
            return
        
        # Get all Y coordinates
        all_ys = set()
        for hist_info in entity_hists.values():
            all_ys.update(hist_info['histogram'].keys())
        y_coords = sorted(all_ys)
        
        # Plot each entity's distribution
        width = 0.8 / len(entity_hists)
        x = np.arange(len(y_coords))
        
        for i, (entity_name, hist_info) in enumerate(entity_hists.items()):
            counts = [hist_info['histogram'].get(y, 0) for y in y_coords]
            entity_type_name = entity_name.replace('_y', '')
            
            # Get color from entity type
            try:
                entity_type = EntityType(entity_type_name)
                color = self.entity_colors.get(entity_type, 'gray')
            except ValueError:
                color = 'gray'
            
            ax.bar(x + i * width, counts, width, label=entity_type_name, 
                  color=color, alpha=0.7)
        
        ax.set_xlabel('Y Coordinate (Row)')
        ax.set_ylabel('Entity Count')
        ax.set_title('Y-Coordinate Distribution by Entity')
        ax.set_xticks(x + width * (len(entity_hists) - 1) / 2)
        ax.set_xticklabels(y_coords)
        ax.legend()
        
        # Add band boundaries as vertical lines
        for band in self.stratification.bands:
            for y_boundary in [band.y_min - 0.5, band.y_max + 0.5]:
                if y_boundary in y_coords:
                    idx = y_coords.index(y_boundary)
                    ax.axvline(idx, color='purple', linestyle='--', alpha=0.7)


def plot_simple_placement(result: PlacementResult, 
                         grid_region: GridRegion,
                         entities: List[Entity],
                         title: str = "Entity Placement"):
    """Simple plotting function similar to the original"""
    visualizer = PlacementVisualizer(
        grid_region, 
        Stratification.create_horizontal_bands(grid_region, 4),  # Default 4 bands
        entities
    )
    
    fig, ax = plt.subplots(figsize=(8, 6))
    visualizer.plot_placement_with_bands(result, ax)
    ax.set_title(title)
    plt.show()


def compare_placements(results: List[PlacementResult], 
                      labels: List[str],
                      grid_region: GridRegion,
                      entities: List[Entity]):
    """Compare multiple placement results side by side"""
    n_results = len(results)
    if n_results == 0:
        return
    
    fig, axes = plt.subplots(1, n_results, figsize=(6*n_results, 6))
    if n_results == 1:
        axes = [axes]
    
    visualizer = PlacementVisualizer(
        grid_region,
        Stratification.create_horizontal_bands(grid_region, 4),
        entities
    )
    
    for i, (result, label) in enumerate(zip(results, labels)):
        visualizer.plot_placement_with_bands(result, axes[i])
        axes[i].set_title(label)
    
    plt.tight_layout()
    plt.show()
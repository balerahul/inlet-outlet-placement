"""
Placement Metrics and Reporting System

Provides comprehensive analysis of placement quality according to 
the acceptance criteria defined in placement_plan.md
"""

import math
from typing import Dict, List, Tuple, Set, Any
from collections import defaultdict, Counter
import statistics

from stratified_placement import (
    GridCell, Entity, GridRegion, Stratification, PlacementResult, 
    EntityType, euclidean_distance
)


class PlacementMetrics:
    """Comprehensive metrics calculator for placement quality assessment"""
    
    def __init__(self, 
                 grid_region: GridRegion,
                 stratification: Stratification,
                 entities: List[Entity],
                 cross_entity_radius: float = 1.0):
        self.grid_region = grid_region
        self.stratification = stratification
        self.entities = entities
        self.cross_entity_radius = cross_entity_radius
        self.entity_map = {e.entity_type: e for e in entities}
    
    def analyze_placement(self, result: PlacementResult) -> Dict[str, Any]:
        """
        Comprehensive analysis of placement result
        
        Returns:
            Dictionary containing all metrics and analysis results
        """
        metrics = {
            'quota_satisfaction': self._analyze_quota_satisfaction(result),
            'coverage_metrics': self._analyze_coverage_metrics(result),
            'separation_metrics': self._analyze_separation_metrics(result),
            'distribution_histograms': self._generate_distribution_histograms(result),
            'feasibility_summary': self._generate_feasibility_summary(result),
            'overall_quality_score': 0.0  # Will be calculated at the end
        }
        
        # Calculate overall quality score
        metrics['overall_quality_score'] = self._calculate_quality_score(metrics)
        
        return metrics
    
    def _analyze_quota_satisfaction(self, result: PlacementResult) -> Dict[str, Any]:
        """Analyze how well band quotas were satisfied"""
        quota_analysis = {}
        
        for entity in self.entities:
            entity_type = entity.entity_type
            if entity_type not in result.placements:
                continue
            
            placements = result.placements[entity_type]
            quotas = self.stratification.calculate_quotas(entity)
            
            # Count actual placements per band
            actual_per_band = defaultdict(int)
            for placement in placements:
                for band in self.stratification.bands:
                    if band.contains_cell(placement):
                        actual_per_band[band.index] += 1
                        break
            
            # Calculate satisfaction metrics
            quota_diffs = {}
            total_deviation = 0
            max_deviation = 0
            
            for band_idx, expected in quotas.items():
                actual = actual_per_band[band_idx]
                diff = actual - expected
                quota_diffs[band_idx] = diff
                total_deviation += abs(diff)
                max_deviation = max(max_deviation, abs(diff))
            
            quota_analysis[entity_type.value] = {
                'expected_quotas': quotas,
                'actual_per_band': dict(actual_per_band),
                'quota_differences': quota_diffs,
                'total_deviation': total_deviation,
                'max_deviation': max_deviation,
                'quota_satisfaction_rate': 1.0 - (total_deviation / entity.count) if entity.count > 0 else 1.0
            }
        
        return quota_analysis
    
    def _analyze_coverage_metrics(self, result: PlacementResult) -> Dict[str, Any]:
        """Analyze row/band coverage and distribution uniformity"""
        coverage = {}
        
        # Per-entity coverage
        for entity in self.entities:
            entity_type = entity.entity_type
            if entity_type not in result.placements:
                continue
            
            placements = result.placements[entity_type]
            
            # Band coverage
            bands_occupied = set()
            for placement in placements:
                for band in self.stratification.bands:
                    if band.contains_cell(placement):
                        bands_occupied.add(band.index)
                        break
            
            band_coverage_rate = len(bands_occupied) / len(self.stratification.bands)
            
            # Row coverage within allowed region
            allowed_rows = {cell.y for cell in entity.allowed_region}
            occupied_rows = {placement.y for placement in placements}
            row_coverage_rate = len(occupied_rows) / len(allowed_rows) if allowed_rows else 0
            
            coverage[entity_type.value] = {
                'band_coverage_rate': band_coverage_rate,
                'bands_occupied': sorted(bands_occupied),
                'row_coverage_rate': row_coverage_rate,
                'rows_occupied': sorted(occupied_rows),
                'total_allowed_rows': len(allowed_rows)
            }
        
        # Union coverage
        all_placements = []
        for placements in result.placements.values():
            all_placements.extend(placements)
        
        union_bands = set()
        union_rows = set()
        for placement in all_placements:
            union_rows.add(placement.y)
            for band in self.stratification.bands:
                if band.contains_cell(placement):
                    union_bands.add(band.index)
                    break
        
        coverage['union'] = {
            'band_coverage_rate': len(union_bands) / len(self.stratification.bands),
            'bands_occupied': sorted(union_bands),
            'row_coverage_rate': len(union_rows) / self.grid_region.height,
            'rows_occupied': sorted(union_rows)
        }
        
        return coverage
    
    def _analyze_separation_metrics(self, result: PlacementResult) -> Dict[str, Any]:
        """Analyze minimum separation distances"""
        separation = {}
        
        # Intra-entity separation
        for entity in self.entities:
            entity_type = entity.entity_type
            if entity_type not in result.placements:
                continue
            
            placements = result.placements[entity_type]
            if len(placements) < 2:
                separation[f'{entity_type.value}_intra'] = {
                    'min_distance': float('inf'),
                    'mean_distance': float('inf'),
                    'distances': [],
                    'violations': 0
                }
                continue
            
            distances = []
            violations = 0
            
            for i, p1 in enumerate(placements):
                for p2 in placements[i+1:]:
                    dist = euclidean_distance(p1, p2)
                    distances.append(dist)
                    if dist < entity.intra_radius:
                        violations += 1
            
            separation[f'{entity_type.value}_intra'] = {
                'min_distance': min(distances) if distances else float('inf'),
                'mean_distance': statistics.mean(distances) if distances else float('inf'),
                'distances': distances,
                'violations': violations,
                'required_radius': entity.intra_radius
            }
        
        # Cross-entity separation
        entity_types = list(result.placements.keys())
        for i, type1 in enumerate(entity_types):
            for type2 in entity_types[i+1:]:
                placements1 = result.placements[type1]
                placements2 = result.placements[type2]
                
                distances = []
                violations = 0
                
                for p1 in placements1:
                    for p2 in placements2:
                        dist = euclidean_distance(p1, p2)
                        distances.append(dist)
                        if dist < self.cross_entity_radius:
                            violations += 1
                
                key = f'{type1.value}_{type2.value}_cross'
                separation[key] = {
                    'min_distance': min(distances) if distances else float('inf'),
                    'mean_distance': statistics.mean(distances) if distances else float('inf'),
                    'distances': distances,
                    'violations': violations,
                    'required_radius': self.cross_entity_radius
                }
        
        return separation
    
    def _generate_distribution_histograms(self, result: PlacementResult) -> Dict[str, Any]:
        """Generate 1D histograms for distribution analysis"""
        histograms = {}
        
        # Y-axis (row) histograms for each entity
        for entity in self.entities:
            entity_type = entity.entity_type
            if entity_type not in result.placements:
                continue
            
            placements = result.placements[entity_type]
            y_coords = [p.y for p in placements]
            
            # Create histogram bins
            y_counts = Counter(y_coords)
            all_y_in_region = sorted({cell.y for cell in entity.allowed_region})
            
            histogram = {y: y_counts.get(y, 0) for y in all_y_in_region}
            
            # Calculate uniformity metrics
            counts = list(histogram.values())
            if counts:
                uniformity_score = 1.0 - (statistics.stdev(counts) / statistics.mean(counts)) if statistics.mean(counts) > 0 else 0
            else:
                uniformity_score = 0
            
            histograms[f'{entity_type.value}_y'] = {
                'histogram': histogram,
                'uniformity_score': max(0, uniformity_score),  # Clamp to [0, 1]
                'mean_count': statistics.mean(counts) if counts else 0,
                'std_dev': statistics.stdev(counts) if len(counts) > 1 else 0
            }
        
        # Union histogram
        all_placements = []
        for placements in result.placements.values():
            all_placements.extend(placements)
        
        y_coords = [p.y for p in all_placements]
        y_counts = Counter(y_coords)
        all_y = list(range(1, self.grid_region.height + 1))
        
        union_histogram = {y: y_counts.get(y, 0) for y in all_y}
        counts = list(union_histogram.values())
        
        if counts and sum(counts) > 0:
            uniformity_score = 1.0 - (statistics.stdev(counts) / statistics.mean(counts))
        else:
            uniformity_score = 0
        
        histograms['union_y'] = {
            'histogram': union_histogram,
            'uniformity_score': max(0, uniformity_score),
            'mean_count': statistics.mean(counts) if counts else 0,
            'std_dev': statistics.stdev(counts) if len(counts) > 1 else 0
        }
        
        return histograms
    
    def _generate_feasibility_summary(self, result: PlacementResult) -> Dict[str, Any]:
        """Generate summary of feasibility constraints and relaxations"""
        return {
            'feasibility_notes': result.feasibility_notes,
            'quota_deviations': result.quota_deviations,
            'total_notes': len(result.feasibility_notes),
            'has_violations': len(result.feasibility_notes) > 0
        }
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score (0-1, higher is better)"""
        score_components = []
        
        # Quota satisfaction score (0-1)
        quota_scores = []
        for entity_metrics in metrics['quota_satisfaction'].values():
            quota_scores.append(entity_metrics['quota_satisfaction_rate'])
        
        if quota_scores:
            score_components.append(statistics.mean(quota_scores))
        
        # Coverage score (0-1)
        coverage_scores = []
        for entity_name, coverage in metrics['coverage_metrics'].items():
            if entity_name != 'union':
                coverage_scores.append((coverage['band_coverage_rate'] + coverage['row_coverage_rate']) / 2)
        
        if coverage_scores:
            score_components.append(statistics.mean(coverage_scores))
        
        # Separation score (penalty for violations)
        violation_penalty = 0
        total_pairs = 0
        for sep_name, sep_metrics in metrics['separation_metrics'].items():
            violations = sep_metrics['violations']
            total_distances = len(sep_metrics['distances'])
            if total_distances > 0:
                violation_penalty += violations / total_distances
                total_pairs += 1
        
        if total_pairs > 0:
            separation_score = 1.0 - (violation_penalty / total_pairs)
            score_components.append(max(0, separation_score))
        
        # Distribution uniformity score
        uniformity_scores = []
        for hist_name, hist_data in metrics['distribution_histograms'].items():
            uniformity_scores.append(hist_data['uniformity_score'])
        
        if uniformity_scores:
            score_components.append(statistics.mean(uniformity_scores))
        
        # Overall score is the mean of all components
        return statistics.mean(score_components) if score_components else 0.0


def print_placement_report(metrics: Dict[str, Any], detailed: bool = True) -> str:
    """Generate a human-readable placement quality report"""
    lines = []
    lines.append("=" * 60)
    lines.append("STRATIFIED PLACEMENT QUALITY REPORT")
    lines.append("=" * 60)
    lines.append(f"Overall Quality Score: {metrics['overall_quality_score']:.3f}")
    lines.append("")
    
    # Quota satisfaction
    lines.append("QUOTA SATISFACTION:")
    for entity, quota_data in metrics['quota_satisfaction'].items():
        rate = quota_data['quota_satisfaction_rate']
        lines.append(f"  {entity}: {rate:.3f} (deviation: {quota_data['total_deviation']})")
    lines.append("")
    
    # Coverage metrics
    lines.append("COVERAGE METRICS:")
    for entity, coverage_data in metrics['coverage_metrics'].items():
        band_rate = coverage_data['band_coverage_rate']
        row_rate = coverage_data['row_coverage_rate']
        lines.append(f"  {entity}: Band coverage {band_rate:.3f}, Row coverage {row_rate:.3f}")
    lines.append("")
    
    # Separation violations
    lines.append("SEPARATION VIOLATIONS:")
    for sep_name, sep_data in metrics['separation_metrics'].items():
        violations = sep_data['violations']
        min_dist = sep_data['min_distance']
        required = sep_data['required_radius']
        lines.append(f"  {sep_name}: {violations} violations, min_dist={min_dist:.2f}, required={required:.2f}")
    lines.append("")
    
    # Feasibility notes
    if metrics['feasibility_summary']['feasibility_notes']:
        lines.append("FEASIBILITY NOTES:")
        for note in metrics['feasibility_summary']['feasibility_notes']:
            lines.append(f"  - {note}")
    else:
        lines.append("FEASIBILITY: All constraints satisfied")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)
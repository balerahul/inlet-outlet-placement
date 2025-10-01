# Methodology: Band-Aware Partitioning for Constrained Genetic Algorithms

> **Module**: `ga_ext/band_utils.py`
> **Date**: 2025-10-01
> **Purpose**: Enable genetic algorithm operations while preserving stratified placement constraints

---

## 1. Overview

Band-aware partitioning is a **constraint-preservation technique** that enables genetic algorithms to operate on spatially stratified solutions without violating structural constraints. This methodology addresses a fundamental challenge in applying evolutionary algorithms to problems with hierarchical or spatial organization requirements.

### Core Problem

When applying standard genetic algorithm operators (crossover, mutation) to stratified placement problems, naive approaches can:
- Break vertical stratification constraints (entities moving between forbidden bands)
- Violate quota distributions (uneven allocation across strata)
- Disrupt carefully maintained spatial properties
- Create infeasible solutions requiring extensive repair

### Our Solution

Partition the solution space **before** applying genetic operators, ensuring all operations respect the underlying stratification structure. This transforms a **constrained optimization problem** into a **structured recombination problem** where constraints are preserved by design rather than repaired after violation.

---

## 2. Theoretical Foundation

### 2.1 Stratified Sampling in Optimization

**Stratified sampling** divides a population into homogeneous subgroups (strata) before sampling. This technique, widely used in statistics, ensures:
- **Representation**: Each stratum is proportionally represented
- **Reduced variance**: Sampling within strata reduces overall variance
- **Constraint satisfaction**: Stratum-specific constraints are naturally maintained

In genetic algorithms, applying this concept means:
```
Traditional GA: Operate on entire solution → Repair violations
Stratified GA:  Partition by strata → Operate within strata → Automatic constraint satisfaction
```

### 2.2 Spatial Partitioning for Constraint Handling

Research in constraint-handling genetic algorithms [Constraint Handling in GAs, Journal of Heuristics] shows that **encoding constraints into the representation** is more effective than penalty-based or repair-based approaches.

Key insight: If genetic operators cannot create constraint violations, no repair is needed.

**Band-aware partitioning achieves this by:**
1. Decomposing the solution into constraint-respecting units
2. Ensuring all genetic operations preserve unit boundaries
3. Reconstructing the solution from valid units

### 2.3 Mathematical Framework

Let:
- **G** = rectangular grid of dimensions *w* × *h*
- **B** = set of horizontal bands {B₀, B₁, ..., Bₙ₋₁}
- **E** = set of entity types {e₁, e₂, ..., eₘ}
- **S** = solution (placement) mapping entities to positions

**Stratification Property**: Each band Bᵢ is defined by Y-coordinate range [yₘᵢₙ, yₘₐₓ]

**Partition Function**:
```
π: S × E × B → P(G)
π(s, e, b) = {(x, y) ∈ s[e] | y ∈ [b.yₘᵢₙ, b.yₘₐₓ]}
```

This creates a **decomposition** of the solution:
```
S = ⋃(e∈E, b∈B) π(S, e, b)
```

**Key Property**: Any operation that preserves π maintains stratification.

---

## 3. Methodology Components

### 3.1 Band Partitioning

**Input**: Complete solution S with entity placements
**Output**: Partition map {(entity_type, band_id) → positions}

**Algorithm**:
1. Create horizontal band structure (using existing grid dimensions and band count)
2. For each entity type:
   - For each placement position (x, y):
     - Determine band b where yₘᵢₙ ≤ y ≤ yₘₐₓ
     - Add position to partition[(entity_type, band_id)]

**Time Complexity**: O(|E| × |placements|) - linear scan

**Key Advantage**: Creates a **fine-grained view** of the solution that enables targeted genetic operations.

### 3.2 Quota Calculation

**Problem**: How many entities of each type should be in each band?

**Approach**: Proportional allocation based on available cells

For entity type e and band b:
```
quota(e, b) = round(count(e) × available_cells(e, b) / total_available_cells(e))
```

**Why this works**:
- Respects spatial constraints (some bands may exclude certain entities)
- Maintains feasibility (quotas sum to total entity count)
- Balances distribution (proportional to capacity)

**Adjustment Strategy**: After rounding, distribute residual entities to bands with capacity using round-robin allocation.

### 3.3 Band Boundary Detection

Each band b is characterized by:
- **Index**: Sequential identifier (0, 1, 2, ...)
- **Y-range**: [yₘᵢₙ, yₘₐₓ] calculated from grid height and band count
- **Cells**: Set of all grid positions within Y-range

**Lookup Function**: Given position (x, y), find its band in O(1) or O(log n):
```
band_id = floor((y - 1) / band_height)
```

This enables fast band membership checks during genetic operations.

### 3.4 Free Cell Discovery

For mutation and repair operations, we need to find valid placement locations.

**Band-constrained free cell search**:
```
free_cells(band, occupied, allowed_region) =
    {c ∈ allowed_region | c.band == band ∧ c ∉ occupied}
```

**Applications**:
- Mutation: Find nearby free cells for jittering
- Repair: Relocate conflicting entities
- Quota adjustment: Move surplus entities to underfull bands

---

## 4. Integration with Genetic Operators

### 4.1 Constraint-Preserving Crossover

Traditional crossover might combine:
```
Parent A: Band 0 → [entity at (5,2)]
Parent B: Band 1 → [entity at (5,8)]
Child:    Randomly mix → VIOLATION if entity moves to wrong band
```

With band-aware partitioning:
```
Parent A partitioned: {(vinlet, 0): [(5,2)], (vinlet, 1): [(10,8)]}
Parent B partitioned: {(vinlet, 0): [(3,2)], (vinlet, 1): [(12,9)]}

Crossover per (entity, band) key:
  - (vinlet, 0): Choose A or B → Select [(5,2)] from A
  - (vinlet, 1): Choose A or B → Select [(12,9)] from B

Child: {(vinlet, 0): [(5,2)], (vinlet, 1): [(12,9)]}  ✓ Valid
```

**Property**: All entities remain in their designated bands.

### 4.2 Band-Respecting Mutation

All mutation operators use band information to constrain modifications:

**Within-band swap**: Only swaps entities in the **same** (entity_type, band) partition
**Local jitter**: Only moves entity to free cells in the **same** band
**Micro-reseed**: Re-places entities within their **original** bands

**Result**: Mutations explore the solution space while maintaining stratification.

### 4.3 Quota-Aware Repair

When crossover creates quota imbalances:
```
Band 0: Expected 5 vinlets, Got 7 (surplus: +2)
Band 1: Expected 5 vinlets, Got 3 (deficit: -2)
```

Repair strategy:
1. Identify surplus and deficit bands
2. Move entities from surplus to adjacent deficit bands
3. Prioritize moves that improve separation
4. Log controlled quota "borrow" if perfect balance impossible

---

## 5. Advantages Over Alternative Approaches

### 5.1 Penalty-Based Methods

**Traditional Approach**: Add penalty to fitness for constraint violations
```
fitness = base_fitness - penalty × violation_count
```

**Problems**:
- Difficult to calibrate penalty weights
- Population may contain many infeasible solutions
- Wastes evaluations on invalid solutions

**Band-Aware Advantage**: Constraints satisfied by construction, not penalized.

### 5.2 Repair-After-Violation

**Traditional Approach**: Allow any crossover/mutation, then repair violations

**Problems**:
- Repair may be computationally expensive
- Repair may significantly alter offspring (disrupts parent similarity)
- No guarantee of finding feasible repair

**Band-Aware Advantage**: Minimal repair needed (only for conflicts, not stratification).

### 5.3 Specialized Encoding

**Alternative Approach**: Design problem-specific chromosome encoding that cannot express violations

**Problems**:
- Requires custom encoding/decoding logic
- May not support all problem variants
- Complex to implement and maintain

**Band-Aware Advantage**: Works with natural CSV representation, non-intrusive to existing system.

---

## 6. Performance Characteristics

### 6.1 Computational Complexity

- **Partitioning**: O(n) where n = number of placements
- **Band lookup**: O(1) with direct calculation
- **Free cell search**: O(k) where k = cells in band (cached for efficiency)
- **Quota calculation**: O(b × e) where b = bands, e = entity types

**Overall**: Linear overhead for constraint preservation vs. potentially exponential repair costs.

### 6.2 Memory Usage

Additional storage required:
- Partition map: O(n) - stores same positions with different keys
- Band boundaries: O(b) - constant per band
- Quota targets: O(b × e) - small constant

**Trade-off**: Small memory overhead for guaranteed constraint satisfaction.

### 6.3 Solution Quality

By preserving stratification:
- **Feasibility rate**: 100% for stratification constraints (conflicts still possible)
- **Diversity**: Maintains structured exploration of solution space
- **Convergence**: Faster convergence due to reduced infeasible region search

---

## 7. Limitations and Extensions

### 7.1 Current Limitations

1. **Fixed band structure**: Bands are predetermined and uniform
2. **Horizontal stratification only**: Y-axis stratification (could extend to X)
3. **Quota flexibility**: Limited tolerance for quota deviations

### 7.2 Possible Extensions

**Dynamic band adjustment**: Allow GA to evolve band boundaries
**Multi-dimensional stratification**: Support both X and Y stratification
**Soft quotas**: Fuzzy quota targets with preference ranges
**Hierarchical bands**: Nested band structures for multi-scale constraints

---

## 8. Connection to Existing System

### 8.1 Non-Invasive Integration

The band-aware partitioning module **imports** but **does not modify** the existing stratified placement engine. It uses:
- `GridRegion`: For grid dimensions and cell generation
- `Stratification`: For band boundary calculations
- `Entity`: For quota calculation logic

**Design principle**: Leverage existing validated code rather than reimplementing.

### 8.2 Compatibility

Works with any solution produced by the existing placement engine because:
- Uses same grid coordinate system
- Respects same band definitions
- Maintains same entity type semantics

**Result**: GA can evolve any existing solution without breaking constraints.

---

## 9. Practical Implications

### 9.1 For External Evaluators

External fitness evaluators receive solutions that:
- Always satisfy stratification constraints
- May have minor quota deviations (logged in lineage)
- Maintain spatial feasibility (in allowed regions)

**Benefit**: Can focus evaluation on quality metrics rather than constraint checking.

### 9.2 For Multi-Generation Evolution

Stratification preservation across generations enables:
- **Cumulative improvement**: Building on valid solutions
- **Stable convergence**: No oscillation between feasible/infeasible regions
- **Predictable behavior**: Constraint violations don't compound over time

---

## 10. Summary

Band-aware partitioning transforms genetic algorithm operations on stratified placement problems from a **constrained optimization challenge** into a **structured recombination task**.

**Key Innovation**: Decompose solutions into constraint-respecting units before applying genetic operators, ensuring structural properties are preserved by design rather than enforced through repair.

**Core Trade-off**: Small computational overhead for partitioning vs. large savings in repair and guaranteed constraint satisfaction.

**Result**: Genetic algorithms that respect domain constraints while effectively exploring the solution space.

---

## References

- Constraint Handling in Genetic Algorithms: The Set Partitioning Problem. *Journal of Heuristics*, 1998.
- A Grouping Genetic Algorithm for Joint Stratification. *arXiv:1709.03076*, 2017.
- Stratified Sampling for Even Workload Partitioning. *IEEE Conference Publication*, 2015.
- Existing stratified placement system documentation: `placement_plan.md`

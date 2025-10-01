# Methodology: Crossover Operators for Spatial Placement Problems

> **Module**: `ga_ext/crossover.py`
> **Date**: 2025-10-01
> **Purpose**: Enable genetic recombination of placement solutions while preserving spatial and structural constraints

---

## 1. Overview

**Crossover** (also called recombination) is the primary genetic operator that combines genetic material from two parent solutions to create offspring. In the context of spatial placement problems, crossover must balance two competing objectives:
1. **Exploration**: Combine diverse parent features to explore new solution regions
2. **Constraint preservation**: Maintain structural properties (stratification, quotas, spatial feasibility)

This document describes three crossover strategies tailored to stratified placement problems, each offering different trade-offs between exploration and structure preservation.

---

## 2. Theoretical Foundation

### 2.1 Classical Crossover in Genetic Algorithms

Traditional genetic algorithms use crossover operators designed for binary or permutation encodings:

**Single-Point Crossover**: Split chromosomes at one position, swap tails
```
Parent A: [1 1 0 | 1 0 1 0]
Parent B: [0 0 1 | 0 1 1 1]
          --------+--------
Child:    [1 1 0 | 0 1 1 1]
```

**Multi-Point Crossover**: Split at multiple positions, swap alternating segments
```
Parent A: [1 1 | 0 1 0 | 1 0]
Parent B: [0 0 | 1 0 1 | 1 1]
          -----+-------+----
Child:    [1 1 | 1 0 1 | 1 0]
```

**Uniform Crossover**: For each gene, randomly select from either parent
```
Parent A: [1 1 0 1 0 1 0]
Parent B: [0 0 1 0 1 1 1]
Mask:     [A B A B A A B]
Child:    [1 0 0 0 0 1 1]
```

### 2.2 Challenges for Spatial Placement

Standard crossover operators face problems with spatial placements:

1. **Non-linear structure**: Positions aren't sequential (2D, not 1D)
2. **Set-based representation**: Each entity type has a *set* of positions (no natural ordering)
3. **Complex constraints**: Stratification, quotas, separation requirements
4. **Conflict generation**: Combining parents may place multiple entities at same location

**Key Insight**: We need *spatially-aware* crossover that respects the 2D grid structure and maintains feasibility.

### 2.3 Building Block Hypothesis

The **building block hypothesis** [Holland, 1975] states that GAs work by identifying, preserving, and recombining "building blocks" - short, low-order, highly-fit schemata.

For spatial placements, natural building blocks are:
- **Band-wise**: Entities within same horizontal band
- **Block-wise**: Entities within same spatial region
- **Entity-wise**: All placements of same entity type

**Design principle**: Crossover should respect these natural boundaries to preserve high-quality sub-structures.

---

## 3. Crossover Strategy 1: Band-Wise Crossover

### 3.1 Motivation

In stratified placement, **horizontal bands are fundamental structural units**. Each band has:
- Independent quota constraints
- Distinct entity distributions
- Separate optimization objectives (within-band separation)

Band-wise crossover treats each (entity_type, band) combination as an atomic unit that should be inherited intact from one parent.

### 3.2 Algorithm

**Input**: Two parent solutions A and B
**Output**: One child solution C and crossover mask

**Procedure**:
```
1. Partition both parents by (entity_type, band_id):
   A_partition = {(vinlet, 0): [...], (vinlet, 1): [...], ...}
   B_partition = {(vinlet, 0): [...], (vinlet, 1): [...], ...}

2. For each (entity_type, band_id) key:
   - Flip coin (or use crossover_rate bias)
   - If heads: inherit from parent A
   - If tails: inherit from parent B
   - Record choice in crossover_mask

3. Combine all inherited units into child
   C_placements[entity_type] = concat all bands for that entity

4. Return child (may have conflicts → repair)
```

**Crossover Mask Example**:
```
{
  ('vinlet', 0): 'A',    # Inherited all band-0 vinlets from parent A
  ('vinlet', 1): 'B',    # Inherited all band-1 vinlets from parent B
  ('acinlet', 0): 'A',
  ('acinlet', 1): 'A'
}
```

### 3.3 Properties

**Advantages**:
- ✅ Preserves band structure completely
- ✅ Maintains quota distributions per band
- ✅ High-quality band configurations inherited intact
- ✅ Minimal constraint violations (only potential conflicts)

**Disadvantages**:
- ❌ Coarse-grained (large units of inheritance)
- ❌ May inherit correlated bands together (less mixing)
- ❌ Limited exploration if parents similar within bands

**Best for**: Problems where band-level optimization is critical, stratification must be strictly preserved.

### 3.4 Theoretical Analysis

Let:
- n = number of (entity_type, band) combinations
- Each combination can be inherited from parent A or B

**Search space**: 2^n possible children from each parent pair

**Expected mixing**: With uniform random selection, child inherits ~50% from each parent

**Constraint preservation**:
- Stratification: 100% (bands never mixed)
- Quotas: 100% per band (inherited intact)
- Conflicts: Possible at band boundaries

---

## 4. Crossover Strategy 2: Block-2D Crossover

### 4.1 Motivation

Sometimes optimal patterns span multiple bands (vertical structures) or are localized spatially (corners, edges). Band-wise crossover cannot capture these patterns.

**Block-2D crossover** divides the grid into rectangular blocks and inherits each block independently, enabling:
- Spatial locality preservation
- Multi-band pattern inheritance
- Finer-grained recombination than entity-wise

### 4.2 Algorithm

**Input**: Parents A and B, block configuration (blocks_x, blocks_y)
**Output**: Child C and block mask

**Procedure**:
```
1. Divide grid into blocks_x × blocks_y rectangles:
   block_width = grid_width / blocks_x
   block_height = grid_height / blocks_y

2. For each block (bx, by):
   - Randomly assign to parent A or B
   - Record in block_mask[(bx, by)]

3. For each entity in each parent:
   - Determine which block the entity belongs to
   - If block assigned to this parent, include entity in child
   - Otherwise, skip entity

4. Combine all selected entities into child
```

**Block Assignment Example** (2×2 grid):
```
Grid divided into 4 blocks:

┌─────────┬─────────┐
│ Block   │ Block   │
│ (0,0)→A │ (1,0)→B │
├─────────┼─────────┤
│ Block   │ Block   │
│ (0,1)→B │ (1,1)→A │
└─────────┴─────────┘

Entities in blocks from A: Keep
Entities in blocks from B: Keep
```

### 4.3 Properties

**Advantages**:
- ✅ Preserves spatial locality (nearby entities stay together)
- ✅ Can capture multi-band patterns
- ✅ Finer-grained than entity-wise, coarser than uniform
- ✅ Configurable granularity (adjust block count)

**Disadvantages**:
- ❌ May break band structure (entities cross band boundaries)
- ❌ Can create quota imbalances (blocks have uneven entity counts)
- ❌ More conflicts than band-wise (more mixing)

**Best for**: Problems where spatial patterns are important, stratification is flexible, diversity is prioritized over constraint satisfaction.

### 4.4 Theoretical Analysis

**Search space**: 2^(blocks_x × blocks_y) possible children

**Block size trade-off**:
- Small blocks (many): More mixing, more exploration, more conflicts
- Large blocks (few): Less mixing, more constraint preservation

**Optimal block size**: Depends on problem scale and parent diversity
- Typical: 3×3 to 5×5 for 20×10 grids
- Rule of thumb: ~10-20% of grid dimension

---

## 5. Crossover Strategy 3: Entity-Wise Crossover

### 5.1 Motivation

The **coarsest-grained** crossover: inherit *all* placements of each entity type from one parent or the other.

Use cases:
- Parent solutions have very different entity distribution philosophies
- Want to test combinations of different entity strategies
- Maximize exploration (most disruptive crossover)

### 5.2 Algorithm

**Input**: Parents A and B
**Output**: Child C and entity mask

**Procedure**:
```
1. List all entity types: [vinlet, voutlet, acinlet, acoutlet]

2. For each entity_type:
   - Randomly select parent A or B
   - Inherit ALL placements of this entity type from selected parent
   - Record choice in entity_mask[entity_type]

3. Combine selected entity sets into child
```

**Entity Mask Example**:
```
{
  'vinlet': 'A',     # All vinlets from parent A
  'voutlet': 'B',    # All voutlets from parent B
  'acinlet': 'A',
  'acoutlet': 'B'
}
```

### 5.3 Properties

**Advantages**:
- ✅ Simple to implement and understand
- ✅ Preserves intra-entity optimization (separation within entity type)
- ✅ Enables testing entity-strategy combinations
- ✅ Fast (no per-position processing)

**Disadvantages**:
- ❌ Very coarse-grained (limited exploration)
- ❌ High chance of quota violations (entity distributions differ)
- ❌ May not respect cross-entity relationships
- ❌ Requires extensive repair

**Best for**: Initial exploration phases, testing radically different approaches, problems where entity types are independent.

### 5.4 Theoretical Analysis

**Search space**: 2^(number of entity types) possible children
- Typical: 2^4 = 16 children per parent pair

**Expected diversity**:
- If parents very different: High diversity
- If parents similar: Low diversity (bottleneck)

**Constraint preservation**: Minimal - requires most repair

---

## 6. Comparison and Selection Criteria

| Criterion | Band-Wise | Block-2D | Entity-Wise |
|-----------|-----------|----------|-------------|
| **Granularity** | Medium (per band) | Fine (per block) | Coarse (per entity) |
| **Stratification Preservation** | ✅ Perfect | ⚠️ Partial | ❌ None |
| **Quota Preservation** | ✅ High | ⚠️ Medium | ❌ Low |
| **Conflict Rate** | Low | Medium | High |
| **Exploration Power** | Medium | High | Very High |
| **Computation Cost** | Medium | Medium | Low |
| **Repair Required** | Minimal | Moderate | Extensive |
| **Best Parent Similarity** | Medium | Low | High |

### Selection Guidelines

**Use Band-Wise when**:
- Stratification is mandatory constraint
- Parents have good band-level optimization
- Quota preservation critical
- Prefer safety over exploration

**Use Block-2D when**:
- Spatial patterns more important than bands
- Need high diversity in population
- Can tolerate repair costs
- Parents have distinct spatial strategies

**Use Entity-Wise when**:
- Early exploration phase
- Testing entity strategy combinations
- Entity types relatively independent
- Repair mechanism is robust

---

## 7. Conflict Detection and Handling

### 7.1 Why Conflicts Occur

Crossover can create **position conflicts**: multiple entities at same (x, y) location.

**Example**:
```
Parent A: vinlet at (5,5), acinlet at (7,5)
Parent B: vinlet at (5,5), acinlet at (8,5)

Child (inherits different bands/blocks):
  - Vinlet from A at (5,5)
  - Acinlet from B at (5,5)  ← CONFLICT!
```

### 7.2 Conflict Detection Algorithm

**Procedure**:
```
1. Create position counter: position_count = {}
2. For each entity_type in child:
   For each position (x,y):
     position_count[(x,y)] += 1
3. conflicts = [pos for pos, count in position_count if count > 1]
```

**Time Complexity**: O(n) where n = total placements

### 7.3 Conflict Resolution Strategies

Conflicts are resolved by **repair operators** (separate module), but crossover can minimize conflicts:

**Design strategies**:
1. **Prefer strategies with lower conflict rates** (band-wise > block-2D > entity-wise)
2. **Log conflicts for external evaluator** (may penalize high-conflict children)
3. **Adaptive strategy switching** (use safer crossover if conflict rate too high)

---

## 8. Crossover Rate and Control

### 8.1 Crossover Probability

Not all parent pairs produce children via crossover. Alternative: **clone** a parent.

**Crossover rate** (ρc): Probability of applying crossover vs. cloning
- Typical values: 0.6 - 0.9
- High rate: More exploration, more diversity
- Low rate: More exploitation, preserve good solutions

**Implementation**:
```
if random() < crossover_rate:
    child = crossover(parent_a, parent_b)
else:
    child = clone(select_best(parent_a, parent_b))
```

### 8.2 Within-Crossover Bias

For band-wise and block-2D crossover, each unit independently selects parent A or B.

**Bias parameter** (α): Probability of selecting parent A
- α = 0.5: Uniform (unbiased)
- α > 0.5: Favor parent A (e.g., if A has better fitness)
- α < 0.5: Favor parent B

**Application**: If external evaluator ranks parents, can bias toward better parent.

### 8.3 Adaptive Crossover

**Idea**: Adjust crossover strategy based on population diversity or convergence state.

**Strategy switching rules**:
```
if population_diversity < threshold_low:
    use block_2d_crossover  # Increase exploration
elif conflict_rate > threshold_high:
    use bandwise_crossover  # Reduce conflicts
else:
    use configured_strategy # Normal operation
```

---

## 9. Integration with External Fitness Evaluation

### 9.1 Lineage Tracking

Each crossover operation records:
- Parent IDs
- Crossover strategy used
- Crossover mask (which units from which parent)
- Conflict count

**Purpose**: External evaluator can analyze:
- Which parent combinations produce best children
- Which crossover strategies most effective
- Which spatial patterns worth preserving

### 9.2 Conflict Reporting

Conflicts are logged but **not resolved** by crossover operator. Instead:
1. Child marked as "provisional" (needs repair)
2. Conflicts logged in metadata
3. Repair module resolves conflicts before evaluation

**Separation of concerns**:
- Crossover: Focus on recombination
- Repair: Focus on feasibility
- External evaluator: Focus on quality

---

## 10. Performance Characteristics

### 10.1 Computational Complexity

**Band-Wise Crossover**:
- Partition parents: O(n) where n = total placements
- Combine units: O(n)
- Total: **O(n) linear**

**Block-2D Crossover**:
- Block assignment: O(blocks_x × blocks_y) = constant
- Entity assignment: O(n)
- Total: **O(n) linear**

**Entity-Wise Crossover**:
- Entity selection: O(e) where e = entity types = constant
- Copy placements: O(n)
- Total: **O(n) linear**

**Conclusion**: All strategies have linear time complexity - efficient for large problems.

### 10.2 Memory Usage

Additional storage:
- Crossover mask: O(units) where units = bands, blocks, or entities
- Child placements: O(n) (same as parents)
- Conflict list: O(c) where c = conflicts (typically small)

**Memory efficient**: No significant overhead beyond parent storage.

---

## 11. Relationship to Classical Crossover

### 11.1 Band-Wise ≈ Multi-Point Crossover

If we linearize positions by (entity_type, band_id), band-wise crossover becomes multi-point crossover with cuts at band boundaries.

**Difference**: Band-wise respects 2D structure; multi-point is 1D.

### 11.2 Block-2D ≈ Uniform Crossover

Each spatial block independently selects parent, similar to uniform crossover selecting each gene independently.

**Difference**: Block-2D operates on spatial regions; uniform on individual genes.

### 11.3 Entity-Wise ≈ Single-Point Crossover

Inheriting entire entity types is like single-point crossover with one cut point separating entity types.

**Difference**: Entity-wise has semantic meaning (entity types); single-point is arbitrary split.

---

## 12. Advanced Topics

### 12.1 Multi-Parent Crossover

Extend to more than 2 parents:
```
Child inherits each unit from one of K parents
Requires selecting best K parents via tournament
```

**Benefit**: Can combine features from multiple high-quality solutions.

### 12.2 Problem-Specific Crossover

For specific optimization objectives:
- **Separation-preserving**: Only inherit bands with good separation
- **Coverage-optimizing**: Prefer blocks with even distribution
- **Quota-balanced**: Adjust inheritance to minimize quota deviations

### 12.3 Learning Crossover Strategies

Use machine learning to learn which crossover strategy works best:
- Track success rate of each strategy
- Adaptively select based on past performance
- Population-based strategy distribution

---

## 13. Summary

Crossover operators for spatial placement problems must balance:
1. **Structural preservation** (constraints)
2. **Exploration power** (diversity)
3. **Computational efficiency** (speed)

**Key Innovations**:
- **Band-wise**: Respects stratification, preserves quotas, minimal conflicts
- **Block-2D**: Spatial locality, multi-band patterns, high diversity
- **Entity-wise**: Maximum exploration, tests strategy combinations

**Design Philosophy**: Choose crossover granularity based on problem constraints and optimization phase.

**Best Practice**: Start with band-wise (safe), switch to block-2D if stuck (exploration), use entity-wise for initial population diversity.

---

## References

- Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*. University of Michigan Press.
- Crossover in Genetic Algorithms. *GeeksforGeeks*, 2024.
- Uniform Crossover in Genetic Algorithms. *ResearchGate*, 1989.
- Genetic Algorithm. *Cornell University Computational Optimization*, 2024.
- Crossover Operators in GA. *Geek Culture*, Medium, 2021.

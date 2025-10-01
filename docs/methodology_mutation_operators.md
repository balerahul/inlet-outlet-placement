# Methodology: Mutation Operators for Spatial Placement Optimization

> **Module**: `ga_ext/mutation.py`
> **Date**: 2025-10-01
> **Purpose**: Enable controlled exploration of solution space while preserving spatial and stratification constraints

---

## 1. Overview

**Mutation** is a genetic operator that introduces random variations into individual solutions, serving as the primary mechanism for:
1. **Exploration**: Discovering new regions of the solution space
2. **Diversity maintenance**: Preventing premature convergence
3. **Local optimization**: Fine-tuning solutions through small adjustments

In spatial placement problems, mutation must navigate the tension between **exploration** (trying new configurations) and **constraint preservation** (maintaining stratification, quotas, and feasibility).

This document describes three band-respecting mutation operators designed specifically for stratified placement problems.

---

## 2. Theoretical Foundation

### 2.1 Role of Mutation in Genetic Algorithms

Classical genetic algorithms use mutation as a **background operator** with two key functions:

**1. Genetic Diversity Maintenance**
- Prevents population from converging to local optima
- Introduces alleles lost during selection pressure
- Maintains exploration capability throughout evolution

**2. Local Search Enhancement**
- Makes small adjustments to promising solutions
- Explores neighborhood of current best solutions
- Acts as hill-climbing within GA framework

**Balance Principle**: Mutation rate must be:
- **High enough** to maintain diversity and escape local optima
- **Low enough** to not disrupt good solutions (preserve building blocks)

**Typical mutation rates**: 0.01 - 0.3 (1% - 30% of individuals mutated per generation)

### 2.2 Classical Mutation Operators

**Bit-Flip Mutation** (for binary encoding):
```
Before: [1 0 1 1 0 1 0]
Flip:   [1 0 1 0 0 1 0]  (4th bit flipped)
```

**Swap Mutation** (for permutation encoding):
```
Before: [3 2 5 1 4]
Swap:   [3 4 5 1 2]  (positions 2 and 5 swapped)
```

**Scramble Mutation** (for permutation encoding):
```
Before: [1 2 3 4 5 6 7]
Select: [  2 3 4 5    ] (subset)
Scramble: [1 5 4 2 3 6 7] (subset randomized)
```

**Inversion Mutation** (for permutation encoding):
```
Before: [1 2 3 4 5 6 7]
Select: [  2 3 4 5    ] (subset)
Invert: [1 5 4 3 2 6 7] (subset reversed)
```

### 2.3 Challenges for Spatial Placement

Standard mutation operators fail for spatial placements because:

1. **2D structure**: Positions are (x, y) coordinates, not linear sequences
2. **Stratification constraints**: Entities must stay in designated bands
3. **Quota requirements**: Entity counts per band must be maintained
4. **Spatial feasibility**: Mutations must respect allowed regions and avoid overlaps
5. **Separation objectives**: Mutations should improve (or maintain) entity spacing

**Key Innovation Required**: Design mutation operators that work *within* the stratified structure, treating bands as independent mutation contexts.

### 2.4 Band-Respecting Mutation Philosophy

**Core Principle**: Mutations operate within band boundaries, not across them.

**Analogy**: Think of each (entity_type, band) combination as a separate "sub-chromosome" that can be mutated independently without affecting other bands.

**Benefits**:
- Stratification preserved automatically (no cross-band moves)
- Quotas maintained (no entities added/removed from bands)
- Local optimization (improve band-level configurations)
- Constraint satisfaction (mutations inherently feasible)

---

## 3. Mutation Operator 1: Within-Band Swap

### 3.1 Motivation

The **simplest** band-respecting mutation: swap positions of two entities of the same type within the same band.

**Use case**: Explore alternative spatial arrangements without changing band structure or quotas.

**Biological analogy**: Rearranging components within a cell without changing cell boundaries.

### 3.2 Algorithm

**Input**: Individual, entity type to mutate
**Output**: Mutated individual, operation log

**Procedure**:
```
1. Partition individual by (entity_type, band_id)

2. Select random entity_type to mutate

3. Find bands containing this entity_type:
   bands_with_entity = [band for (entity, band) in partition if entity == entity_type]

4. If no bands or band has < 2 entities:
   Return unchanged (cannot swap)

5. Select random band from bands_with_entity

6. Select two random positions in this band:
   pos1, pos2 = random_sample(positions_in_band, size=2)

7. Swap positions:
   placements[entity_type][idx1] ← pos2
   placements[entity_type][idx2] ← pos1

8. Return mutated individual
```

**Example**:
```
Band 0, vinlet placements: [(5,2), (10,3), (15,4)]

Swap operation:
  Select: (5,2) and (15,4)
  Result: [(15,4), (10,3), (5,2)]
```

### 3.3 Properties

**Advantages**:
- ✅ Simplest implementation
- ✅ Perfect constraint preservation (no violations)
- ✅ Fast execution (O(1) swap operation)
- ✅ Reversible (swap back undoes mutation)
- ✅ Safe (always produces valid solution)

**Disadvantages**:
- ❌ Limited exploration (only 2 positions change)
- ❌ May not improve separation (random swap)
- ❌ Small search neighborhood

**Best for**:
- Fine-tuning near-optimal solutions
- Maintaining feasibility with minimal disruption
- Early generations (gentle exploration)

### 3.4 Enhancement: Distance-Improving Swap

**Modification**: Only accept swap if it improves minimum separation distance.

**Algorithm extension**:
```
6b. Calculate current min distance for these two entities
7b. Calculate min distance if swapped
8b. If swapped_distance > current_distance:
      Accept swap
    Else:
      Reject (keep original)
```

**Benefit**: Combines mutation with local hill-climbing.

**Trade-off**: Reduces exploration (rejects many random swaps) but improves quality.

---

## 4. Mutation Operator 2: Band-Local Jitter

### 4.1 Motivation

**Swap** is too conservative - it only exchanges existing positions. **Jitter** explores new positions by moving an entity to a nearby free cell within the same band.

**Use case**: Local optimization around promising configurations.

**Biological analogy**: Molecule vibration within a confined region.

### 4.2 Algorithm

**Input**: Individual, entity type, jitter radius
**Output**: Mutated individual, operation log

**Procedure**:
```
1. Select random entity_type to mutate

2. Select random placement of this entity:
   current_pos = random_choice(placements[entity_type])

3. Determine band for current_pos:
   band_id = get_band(current_pos.y)

4. Get occupied positions (excluding current_pos):
   occupied = all_positions - {current_pos}

5. Get free cells in same band:
   free_cells = {c in band | c not in occupied and c in allowed_region}

6. Filter to nearby cells (within jitter radius):
   nearby_free = {c in free_cells |
                  |c.x - current_pos.x| ≤ jitter_radius and
                  |c.y - current_pos.y| ≤ jitter_radius}

7. If nearby_free is empty:
   Try any free cell in band (fallback)

8. Select random nearby free cell:
   new_pos = random_choice(nearby_free)

9. Update placement:
   placements[entity_type][idx] ← new_pos

10. Return mutated individual
```

**Example**:
```
Current position: (10, 5)
Jitter radius: 3

Candidate cells:
  (7,5), (8,5), (9,5), (11,5), (12,5), (13,5)  (x-direction)
  (10,3), (10,4), (10,6), (10,7)              (y-direction within band)

Select: (12, 6) (random from nearby free cells)
```

### 4.3 Properties

**Advantages**:
- ✅ Explores new positions (not limited to existing placements)
- ✅ Controlled exploration (radius limits disruption)
- ✅ Respects spatial locality (nearby moves)
- ✅ Maintains constraints (band boundaries, allowed regions)

**Disadvantages**:
- ❌ May fail if no free cells (dense configurations)
- ❌ Computationally more expensive than swap (need to find free cells)
- ❌ Radius parameter requires tuning

**Best for**:
- Mid-stage optimization (after initial exploration)
- Improving entity separation
- Dense grids with limited free space

### 4.4 Jitter Radius Selection

**Small radius (1-2 cells)**:
- Conservative exploration
- Fine-tuning existing configurations
- High success rate (more nearby free cells)

**Medium radius (3-5 cells)**:
- Balanced exploration/exploitation
- Good default choice
- Explores local neighborhoods

**Large radius (>5 cells)**:
- Aggressive exploration
- Approaches random placement
- May break local patterns

**Adaptive strategy**:
```
if min_separation < target:
    radius = large  # Need significant changes
elif min_separation near target:
    radius = medium # Fine-tuning
else:
    radius = small  # Maintain good configuration
```

---

## 5. Mutation Operator 3: Micro-Reseed

### 5.1 Motivation

**Swap** and **jitter** make incremental changes. Sometimes, more disruptive mutations are needed to:
- Escape local optima
- Explore radically different configurations
- Recover from poor initial placements

**Micro-reseed** removes a small fraction of entities and re-places them randomly within their original bands, effectively "restarting" part of the solution.

### 5.2 Algorithm

**Input**: Individual, entity type, reseed fraction (e.g., 0.1 = 10%)
**Output**: Mutated individual, operation log

**Procedure**:
```
1. Select random entity_type to mutate

2. Calculate number to reseed:
   num_to_reseed = max(1, floor(count(entity_type) × fraction))

3. Select random placements to remove:
   indices_to_reseed = random_sample(range(count), num_to_reseed)

4. For each selected placement:
   a. Record its current position and band
   b. Remove from occupied positions
   c. Get free cells in same band
   d. Select random free cell
   e. Place entity at new position
   f. Add to occupied positions

5. Update placements array

6. Return mutated individual
```

**Example**:
```
Entity: vinlet (10 total)
Fraction: 0.2 (20%)
Reseed count: 2

Selected for reseeding: vinlet at (5,2) and (15,8)
Bands: 0 and 1

New random positions in same bands:
  (5,2) → (8,3)   (band 0)
  (15,8) → (12,9) (band 1)
```

### 5.3 Properties

**Advantages**:
- ✅ High exploration power (significant changes)
- ✅ Maintains overall structure (most entities unchanged)
- ✅ Escapes local optima (breaks poor local patterns)
- ✅ Preserves constraints (reseeding within bands)

**Disadvantages**:
- ❌ Disruptive (may destroy good local patterns)
- ❌ Computationally expensive (multiple position searches)
- ❌ High variance in outcome quality

**Best for**:
- Population diversity maintenance
- Escaping plateaus in optimization
- Late-generation exploration bursts

### 5.4 Reseed Fraction Tuning

**Very small (1-5%)**:
- Minimal disruption
- Essentially like multiple jitters
- Safe exploration

**Small (5-15%)** [**Recommended default**]:
- Balanced exploration
- Significant but controlled changes
- Good for most applications

**Large (15-30%)**:
- Aggressive exploration
- Near-random replacement
- Risk destroying good solutions

**Adaptive strategy**:
```
if generations_without_improvement > patience:
    fraction = large   # Need dramatic change
elif population_diversity < threshold:
    fraction = medium  # Boost diversity
else:
    fraction = small   # Normal operation
```

---

## 6. Mutation Orchestration

### 6.1 Multi-Operator Strategy

Rather than using a single mutation operator, the **mutation orchestrator** probabilistically applies multiple operators, potentially multiple times per individual.

**Advantages**:
- Combines exploration power of different operators
- Adapts to different problem regions
- Increases mutation diversity

### 6.2 Orchestration Algorithm

**Input**: Individual, configuration
**Output**: Mutated individual, operation log

**Configuration**:
```yaml
mutation_rate: 0.3  # 30% of individuals mutated

mutation:
  operators:
    within_band_swap: 0.4    # 40% probability
    band_local_jitter: 0.4   # 40% probability
    micro_reseed: 0.2        # 20% probability
  max_ops_per_individual: 3  # Apply 1-3 operations
```

**Procedure**:
```
1. Decide whether to mutate:
   if random() > mutation_rate:
     return unchanged

2. Decide number of operations:
   num_ops = random_integer(1, max_ops_per_individual)

3. For each operation:
   a. Select operator probabilistically:
      r = random()
      if r < 0.4: use within_band_swap
      elif r < 0.8: use band_local_jitter
      else: use micro_reseed

   b. Select random entity_type

   c. Apply selected operator

   d. Log operation

4. Return mutated individual with full log
```

**Example execution**:
```
Individual: parent_001
Mutation decision: Yes (random = 0.15 < 0.3)
Operations: 2 (random selection from [1,2,3])

Operation 1:
  - Operator selected: band_local_jitter (random = 0.65)
  - Entity: vinlet
  - Result: Moved (10,5) → (12,6)

Operation 2:
  - Operator selected: within_band_swap (random = 0.22)
  - Entity: acinlet
  - Result: Swapped (5,7) ↔ (8,8)

Final log: ["band_local_jitter(vinlet, band=1): (10,5)→(12,6)",
            "within_band_swap(acinlet, band=1): (5,7)↔(8,8)"]
```

### 6.3 Operator Probability Tuning

**Conservative mix** (favor swap):
```
within_band_swap: 0.6
band_local_jitter: 0.3
micro_reseed: 0.1
```
Use when: Solutions are high-quality, need fine-tuning

**Balanced mix** (recommended):
```
within_band_swap: 0.4
band_local_jitter: 0.4
micro_reseed: 0.2
```
Use when: Standard optimization, balanced exploration

**Aggressive mix** (favor reseed):
```
within_band_swap: 0.2
band_local_jitter: 0.3
micro_reseed: 0.5
```
Use when: Stuck in local optima, need diversity boost

---

## 7. Constraint Preservation Guarantees

### 7.1 Stratification Invariants

**Theorem**: All three mutation operators preserve stratification.

**Proof**:
- **Within-band swap**: Swaps occur only within same band → no cross-band moves
- **Band-local jitter**: Target cells restricted to same band → no cross-band moves
- **Micro-reseed**: Reseeding occurs within original band → no cross-band moves

**Consequence**: Mutated solutions always satisfy band constraints.

### 7.2 Quota Preservation

**Theorem**: All three mutation operators preserve entity counts per (entity_type, band).

**Proof**:
- **Within-band swap**: Rearranges existing entities → count unchanged
- **Band-local jitter**: Moves entity within band → count per band unchanged
- **Micro-reseed**: Replaces entity within same band → count per band unchanged

**Consequence**: Mutated solutions maintain quota distributions.

### 7.3 Feasibility Maintenance

**Allowed region constraint**:
- All operators check `cell in allowed_region` before placing
- Mutations rejected if no valid cells available

**Overlap constraint**:
- Jitter and reseed check `cell not in occupied` before placing
- Prevents creating position conflicts

**Result**: Mutations produce feasible solutions (no stratification violations, no overlaps).

---

## 8. Performance Characteristics

### 8.1 Computational Complexity

**Within-band swap**:
- Partition: O(n)
- Select positions: O(1)
- Swap: O(1)
- **Total: O(n) per mutation**

**Band-local jitter**:
- Find free cells: O(b) where b = cells in band
- Select nearby: O(k) where k = cells in radius
- **Total: O(n + b) per mutation**

**Micro-reseed**:
- Select entities: O(r) where r = reseed count
- Find free cells: O(b) per entity
- **Total: O(n + r×b) per mutation**

**Orchestrator**:
- Apply k operations: k × (per-operation cost)
- Typical k = 1-3
- **Total: O(k×n) per individual**

**Conclusion**: All operators have linear or near-linear complexity - efficient for large problems.

### 8.2 Memory Usage

- Partition map: O(n) temporary storage
- Free cell set: O(b) per band
- Operation log: O(k) strings

**Memory efficient**: Dominated by solution representation itself.

### 8.3 Success Rate

**Metric**: Percentage of mutation attempts that succeed (find valid new position).

**Typical success rates**:
- Within-band swap: ~99% (only fails if < 2 entities in band)
- Band-local jitter: 60-90% (depends on density and radius)
- Micro-reseed: 70-95% (depends on available free cells)

**Failure handling**: Log failure, return unchanged individual.

---

## 9. Mutation Rate Dynamics

### 9.1 Static Mutation Rate

**Fixed rate throughout evolution**:
```
mutation_rate = 0.3  # 30% of population mutated every generation
```

**Advantages**:
- Simple to implement
- Predictable behavior
- Standard in literature

**Disadvantages**:
- Not adaptive to search progress
- Same rate for early exploration and late exploitation

### 9.2 Adaptive Mutation Rate

**Adjust rate based on population state**:

**Strategy 1: Diversity-based**
```
if population_diversity < threshold_low:
    mutation_rate = high  # Boost diversity
elif population_diversity > threshold_high:
    mutation_rate = low   # Preserve good solutions
```

**Strategy 2: Fitness-based**
```
if best_fitness_improvement < epsilon:
    mutation_rate += delta  # Increase exploration
else:
    mutation_rate = base_rate  # Normal operation
```

**Strategy 3: Generation-based**
```
mutation_rate = base_rate × (1 - generation / max_generations)^k

Early: high rate (exploration)
Late: low rate (exploitation)
```

### 9.3 Recommended Settings

**Default configuration** (works for most problems):
```
mutation_rate: 0.3
operators:
  within_band_swap: 0.4
  band_local_jitter: 0.4
  micro_reseed: 0.2
max_ops_per_individual: 2
jitter_radius: 3
micro_reseed_fraction: 0.1
```

**Early-stage emphasis** (first 25% of generations):
```
mutation_rate: 0.5
micro_reseed_fraction: 0.2  # More aggressive
```

**Late-stage emphasis** (last 25% of generations):
```
mutation_rate: 0.1
within_band_swap: 0.7  # More conservative
```

---

## 10. Integration with Crossover

### 10.1 Mutation After Crossover

Typical GA pipeline:
```
Parent A, Parent B
  → Crossover
    → Child (provisional)
      → Mutation
        → Child (final)
          → Repair (if needed)
            → Evaluation
```

**Why mutation after crossover**:
- Crossover creates building blocks
- Mutation fine-tunes crossover output
- Introduces variations that crossover cannot generate

### 10.2 Mutation vs. Crossover Rates

**Balanced approach** (recommended):
```
crossover_rate: 0.7   # 70% of offspring from crossover
mutation_rate: 0.3    # 30% of offspring mutated
```

**Mutation-heavy** (when stuck):
```
crossover_rate: 0.5
mutation_rate: 0.5
```

**Crossover-heavy** (when diverse population):
```
crossover_rate: 0.9
mutation_rate: 0.1
```

### 10.3 Operator Synergy

**Crossover strengths**:
- Combines large-scale structures
- Exploits population information
- Fast convergence

**Mutation strengths**:
- Explores local neighborhoods
- Maintains diversity
- Escapes local optima

**Synergy**: Crossover for macroscopic search, mutation for microscopic refinement.

---

## 11. Comparison to Classical Operators

### 11.1 Within-Band Swap ≈ Classical Swap

**Similarity**: Both exchange positions

**Difference**: Band-aware swap restricted to same (entity, band) unit

**Advantage**: Constraint preservation

### 11.2 Band-Local Jitter ≈ Gaussian Mutation

**Classical Gaussian mutation** (for continuous spaces):
```
x' = x + N(0, σ²)  # Add Gaussian noise
```

**Band-local jitter** (for discrete grids):
```
x' = x + random_offset within radius  # Add discrete offset
```

**Similarity**: Both move value to nearby location

**Difference**: Jitter respects grid structure and band boundaries

### 11.3 Micro-Reseed ≈ Random Mutation

**Classical random mutation**: Replace value with random new value

**Micro-reseed**: Replace subset of positions with random new positions

**Similarity**: Introduces random diversity

**Difference**: Reseed preserves band structure

---

## 12. Advanced Topics

### 12.1 Directed Mutation

Instead of random mutations, use problem knowledge:

**Separation-improving mutation**: Only accept mutations that increase minimum distance

**Coverage-improving mutation**: Move entities to under-represented regions

**Quota-balancing mutation**: Prefer moves that balance band quotas

**Trade-off**: Reduces exploration but improves quality per mutation.

### 12.2 Multi-Scale Mutation

Apply mutations at different spatial scales:

**Fine-scale**: ±1 cell moves (jitter radius = 1)
**Medium-scale**: ±3 cell moves (jitter radius = 3)
**Coarse-scale**: Reseed within band

**Benefit**: Explores at multiple granularities simultaneously.

### 12.3 Cooperative Mutation

Mutate multiple related entities together:

**Example**: If vinlet and voutlet should be near each other, mutate both simultaneously to maintain relationship.

**Challenge**: Requires domain knowledge of entity relationships.

---

## 13. Practical Guidelines

### 13.1 Debugging Mutations

**Verification checklist**:
- ✅ Entity counts preserved per band
- ✅ No entities outside allowed regions
- ✅ No entities crossing band boundaries
- ✅ No position overlaps created
- ✅ Operation log complete and accurate

**Common bugs**:
- Index errors when selecting positions
- Not checking for free cells before placement
- Forgetting to update occupied positions
- Cross-band moves in jitter/reseed

### 13.2 Parameter Tuning Workflow

**Step 1**: Start with recommended defaults

**Step 2**: Run for 10-20 generations, measure:
- Fitness improvement rate
- Population diversity
- Constraint violation rate
- Mutation success rate

**Step 3**: Adjust based on observations:
- If stuck (no improvement): Increase mutation_rate, increase micro_reseed
- If too chaotic (fitness decreasing): Decrease mutation_rate, increase swap
- If too slow: Increase jitter_radius, increase max_ops

**Step 4**: Iterate until satisfactory performance

### 13.3 Visualization for Analysis

**Useful plots**:
- Fitness vs. mutation rate (find optimal rate)
- Position changes histogram (verify mutations occur)
- Band distributions before/after (verify quota preservation)
- Min distance before/after mutation (assess quality impact)

---

## 14. Summary

Mutation operators for spatial placement problems must preserve constraints while exploring the solution space.

**Key Innovations**:
1. **Within-band swap**: Safe, conservative local exploration
2. **Band-local jitter**: Balanced exploration with spatial awareness
3. **Micro-reseed**: Aggressive exploration while maintaining structure

**Design Philosophy**:
- Operate within band boundaries (automatic constraint satisfaction)
- Combine multiple operators (diverse exploration strategies)
- Control disruption level (from gentle swaps to radical reseeding)

**Best Practices**:
- Start with balanced operator mix
- Adjust mutation rate based on search progress
- Log all operations for analysis
- Verify constraint preservation in tests

**Result**: Effective mutation that explores solution space without violating stratification or quota constraints.

---

## References

- Study of Various Mutation Operators in Genetic Algorithms. *IJCSIT*, Vol. 5, 2014.
- Performance Impact of Mutation Operators. *PMC*, 2016.
- Genetic Algorithms - Mutation. *Tutorialspoint*, 2024.
- Mutation in Genetic Algorithms. *GeeksforGeeks*, 2024.
- Your 2024 Guide to Mastering Genetic Algorithms. *NumberAnalytics*, 2024.
- A Review on Genetic Algorithm: Past, Present, and Future. *PMC*, 2020.

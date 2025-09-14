# Stratified, Non-Overlapping Multi-Entity Placement on a Rectangular Grid

## 1. Purpose

Design a general, repeatable procedure to place multiple entity types (e.g., Vinlet and ACinlet) on a rectangular grid so that:

- Each entity is **well spread** across both axes.
- The **union** of all entities is also well spread.
- **No overlaps** occur.
- The approach **scales** to any grid size or aspect ratio and to any number of entity types.

---

## 2. Scope & Definitions

- **Grid**: Discrete cells with integer coordinates \((x, y)\), \(x \in \{1,\dots,n\}\), \(y \in \{1,\dots,m\}\).
- **Region**: A subset of the grid where a particular entity is allowed (e.g., an “inlet zone”).
- **Entities**: Distinct types to be placed; each type \(E\) has a required count \(k_E\) and a permitted region.
- **Feasibility**: There exist at least \(\sum_E k_E\) distinct cells within the allowed regions across entities, with no cell used by more than one entity (unless joint occupancy is explicitly allowed, which is **not** assumed here).

---

## 3. Objectives

1. **Per-Entity Stratification**  
   Each entity’s placements should occupy the short axis (often \(y\)) and the long axis (often \(x\)) in a balanced way.

2. **Joint Stratification**  
   The union of all entities should not leave large gaps or starve any part of the region.

3. **Separation**  
   Maintain minimum distances:
   - **Intra-entity** minimum spacing \(r_\text{self}(E)\).
   - **Inter-entity** minimum spacing \(r_\text{cross}(E_i, E_j)\).

4. **Robustness to Aspect Ratio**  
   Perform well when the region is long in \(x\) or long in \(y\), or nearly square.

---

## 4. High-Level Procedure

### Phase A — Normalize & Partition

1. **Normalize Coordinates**  
   Map the allowed region of each entity to \([0,1]\times[0,1]\). This makes all subsequent rules scale-free.

2. **Choose Stratification**  
   - Split the region along \(y\) into \(N_y\) horizontal **bands** of equal height (or weighted as needed).  
   - Optionally split along \(x\) into \(N_x\) vertical **bands** for 2D stratification (forming \(N_x \times N_y\) cells).

3. **Set Quotas**  
   For each entity \(E\) with required count \(k_E\):
   - Assign a **per-y-band quota**: at least \(\lfloor k_E/N_y \rfloor\) per band, distributing remainders to bands with the lowest current allocation.  
   - If using 2D stratification, distribute \(k_E\) across \((x,y)\) cells to approximate uniform coverage.

> **Rationale:** Quotas guarantee that no rows (or bands) are starved for any entity.

---

### Phase B — Initial Per-Entity Placement (Meet Quotas)

4. **Band-First Placement**  
   For each entity \(E\), fill its quotas **band by band**:
   - Within a band (or band cell), pick cells that are **far from** existing placements of the **same entity** in that band to encourage spread.
   - If preferred, bias distances to emphasize \(y\) separation by using an **anisotropic measure** (e.g., scale \(y\) by factor \(w_y>1\)).

5. **Feasibility Checks**  
   - If a band lacks enough free cells to meet a quota, borrow from **adjacent bands** while tracking the deficit and noting the relaxation in the final report.
   - Respect each entity’s allowed region strictly.

> **Rationale:** This stage guarantees per-entity vertical occupancy before considering union-level spread.

---

### Phase C — Joint Refinement (Union-Level Blue-Noise)

6. **Define Separation Radii**  
   - Intra-entity radius \(r_\text{self}(E)\): minimum distance between two placements of entity \(E\).  
   - Cross-entity radius \(r_\text{cross}(E_i,E_j)\): minimum distance between any placements of \(E_i\) and \(E_j\).
   - Radii may be **anisotropic**: distance \(d=\sqrt{(x_1-x_2)^2 + (w_y(y_1-y_2))^2}\) to emphasize vertical fill.

7. **Local Improvement Iterations**  
   - Consider the **union** of all placements.  
   - Iteratively propose **local swaps** or **nudges** **within the same band** (or the same stratification cell) that increase:
     1) the **minimum** intra-entity distance for at least one entity, or  
     2) the **minimum** cross-entity distance,  
     without breaking quotas or violating allowed regions.
   - Prioritize moves that improve the **worst** current distance (lexicographic maximin).

8. **Conflict Resolution**  
   - If two entities contend for the same cell, attempt a **swap** within their respective bands so both satisfy band quotas and distances.  
   - If a band is too dense to satisfy radii, **reduce radii slightly and symmetrically** for all entities in that band, then continue refinement.

> **Rationale:** This creates a near blue-noise pattern for the union while preserving per-entity guarantees.

---

## 5. Acceptance Criteria & Reporting

- **Quota Satisfaction**  
  - Each entity meets its per-band quotas (or deviations are explicitly recorded with reasons).

- **Coverage Metrics**  
  - **Row/Band Coverage**: proportion of bands occupied by each entity and by the union.  
  - **1D Histograms** along \(y\) (and optionally \(x\)) for each entity and for the union; target near-uniform distributions.

- **Separation Metrics**  
  - **Minimum intra-entity distance** per entity.  
  - **Minimum cross-entity distance** across all entity pairs.  
  - Report anisotropy (the \(w_y\) used) and the realized min-gaps.

- **Feasibility Notes**  
  - Any relaxed constraints (e.g., reduced radii, borrowed quotas) are documented per band.

- **Constructability Hooks (Optional)**  
  - Keep-out zones, alignment preferences, symmetry constraints, or installer-preferred rows can be encoded as forbidden bands or weighted quotas.

---

## 6. Parameter Guidance

- **Number of Bands \(N_y\)**  
  - At least the number of distinct usable rows; more bands increase control but may reduce feasibility if counts are small.

- **Anisotropy Weight \(w_y\)**  
  - Use \(w_y>1\) when vertical fill is critical; set \(w_y=1\) for isotropic spacing.  
  - If the region is shallow in \(y\), a larger \(w_y\) combats clustering at \(y\)-extremes.

- **Radii Selection**  
  - Start from installation clearances or aesthetic spacing and adjust to achieve feasibility.  
  - Use **common radii** across entities for fairness unless domain reasons dictate otherwise.

---

## 7. Robustness to Aspect Ratio & Multiple Entities

- **Normalization** ensures decisions are not biased by absolute grid size.  
- **Stratification** controls the short axis explicitly, preventing starvation even when \(x \gg y\) or \(y \gg x\).  
- The procedure applies to **any number of entity types** by assigning quotas and radii per type and enforcing the same joint-refinement logic.

---

## 8. Expected Outcomes

- **No empty bands** for any entity within its allowed region unless infeasible.  
- **Balanced union** coverage that avoids piling up on boundary rows.  
- **Quantified spacing** and **clear deviations** when hard constraints force compromises.  
- A **repeatable, auditable** placement plan suitable for engineering review and aesthetics checks.

---

## 9. Checklist (Before Sign-off)

1. All entities meet band quotas or deviations are approved.  
2. Union-level coverage meets the target histograms (y—and x if applicable).  
3. Min-gap thresholds satisfied (intra-entity and cross-entity).  
4. No overlaps and all placements within allowed regions.  
5. Any relaxations (radii, quotas) are documented with justification.

---

## 10. Notes for Extension

- Incorporate **priority bands** (e.g., airflow or service access) by weighting quotas.  
- Support **heterogeneous radii** where certain entity pairs require larger separations.  
- Add **symmetry** or **gridline** alignment as optional constraints in Phase B.

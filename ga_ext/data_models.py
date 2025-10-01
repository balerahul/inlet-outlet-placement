"""
Data models for GA extension.

Core data structures representing individuals, parent manifests, and lineage records.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any


@dataclass
class Individual:
    """
    Represents a single placement layout (individual in GA population).

    Attributes:
        id: Unique identifier for this individual
        path: Path to CSV file containing placement data
        placements: Dictionary mapping entity_type to list of (x, y) positions
        metadata: Additional information (repair_notes, lineage, timestamps, etc.)
        external_score: Optional fitness score from external evaluator (not used for selection)
    """
    id: str
    path: Path
    placements: dict[str, list[tuple[int, int]]]
    metadata: dict[str, Any] = field(default_factory=dict)
    external_score: Optional[float] = None

    def __post_init__(self):
        """Ensure path is a Path object."""
        if not isinstance(self.path, Path):
            self.path = Path(self.path)

    def copy(self) -> "Individual":
        """
        Create a deep copy of this individual.

        Returns:
            New Individual with copied placements and metadata
        """
        return Individual(
            id=self.id,
            path=self.path,
            placements={
                entity_type: positions.copy()
                for entity_type, positions in self.placements.items()
            },
            metadata=self.metadata.copy(),
            external_score=self.external_score
        )

    def get_all_positions(self) -> set[tuple[int, int]]:
        """
        Get all occupied positions across all entity types.

        Returns:
            Set of (x, y) positions
        """
        positions = set()
        for entity_positions in self.placements.values():
            positions.update(entity_positions)
        return positions

    def get_entity_count(self, entity_type: str) -> int:
        """
        Get count of placements for specific entity type.

        Args:
            entity_type: Entity type to count

        Returns:
            Number of placements for this entity type
        """
        return len(self.placements.get(entity_type, []))

    def total_entity_count(self) -> int:
        """
        Get total count of all placements.

        Returns:
            Total number of placements across all entity types
        """
        return sum(len(positions) for positions in self.placements.values())


@dataclass
class ParentManifest:
    """
    Represents a set of parents selected by external evaluator.

    The manifest contains parent individuals along with optional metadata
    such as scores, weights, and tags. This structure supports weighted
    parent selection in offspring mode.

    Attributes:
        parents: List of Individual objects representing selected parents
        metadata: Additional information (selection criteria, generation number, etc.)
    """
    parents: list[Individual]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate manifest."""
        if not self.parents:
            raise ValueError("ParentManifest must contain at least one parent")

    def get_parent_by_id(self, parent_id: str) -> Optional[Individual]:
        """
        Retrieve parent by ID.

        Args:
            parent_id: ID of parent to retrieve

        Returns:
            Parent Individual if found, None otherwise
        """
        for parent in self.parents:
            if parent.id == parent_id:
                return parent
        return None

    def get_weights(self) -> Optional[list[float]]:
        """
        Get sampling weights for parents if available.

        Returns:
            List of weights (same length as parents) or None if not provided
        """
        if "weights" in self.metadata:
            weights = self.metadata["weights"]
            if len(weights) == len(self.parents):
                return weights
        return None

    def __len__(self) -> int:
        """Number of parents in manifest."""
        return len(self.parents)


@dataclass
class LineageRecord:
    """
    Tracks provenance of a generated child.

    Records all information needed to reproduce or understand how a child
    was created from its parents through GA operations.

    Attributes:
        child_path: Path to child CSV file
        parent_ids: List of parent IDs used to create this child
        mode: Generation mode ("variant" or "offspring")
        crossover_mask: Band-wise parent selection (if crossover was used)
        mutation_ops: List of mutation operations applied
        repair_notes: Notes from repair/refinement process
        seed: Random seed used for this child's generation
        timestamp: When this child was created
        metadata: Additional information
    """
    child_path: Path
    parent_ids: list[str]
    mode: str  # "variant" or "offspring"
    crossover_mask: Optional[dict[tuple[str, int], str]]  # {(entity_type, band_id): "A"|"B"}
    mutation_ops: list[str]
    repair_notes: str
    seed: int
    timestamp: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate lineage record and ensure path is Path object."""
        if not isinstance(self.child_path, Path):
            self.child_path = Path(self.child_path)

        if self.mode not in ["variant", "offspring", "immigrant"]:
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'variant', 'offspring', or 'immigrant'")

        if self.mode == "variant" and len(self.parent_ids) != 1:
            raise ValueError("Variant mode must have exactly one parent")

        if self.mode == "offspring" and len(self.parent_ids) < 2:
            raise ValueError("Offspring mode must have at least two parents")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert lineage record to dictionary for CSV export.

        Returns:
            Dictionary with string-serializable values
        """
        return {
            "child_path": str(self.child_path),
            "parent_ids": ",".join(self.parent_ids),
            "mode": self.mode,
            "crossover_mask": str(self.crossover_mask) if self.crossover_mask else "",
            "mutation_ops": "; ".join(self.mutation_ops),
            "repair_notes": self.repair_notes,
            "seed": self.seed,
            "timestamp": self.timestamp or "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageRecord":
        """
        Create lineage record from dictionary (e.g., from CSV).

        Args:
            data: Dictionary with lineage information

        Returns:
            LineageRecord instance
        """
        # Parse crossover mask from string representation
        crossover_mask = None
        if data.get("crossover_mask"):
            try:
                # This is a simplified parser; actual implementation may need eval or ast.literal_eval
                crossover_mask = eval(data["crossover_mask"])
            except:
                crossover_mask = None

        return cls(
            child_path=Path(data["child_path"]),
            parent_ids=data["parent_ids"].split(","),
            mode=data["mode"],
            crossover_mask=crossover_mask,
            mutation_ops=data["mutation_ops"].split("; ") if data["mutation_ops"] else [],
            repair_notes=data["repair_notes"],
            seed=int(data["seed"]),
            timestamp=data.get("timestamp") or None,
        )


def create_immigrant_record(child_path: Path, seed: int, timestamp: Optional[str] = None) -> LineageRecord:
    """
    Create a lineage record for an immigrant (fresh random layout).

    Args:
        child_path: Path to immigrant CSV
        seed: Random seed used
        timestamp: Creation timestamp

    Returns:
        LineageRecord for immigrant
    """
    return LineageRecord(
        child_path=child_path,
        parent_ids=[],
        mode="immigrant",
        crossover_mask=None,
        mutation_ops=[],
        repair_notes="Fresh random layout generated by existing engine",
        seed=seed,
        timestamp=timestamp,
    )

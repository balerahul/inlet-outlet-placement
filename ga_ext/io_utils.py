"""
I/O utilities for GA extension.

Handles CSV parsing/serialization, manifest loading, lineage logging,
and folder/file management.
"""

import csv
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
import yaml

from .data_models import Individual, ParentManifest, LineageRecord


def load_csv_to_individual(
    csv_path: Union[str, Path],
    individual_id: Optional[str] = None
) -> Individual:
    """
    Load a placement CSV file into an Individual object.

    CSV format:
        name,type,x,y
        acinlet_x5_y4,acinlet,5,4
        vinlet_x10_y8,vinlet,10,8
        ...

    Args:
        csv_path: Path to CSV file
        individual_id: Optional ID for the individual (defaults to filename stem)

    Returns:
        Individual object with placements loaded

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if individual_id is None:
        individual_id = csv_path.stem

    # Parse CSV
    placements = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        # Validate header
        if not all(col in reader.fieldnames for col in ['name', 'type', 'x', 'y']):
            raise ValueError(f"Invalid CSV format in {csv_path}. Expected columns: name,type,x,y")

        for row in reader:
            entity_type = row['type']
            x = int(row['x'])
            y = int(row['y'])

            if entity_type not in placements:
                placements[entity_type] = []

            placements[entity_type].append((x, y))

    return Individual(
        id=individual_id,
        path=csv_path,
        placements=placements,
        metadata={
            "loaded_at": datetime.now().isoformat(),
            "source_file": str(csv_path)
        }
    )


def save_individual_to_csv(
    individual: Individual,
    output_path: Union[str, Path],
    overwrite: bool = False
) -> Path:
    """
    Save an Individual object to CSV file.

    Args:
        individual: Individual to save
        output_path: Path for output CSV
        overwrite: If True, overwrite existing file

    Returns:
        Path to saved CSV file

    Raises:
        FileExistsError: If file exists and overwrite=False
    """
    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {output_path}")

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'type', 'x', 'y'])

        for entity_type, positions in sorted(individual.placements.items()):
            for idx, (x, y) in enumerate(positions):
                name = f"{entity_type}_x{x}_y{y}"
                writer.writerow([name, entity_type, x, y])

    # Update individual's path
    individual.path = output_path
    individual.metadata["saved_at"] = datetime.now().isoformat()

    return output_path


def load_parent_manifest(manifest_path: Union[str, Path]) -> ParentManifest:
    """
    Load a parent manifest CSV file.

    CSV format:
        id,path,score,weight,tags
        parent_001,ga_ext/gen_000/ind_001.csv,0.89,1.0,elite
        parent_002,ga_ext/gen_000/ind_005.csv,0.85,0.8,diverse

    Args:
        manifest_path: Path to manifest CSV

    Returns:
        ParentManifest object

    Raises:
        FileNotFoundError: If manifest file doesn't exist
        ValueError: If manifest format is invalid
    """
    manifest_path = Path(manifest_path)

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    parents = []
    weights = []
    manifest_metadata = {}

    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)

        # Validate required columns
        if 'id' not in reader.fieldnames or 'path' not in reader.fieldnames:
            raise ValueError(f"Invalid manifest format. Required columns: id, path")

        for row in reader:
            parent_id = row['id']
            parent_path = Path(row['path'])

            # Resolve relative paths relative to manifest directory
            if not parent_path.is_absolute():
                parent_path = manifest_path.parent / parent_path

            # Load individual
            individual = load_csv_to_individual(parent_path, parent_id)

            # Store external score if provided
            if 'score' in row and row['score']:
                individual.external_score = float(row['score'])

            # Store tags if provided
            if 'tags' in row and row['tags']:
                individual.metadata['tags'] = row['tags']

            parents.append(individual)

            # Store weight if provided
            if 'weight' in row and row['weight']:
                weights.append(float(row['weight']))
            else:
                weights.append(1.0)  # Default weight

    # Store weights in manifest metadata
    if weights:
        manifest_metadata['weights'] = weights

    manifest_metadata['manifest_path'] = str(manifest_path)
    manifest_metadata['loaded_at'] = datetime.now().isoformat()

    return ParentManifest(parents=parents, metadata=manifest_metadata)


def load_parents_from_directory(
    directory: Union[str, Path],
    pattern: str = "*.csv"
) -> ParentManifest:
    """
    Load all CSV files from a directory as parents.

    Args:
        directory: Directory containing parent CSV files
        pattern: Glob pattern for CSV files (default: "*.csv")

    Returns:
        ParentManifest with all loaded individuals

    Raises:
        FileNotFoundError: If directory doesn't exist
        ValueError: If no CSV files found
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    csv_files = sorted(directory.glob(pattern))

    if not csv_files:
        raise ValueError(f"No CSV files found in {directory} matching pattern {pattern}")

    parents = []
    for csv_file in csv_files:
        individual = load_csv_to_individual(csv_file)
        parents.append(individual)

    return ParentManifest(
        parents=parents,
        metadata={
            'source_directory': str(directory),
            'loaded_at': datetime.now().isoformat(),
            'count': len(parents)
        }
    )


def save_lineage_log(
    lineage_records: list[LineageRecord],
    output_path: Union[str, Path],
    overwrite: bool = False
) -> Path:
    """
    Save lineage records to CSV file.

    Args:
        lineage_records: List of LineageRecord objects
        output_path: Path for output CSV
        overwrite: If True, overwrite existing file

    Returns:
        Path to saved lineage log

    Raises:
        FileExistsError: If file exists and overwrite=False
    """
    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Lineage log already exists: {output_path}")

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV
    with open(output_path, 'w', newline='') as f:
        fieldnames = ['child_path', 'parent_ids', 'mode', 'crossover_mask',
                      'mutation_ops', 'repair_notes', 'seed', 'timestamp']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for record in lineage_records:
            writer.writerow(record.to_dict())

    return output_path


def create_generation_folder(
    root: Union[str, Path],
    generation: int,
    format_string: str = "gen_{:03d}"
) -> Path:
    """
    Create a generation folder with standard naming.

    Args:
        root: Root directory for GA outputs
        generation: Generation number
        format_string: Format string for generation folder name

    Returns:
        Path to created generation folder

    Raises:
        FileExistsError: If folder already exists
    """
    root = Path(root)
    gen_folder = root / format_string.format(generation)

    if gen_folder.exists():
        raise FileExistsError(f"Generation folder already exists: {gen_folder}")

    gen_folder.mkdir(parents=True, exist_ok=False)

    return gen_folder


def generate_child_path(
    generation_folder: Path,
    index: int,
    prefix: str = "child",
    format_string: str = "{:03d}"
) -> Path:
    """
    Generate a standard child file path.

    Args:
        generation_folder: Folder for this generation
        index: Child index
        prefix: Filename prefix (e.g., "child", "variant", "immigrant")
        format_string: Format string for index

    Returns:
        Path for child CSV file
    """
    filename = f"{prefix}_{format_string.format(index)}.csv"
    return generation_folder / filename


def load_config(config_path: Union[str, Path]) -> dict:
    """
    Load GA extension configuration from YAML file.

    Args:
        config_path: Path to config YAML file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def save_metadata(
    metadata: dict,
    output_path: Union[str, Path],
    overwrite: bool = False
) -> Path:
    """
    Save metadata to YAML sidecar file.

    Args:
        metadata: Metadata dictionary
        output_path: Path for output YAML
        overwrite: If True, overwrite existing file

    Returns:
        Path to saved metadata file

    Raises:
        FileExistsError: If file exists and overwrite=False
    """
    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Metadata file already exists: {output_path}")

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    return output_path


def validate_csv_format(csv_path: Union[str, Path]) -> tuple[bool, Optional[str]]:
    """
    Validate that CSV file has correct format.

    Args:
        csv_path: Path to CSV file

    Returns:
        Tuple of (is_valid, error_message)
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        return False, f"File not found: {csv_path}"

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            # Check required columns
            required_cols = {'name', 'type', 'x', 'y'}
            if not required_cols.issubset(set(reader.fieldnames or [])):
                return False, f"Missing required columns. Expected: {required_cols}"

            # Check at least one row
            row_count = 0
            for row in reader:
                row_count += 1
                # Validate types can be parsed
                try:
                    int(row['x'])
                    int(row['y'])
                except ValueError:
                    return False, f"Invalid x,y coordinates in row {row_count}"

            if row_count == 0:
                return False, "CSV file is empty (no placements)"

        return True, None

    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"

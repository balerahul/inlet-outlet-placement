"""
CLI module for GA extension.

Handles run configuration loading, validation, and mode dispatching.
"""

from typing import Dict, Any
from pathlib import Path
import yaml


class ConfigValidationError(Exception):
    """Raised when run configuration is invalid."""
    pass


def load_run_config(config_path: str) -> Dict[str, Any]:
    """
    Load run configuration from YAML file.

    Args:
        config_path: Path to run configuration YAML file

    Returns:
        Dictionary containing run configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigValidationError: If config is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in configuration file: {e}")

    if config is None:
        raise ConfigValidationError("Configuration file is empty")

    return config


def validate_run_config(config: Dict[str, Any]) -> None:
    """
    Validate run configuration structure.

    Args:
        config: Run configuration dictionary

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    # Check mode field
    if 'mode' not in config:
        raise ConfigValidationError("Missing required field: 'mode'")

    mode = config['mode']
    if mode not in ['variant', 'offspring']:
        raise ConfigValidationError(
            f"Invalid mode: '{mode}'. Must be 'variant' or 'offspring'"
        )

    # Check common required fields
    required_common = ['input', 'output', 'generation']
    for field in required_common:
        if field not in config:
            raise ConfigValidationError(f"Missing required field: '{field}'")

    # Validate input section
    if not isinstance(config['input'], dict):
        raise ConfigValidationError("'input' must be a dictionary")

    # Validate output section
    if not isinstance(config['output'], dict):
        raise ConfigValidationError("'output' must be a dictionary")

    if 'root' not in config['output']:
        raise ConfigValidationError("Missing required field: 'output.root'")

    # Validate generation section
    if not isinstance(config['generation'], dict):
        raise ConfigValidationError("'generation' must be a dictionary")

    # Mode-specific validation
    if mode == 'variant':
        _validate_variant_config(config)
    elif mode == 'offspring':
        _validate_offspring_config(config)


def _validate_variant_config(config: Dict[str, Any]) -> None:
    """
    Validate variant mode configuration.

    Args:
        config: Run configuration dictionary

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    # Check required input fields
    if 'parent' not in config['input']:
        raise ConfigValidationError("Variant mode requires 'input.parent' field")

    parent_path = Path(config['input']['parent'])
    if not parent_path.exists():
        raise ConfigValidationError(f"Parent file not found: {parent_path}")

    # Check required generation fields
    if 'variants' not in config['generation']:
        raise ConfigValidationError("Variant mode requires 'generation.variants' field")

    num_variants = config['generation']['variants']
    if not isinstance(num_variants, int) or num_variants <= 0:
        raise ConfigValidationError(
            f"'generation.variants' must be a positive integer, got: {num_variants}"
        )


def _validate_offspring_config(config: Dict[str, Any]) -> None:
    """
    Validate offspring mode configuration.

    Args:
        config: Run configuration dictionary

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    # Check that either parents_manifest or parents_dir is specified
    input_config = config['input']

    has_manifest = 'parents_manifest' in input_config
    has_dir = 'parents_dir' in input_config

    if not has_manifest and not has_dir:
        raise ConfigValidationError(
            "Offspring mode requires either 'input.parents_manifest' or 'input.parents_dir'"
        )

    if has_manifest and has_dir:
        raise ConfigValidationError(
            "Offspring mode cannot have both 'parents_manifest' and 'parents_dir'. "
            "Please specify only one."
        )

    # Validate path existence
    if has_manifest:
        manifest_path = Path(input_config['parents_manifest'])
        if not manifest_path.exists():
            raise ConfigValidationError(f"Parent manifest not found: {manifest_path}")

    if has_dir:
        dir_path = Path(input_config['parents_dir'])
        if not dir_path.exists():
            raise ConfigValidationError(f"Parent directory not found: {dir_path}")
        if not dir_path.is_dir():
            raise ConfigValidationError(f"Parent path is not a directory: {dir_path}")

    # Check required generation fields
    if 'children' not in config['generation']:
        raise ConfigValidationError("Offspring mode requires 'generation.children' field")

    num_children = config['generation']['children']
    if not isinstance(num_children, int) or num_children <= 0:
        raise ConfigValidationError(
            f"'generation.children' must be a positive integer, got: {num_children}"
        )

    # Validate immigrants (optional but must be valid if present)
    if 'immigrants' in config['generation']:
        num_immigrants = config['generation']['immigrants']
        if not isinstance(num_immigrants, int) or num_immigrants < 0:
            raise ConfigValidationError(
                f"'generation.immigrants' must be a non-negative integer, got: {num_immigrants}"
            )


def run_from_config(config_path: str) -> None:
    """
    Load run configuration and execute appropriate mode.

    This is the main entry point called by ga_cli.py.

    Args:
        config_path: Path to run configuration YAML file

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigValidationError: If config is invalid
        Various exceptions from mode implementations
    """
    # Load and validate config
    print(f"Loading configuration from: {config_path}")
    config = load_run_config(config_path)

    print(f"Validating configuration...")
    validate_run_config(config)

    mode = config['mode']
    print(f"Mode: {mode}\n")

    # Dispatch to appropriate mode
    if mode == 'variant':
        from .orchestration import run_variant_mode
        run_variant_mode(config)
    elif mode == 'offspring':
        from .orchestration import run_offspring_mode
        run_offspring_mode(config)
    else:
        # Should never reach here due to validation
        raise ConfigValidationError(f"Invalid mode: {mode}")

    print("\n✅ Run completed successfully!")

#!/usr/bin/env python3
"""
GA Evolution CLI - Minimal entry point.

This is the command-line interface for the genetic algorithm extension.
All configuration is specified in YAML files.

Usage:
    python3 ga_cli.py run_config.yaml
    python3 ga_cli.py --config run_config.yaml
    python3 ga_cli.py --help

Examples:
    # Generate variants from a single parent
    python3 ga_cli.py examples/variant_run.yaml

    # Generate offspring from multiple parents
    python3 ga_cli.py examples/offspring_run.yaml

For more details, see the documentation in GA_IMPLEMENTATION_ROADMAP.md
"""

import sys
from pathlib import Path

# Add project root to path if needed
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    """Main entry point for GA CLI."""
    # Handle help
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print(__doc__)
        sys.exit(0 if len(sys.argv) > 1 else 1)

    # Parse config path
    config_path = sys.argv[1]

    if config_path.startswith('--config='):
        config_path = config_path.split('=', 1)[1]
    elif config_path == '--config':
        if len(sys.argv) < 3:
            print("Error: --config requires an argument")
            print(__doc__)
            sys.exit(1)
        config_path = sys.argv[2]

    # Import and run
    try:
        from ga_ext.cli import run_from_config
        run_from_config(config_path)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

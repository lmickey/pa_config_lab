#!/usr/bin/env python3
"""
Legacy .bin to JSON Converter

This utility converts legacy encrypted .bin configuration files
to the new JSON format.

Usage:
    python convert_legacy_to_json.py
    
    Or from GUI: Tools -> Convert Legacy File
"""

import sys
import os
import pickle
import getpass
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import load_settings
from config.storage.json_storage import save_config_json
from config.schema.config_schema_v2 import create_empty_config_v2


def convert_legacy_file(
    input_file: str, output_file: str, password: str, encrypt_output: bool = False
) -> bool:
    """
    Convert legacy .bin file to JSON format.

    Args:
        input_file: Path to legacy .bin file
        output_file: Path for output JSON file
        password: Password for decryption
        encrypt_output: Whether to encrypt the output JSON

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Converting: {input_file}")
        print(f"Output to: {output_file}")

        # Derive key from password
        cipher = load_settings.derive_key(password)

        # Read and decrypt legacy file
        print("Reading legacy file...")
        with open(input_file, "rb") as f:
            encrypted_data = f.read()

        print("Decrypting...")
        decrypted_data = cipher.decrypt(encrypted_data)

        # Unpickle the data
        print("Unpickling data...")
        legacy_config = pickle.loads(decrypted_data)

        # Convert to v2 schema
        print("Converting to v2 schema...")
        config_v2 = convert_to_v2_schema(legacy_config)

        # Save as JSON
        print("Saving as JSON...")
        if encrypt_output:
            output_cipher, output_salt = cipher  # cipher is actually (cipher, salt) tuple
        else:
            output_cipher = None
            output_salt = None

        success = save_config_json(
            config_v2, output_file, cipher=output_cipher, salt=output_salt, encrypt=encrypt_output
        )

        if success:
            print("\n✅ Conversion successful!")
            print(f"Output file: {output_file}")
            if encrypt_output:
                print("Output is encrypted with the same password")
            else:
                print("Output is unencrypted JSON")
            return True
        else:
            print("\n❌ Failed to save JSON file")
            return False

    except Exception as e:
        print(f"\n❌ Conversion failed: {str(e)}")
        return False


def convert_to_v2_schema(legacy_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert legacy config format to v2 schema.

    Args:
        legacy_config: Legacy configuration dictionary

    Returns:
        v2 schema configuration dictionary
    """
    # Extract TSG ID from legacy config
    pa_data = legacy_config.get("paData", {})
    tsg_id = pa_data.get("paTsgId", "unknown")

    # Create empty v2 config
    config_v2 = create_empty_config_v2(source_tenant=tsg_id)

    # Store legacy data in custom section for backward compatibility
    config_v2["legacy_data"] = {
        "fwData": legacy_config.get("fwData", {}),
        "paData": pa_data,
        "configName": legacy_config.get("configName", ""),
    }

    # Add metadata
    config_v2["metadata"]["notes"] = (
        f"Converted from legacy .bin format\n"
        f"Original config name: {legacy_config.get('configName', 'unknown')}"
    )

    return config_v2


def interactive_convert():
    """Interactive conversion mode."""
    print("\n" + "=" * 60)
    print("Legacy .bin to JSON Converter")
    print("=" * 60 + "\n")

    # Get input file
    input_file = input("Enter path to legacy .bin file: ").strip()
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return False

    # Get password
    password = getpass.getpass("Enter decryption password: ")
    if not password:
        print("❌ Password is required")
        return False

    # Generate output filename
    input_path = Path(input_file)
    default_output = input_path.with_suffix(".json")
    output_file = (
        input(f"Enter output JSON file [{default_output}]: ").strip() or str(default_output)
    )

    # Ask about encryption
    encrypt_choice = input("Encrypt output JSON? (y/N): ").strip().lower()
    encrypt_output = encrypt_choice in ["y", "yes"]

    # Convert
    print("\nStarting conversion...")
    return convert_legacy_file(input_file, output_file, password, encrypt_output)


def batch_convert(input_dir: str, output_dir: str, password: str):
    """
    Batch convert all .bin files in a directory.

    Args:
        input_dir: Directory containing .bin files
        output_dir: Directory for output JSON files
        password: Password for decryption
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    bin_files = list(input_path.glob("*.bin"))

    if not bin_files:
        print(f"No .bin files found in {input_dir}")
        return

    print(f"\nFound {len(bin_files)} .bin files")
    print(f"Output directory: {output_dir}\n")

    success_count = 0
    for bin_file in bin_files:
        output_file = output_path / bin_file.with_suffix(".json").name
        if convert_legacy_file(str(bin_file), str(output_file), password, False):
            success_count += 1
        print()

    print(f"\n✅ Successfully converted {success_count}/{len(bin_files)} files")


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        # Interactive mode
        success = interactive_convert()
        sys.exit(0 if success else 1)
    elif len(sys.argv) == 4:
        # Single file mode: convert_legacy_to_json.py input.bin output.json password
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        password = sys.argv[3]
        success = convert_legacy_file(input_file, output_file, password, False)
        sys.exit(0 if success else 1)
    elif len(sys.argv) == 4 and sys.argv[1] == "--batch":
        # Batch mode: convert_legacy_to_json.py --batch input_dir output_dir
        input_dir = sys.argv[2]
        output_dir = sys.argv[3]
        password = getpass.getpass("Enter decryption password for all files: ")
        batch_convert(input_dir, output_dir, password)
    else:
        print("Usage:")
        print("  Interactive mode:")
        print("    python convert_legacy_to_json.py")
        print()
        print("  Single file mode:")
        print("    python convert_legacy_to_json.py input.bin output.json password")
        print()
        print("  Batch mode:")
        print("    python convert_legacy_to_json.py --batch input_dir output_dir")
        sys.exit(1)


if __name__ == "__main__":
    main()

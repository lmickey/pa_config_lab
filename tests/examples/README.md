# Test Examples Directory

This directory contains example configuration data for testing purposes. The structure mirrors the main `config/` directory structure to make it easy to find relevant examples.

## Structure

```
tests/examples/
├── config/
│   └── models/
│       ├── objects/          # Object examples (addresses, groups, services, etc.)
│       ├── policies/         # Policy examples (security rules, NAT, etc.)
│       ├── profiles/         # Profile examples (auth, decryption, security, etc.)
│       └── infrastructure/   # Infrastructure examples (IKE, IPsec, Service Connections, etc.)
└── README.md
```

## Data Sources

Example configurations can come from:

1. **Generated Examples**: Minimal valid configurations for testing basic functionality
2. **Production Captures**: Real configurations captured from production tenants (sanitized/anonymized)
3. **API Responses**: Raw API responses saved for testing parsing and validation

## File Naming Convention

- `{item_type}_minimal.json` - Minimal valid configuration
- `{item_type}_full.json` - Complete configuration with all optional fields
- `{item_type}_with_dependencies.json` - Configuration with dependencies
- `{item_type}_default.json` - Default/predefined configuration
- `{item_type}_folder.json` - Configuration in a folder
- `{item_type}_snippet.json` - Configuration in a snippet

## Usage in Tests

```python
import json
from pathlib import Path

# Load example configuration
example_path = Path(__file__).parent.parent / "examples" / "config" / "models" / "objects" / "address_minimal.json"
with open(example_path) as f:
    config = json.load(f)

# Use in test
item = AddressObject(config)
```

## Adding New Examples

When adding new examples:

1. **Sanitize data**: Remove sensitive information (IPs, names, etc.)
2. **Document**: Add comments explaining special cases
3. **Validate**: Ensure the example is valid according to API schema
4. **Minimize**: Start with minimal examples, add full examples later

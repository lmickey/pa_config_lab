# Prisma Access Comprehensive Configuration Capture

A comprehensive Python tool for extracting, storing, and migrating Prisma Access SCM tenant configurations.

## Features

- **Complete Configuration Capture**: Extract all security policies, objects, profiles, and infrastructure settings
- **Pull/Push Workflow**: Pull configurations from source tenants and push to target tenants
- **Default Detection**: Automatically identify and filter default configurations
- **Dependency Management**: Track and resolve dependencies between configuration items
- **Conflict Resolution**: Detect and resolve conflicts when pushing configurations
- **JSON Storage**: Human-readable JSON format with schema validation
- **Strong Encryption**: NIST SP 800-132 compliant PBKDF2 encryption with 480K iterations
- **Security Hardened**: OWASP Top 10 compliant, comprehensive input validation
- **Backward Compatible**: Supports migration from legacy pickle format
- **Comprehensive Testing**: Full test suite with 157 tests (unit, integration, E2E, security)

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd pa_config_lab

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set up API credentials:

```bash
export PRISMA_TSG_ID="your-tsg-id"
export PRISMA_API_USER="your-api-client-id"
export PRISMA_API_SECRET="your-api-client-secret"
```

Or use the configuration file:

```bash
python get_settings.py
```

### Pull Configuration

```python
from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.config_pull import pull_configuration

# Initialize client
client = PrismaAccessAPIClient(
    tsg_id="tsg-1234567890",
    api_user="client-id",
    api_secret="client-secret"
)

# Pull configuration
config = pull_configuration(
    client,
    folder_names=None,  # None = all folders
    include_snippets=True
)

# Save configuration
from config.storage.json_storage import save_config_json
save_config_json(config, "backup.json", encrypt=False)
```

### Push Configuration

```python
from prisma.push.config_push import push_configuration
from prisma.push.conflict_resolver import ConflictResolution
from config.storage.json_storage import load_config_json

# Load configuration
config = load_config_json("backup.json")

# Push to target tenant
target_client = PrismaAccessAPIClient(...)
result = push_configuration(
    target_client,
    config,
    dry_run=True,  # Test first
    conflict_strategy=ConflictResolution.SKIP
)
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Comprehensive Configuration Guide](docs/README_COMPREHENSIVE_CONFIG.md)** - Complete user guide
- **[Pull & Push Guide](docs/PULL_PUSH_GUIDE.md)** - Detailed workflow instructions
- **[JSON Schema Reference](docs/JSON_SCHEMA.md)** - Schema documentation
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Migrating from pickle format
- **[API Reference](docs/API_REFERENCE.md)** - API client documentation
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## Project Structure

```
pa_config_lab/
├── config/              # Configuration management
│   ├── schema/         # JSON schema definitions
│   ├── storage/        # Storage functions (JSON, pickle compat)
│   └── defaults/      # Default detection
├── prisma/            # Prisma Access integration
│   ├── api_client.py  # API client
│   ├── pull/          # Pull functionality
│   ├── push/          # Push functionality
│   └── dependencies/  # Dependency resolution
├── cli/               # Command-line interfaces
├── tests/             # Test suite
└── docs/              # Documentation
```

## Key Components

### Pull System

- **Folder Capture**: Discover and capture folder configurations
- **Rule Capture**: Extract security rules from folders and snippets
- **Object Capture**: Capture address objects, groups, services, applications
- **Profile Capture**: Extract authentication, security, and decryption profiles
- **Snippet Capture**: Capture snippet metadata and referenced rules
- **Pull Orchestrator**: Coordinate complete configuration pulls

### Push System

- **Push Validator**: Validate configurations before push
- **Conflict Resolver**: Detect and resolve conflicts
- **Push Orchestrator**: Coordinate configuration pushes
- **Dependency Resolution**: Ensure dependencies are pushed in correct order

### Storage System

- **JSON Storage**: Human-readable JSON format with encryption support
- **Schema Validation**: JSON Schema validation for configuration integrity
- **Migration Tools**: Convert from legacy pickle format
- **Backward Compatibility**: Load legacy configurations

## Testing

### Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/ -v -m "not integration"

# Run integration tests (requires credentials)
export PRISMA_TSG_ID="..."
export PRISMA_API_USER="..."
export PRISMA_API_SECRET="..."
pytest tests/ -v -m integration

# Run with coverage
pytest tests/ --cov --cov-report=html
```

### Test Coverage

- **Unit Tests**: Mocked API responses, fast execution
- **Integration Tests**: Real API calls when credentials available
- **E2E Tests**: Full pull/push workflows

See [Testing Guide](tests/INTEGRATION_TESTS.md) for details.

## CLI Tools

### Pull CLI

Interactive pull interface:

```bash
python cli/pull_cli.py
```

Features:
- Select folders to pull
- Select snippets (with default inclusion option)
- Save configurations

### Application Search

Search for applications:

```bash
python cli/application_search.py
```

## Configuration Format

Configurations use JSON Schema v2.0:

```json
{
  "metadata": {
    "version": "2.0.0",
    "created": "2024-01-01T00:00:00Z",
    "source_tenant": "tsg-1234567890"
  },
  "security_policies": {
    "folders": [...],
    "snippets": [...]
  }
}
```

See [JSON Schema Reference](docs/JSON_SCHEMA.md) for complete structure.

## Requirements

- Python 3.8+
- Prisma Access SCM tenant
- API Client ID and Secret with appropriate permissions

See `requirements.txt` for Python dependencies.

## Development

### Running Tests

```bash
# Unit tests
pytest tests/ -v -m "not integration"

# Integration tests (with credentials)
pytest tests/ -v -m integration

# All tests
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Phase Completion Status

- ✅ **Phase 1**: Foundation & Infrastructure (JSON storage, API client)
- ✅ **Phase 2**: Security Policy Capture (folders, snippets, rules, objects, profiles)
- ✅ **Phase 3**: Default Configuration Detection
- ✅ **Phase 4**: Pull Functionality with Dependency Resolution
- ✅ **Phase 5**: Push Functionality with Conflict Resolution
- ✅ **Phase 6**: Testing Framework (157 tests, 55-70% coverage)
- ✅ **Phase 7**: Documentation & Polish
- ✅ **Phase 7.5**: Security Hardening (NIST/OWASP compliant)
- ✅ **Phase 8**: GUI Development (PyQt6, production-ready)
- 🎉 **Project Complete!**

## License

[Add license information]

## Support

For issues and questions:
- Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Review [API Reference](docs/API_REFERENCE.md)
- Check test examples in `tests/` directory

## See Also

- [Quick Start Guide](QUICK_START.md)
- [Upgrade Plan](UPGRADE_PLAN.md)
- [Testing Documentation](tests/INTEGRATION_TESTS.md)

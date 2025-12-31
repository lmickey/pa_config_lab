# Manual Test Scripts

This directory contains manual test scripts used for development and validation. These are kept separate from the automated test suite in `/tests/`.

## Phase Test Scripts

- **test_phase1.py** - Phase 1 testing (Foundation)
- **test_phase2.py** - Phase 2 testing (Security Policy Capture)
- **test_phase3.py** - Phase 3 testing (Default Detection)
- **test_phase4.py** - Phase 4 testing (Pull Functionality)
- **test_phase5.py** - Phase 5 testing (Push Functionality)
- **test_phase5a.py** - Phase 5 testing variant A
- **test_phase5b.py** - Phase 5 testing variant B
- **test_phase5c.py** - Phase 5 testing variant C

## Special Purpose Tests

- **test_duplicate_objects.py** - Testing duplicate object handling

## Usage

These scripts are meant to be run manually during development to test specific features or scenarios. They are not part of the automated test suite run by pytest.

To run a manual test:

```bash
python tests/manual/test_phase1.py
```

## Automated Tests

For the automated test suite, see the test files in `/tests/`:
- `test_api_client.py`
- `test_infrastructure_capture.py`
- `test_security.py`
- etc.

Run automated tests with:

```bash
pytest tests/
```

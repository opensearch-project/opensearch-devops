# CDK Security Dependencies

This directory contains security-hardened Python dependencies for the OSCAR CDK infrastructure.

## Security Fixes Applied

- **CVE-2025-50181** and **CVE-2025-50182**: Fixed by pinning `urllib3==2.5.0`
- Explicit version constraints prevent vulnerable transitive dependencies

## Installation

### Standard Installation
```bash
pip install -r requirements.txt
```

### Secure Installation (Recommended)
```bash
./install-secure.sh
```

The secure installation script verifies that urllib3 is at the correct version and exits with an error if vulnerabilities are detected.

## Files

- `requirements.txt` - Main dependencies with security constraints
- `tests/requirements.txt` - Test dependencies (inherits security constraints)
- `install-secure.sh` - Secure installation script with verification

## Dependency Strategy

We explicitly pin `urllib3==2.5.0` and constrain `botocore<1.40.0,>=1.39.13` to prevent the vulnerable urllib3 1.26.20 from being installed through transitive dependencies.
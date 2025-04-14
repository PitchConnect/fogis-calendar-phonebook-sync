# Security Checks

This document outlines the security checks and tools used in the FogisCalendarPhoneBookSync project.

## Bandit

We use [Bandit](https://bandit.readthedocs.io/) to find common security issues in Python code. Bandit is a tool designed to find common security issues in Python code, such as:

- Use of assert statements in production code
- Use of exec or eval
- Hard-coded passwords or keys
- Use of insecure functions or modules
- SQL injection vulnerabilities
- Command injection vulnerabilities
- And many more

### Configuration

Our Bandit configuration is in the `.bandit.yaml` file with these key settings:

- **Excluded directories**: We exclude test directories and virtual environments from the scan
- **Skipped tests**: Some low-risk checks are skipped to reduce noise (see below)
- **Confidence level**: MEDIUM (reduces false positives)
- **Severity level**: MEDIUM (focuses on more important issues)

### Skipped Tests

We skip the following tests for specific reasons:

- **B101**: Assert used - assertions are removed when compiling to optimized byte code
- **B104**: Hardcoded bind all interfaces - acceptable for local development
- **B105**: Hardcoded password string - handled separately with environment variables
- **B110**: Try/except/pass detected - acceptable in some cases
- **B303**: Use of insecure MD2, MD4, MD5, or SHA1 hash function - not used for security
- **B311**: Random is not suitable for security/cryptographic purposes - not used for security
- **B314**: Blacklist calls to xml.etree.ElementTree.parse - not used for parsing untrusted XML
- **B320**: Blacklist calls to lxml.etree.parse - not used for parsing untrusted XML
- **B404**: Import of subprocess module - used safely
- **B603**: Subprocess call with shell=True - used safely
- **B607**: Start process with a partial path - used safely

### Integration

Bandit is integrated into our workflow in two ways:

1. **Pre-commit hook**: Runs automatically before each commit to catch security issues early
2. **CI workflow**: Runs as part of our Code Quality workflow in GitHub Actions

### Running Bandit Manually

You can run Bandit manually with the following command:

```bash
bandit -r . -c .bandit.yaml --exclude tests/,venv/,.venv/,env/,.env/,build/,dist/
```

For a more detailed report in JSON format:

```bash
bandit -r . -c .bandit.yaml --exclude tests/,venv/,.venv/,env/,.env/,build/,dist/ --format json --output bandit-results.json
```

## Future Security Enhancements

In the future, we plan to implement additional security measures:

1. **Dependency scanning**: Regular scanning of dependencies for known vulnerabilities
2. **Secret scanning**: Preventing accidental commit of secrets and credentials
3. **SAST (Static Application Security Testing)**: More comprehensive static analysis
4. **Security policy**: Formal security policy and responsible disclosure process

## References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Bandit Test Plugins](https://bandit.readthedocs.io/en/latest/plugins/index.html)
- [OWASP Python Security Project](https://owasp.org/www-project-python-security/)

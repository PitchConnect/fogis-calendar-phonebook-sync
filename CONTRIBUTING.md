# Contributing to FogisCalendarPhoneBookSync

First off, thank you for considering contributing to FogisCalendarPhoneBookSync! It's people like you that make this tool better for everyone.

The following is a set of guidelines for contributing to this project. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Gitflow Workflow](#gitflow-workflow)
  - [Branch Structure](#branch-structure)
  - [Workflow](#workflow)
  - [Merge Guidelines](#merge-guidelines)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Pull Requests](#pull-requests)
- [Development Guidelines](#development-guidelines)
  - [Code Style](#code-style)
  - [Testing](#testing)
  - [Documentation](#documentation)
- [Guidelines for AI Usage](#guidelines-for-ai-usage)
  - [For Human Contributors Using AI](#for-human-contributors-using-ai)
  - [For AI Agents](#for-ai-agents)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Gitflow Workflow

This project follows the Gitflow workflow, which is a branching model designed around project releases. Here's how we use it:

### Branch Structure

- `main`: The production branch. This branch contains the official release history.
- `develop`: The development branch. This is where all feature branches are merged and serves as an integration branch for features.
- `feature/*`: Feature branches. Created from `develop` and merged back into `develop`.
- `release/*`: Release branches. Created from `develop` when it's ready for a release.
- `hotfix/*`: Hotfix branches. Created from `main` to quickly patch production releases.

### Workflow

1. **Feature Development**:
   - Create a feature branch from `develop`: `git checkout -b feature/my-feature develop`
   - Work on your feature
   - When done, merge back to `develop` using a Pull Request
   - After approval, merge the PR (see [Merge Guidelines](#merge-guidelines) below)

### Merge Guidelines

When merging Pull Requests, follow these guidelines to maintain a clean and meaningful history:

1. **When to use Squash Merge**:
   - For feature branches with multiple small, incremental commits
   - When commit messages in the branch are not particularly meaningful
   - For simple changes where the commit history isn't important
   - For most documentation changes

2. **When to use Regular Merge (--no-ff)**:
   - For larger features with a well-structured commit history
   - When the individual commits tell a story about how the feature was developed
   - When each commit represents a logical, atomic change
   - For complex refactorings where the step-by-step changes are important

3. **After Merging**:
   - Always delete the feature branch both locally and remotely
   - Verify that the issue is properly closed if the PR resolves an issue
   - Check if any documentation needs to be updated

2. **Release Process**:
   - When `develop` is ready for release, create a release branch:
     `git checkout -b release/1.0.0 develop`
   - Make any final adjustments, version bumps, etc.
   - Merge to `main` when ready:
     ```
     git checkout main
     git merge --no-ff release/1.0.0
     git tag -a 1.0.0 -m "Version 1.0.0"
     git push origin main --tags
     ```
   - Also merge back to `develop`:
     ```
     git checkout develop
     git merge --no-ff release/1.0.0
     git push origin develop
     git branch -d release/1.0.0
     ```

3. **Hotfixes**:
   - If an issue in `main` needs immediate fixing:
     `git checkout -b hotfix/1.0.1 main`
   - Fix the issue
   - Merge to both `main` and `develop`:
     ```
     git checkout main
     git merge --no-ff hotfix/1.0.1
     git tag -a 1.0.1 -m "Version 1.0.1"
     git push origin main --tags
     git checkout develop
     git merge --no-ff hotfix/1.0.1
     git push origin develop
     git branch -d hotfix/1.0.1
     ```

## How Can I Contribute?

### Reporting Bugs

- **Use the GitHub issue tracker** to report bugs.
- **Check existing issues** to avoid duplicates.
- **Use the bug report template** if available.
- **Be detailed**: Include steps to reproduce, expected behavior, actual behavior, and your environment.

### Suggesting Enhancements

- **Use the GitHub issue tracker** for enhancement suggestions.
- **Check existing suggestions** to avoid duplicates.
- **Be specific** about the enhancement and its benefits.
- **Consider scope**: Will this enhancement be useful to others?

### Pull Requests

1. **Fork the repository** and create your branch from `develop`.
2. **Follow the Gitflow workflow** as described above.
3. **Follow the coding standards** described in the [Code Style](#code-style) section.
4. **Add tests** for new features or bug fixes.
5. **Update documentation** as needed.
6. **Submit a pull request** to the `develop` branch.

## Development Guidelines

### Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use meaningful variable and function names.
- Write docstrings for all functions, classes, and modules.
- Keep functions small and focused on a single responsibility.
- Use type hints where appropriate.

### Testing

- Write unit tests for all new functionality.
- Ensure all tests pass before submitting a pull request.
- Aim for high test coverage.
- Use pytest for testing.

### Documentation

- Update the README.md with details of changes to the interface.
- Update the documentation when changing functionality.
- Use clear, concise language in all documentation.
- Include examples where appropriate.

## Guidelines for AI Usage

### For Human Contributors Using AI

When using AI tools like GitHub Copilot, ChatGPT, or similar:

1. **Review all AI-generated code thoroughly**:
   - Ensure it follows our coding standards
   - Verify it works as expected
   - Check for security issues
   - Test it properly

2. **Disclose AI usage**:
   - Mention in your PR description if significant portions were AI-assisted
   - This helps reviewers focus on potential AI-specific issues

3. **Don't blindly trust AI output**:
   - AI can generate plausible-looking but incorrect code
   - AI may not understand project-specific constraints
   - AI might suggest outdated or insecure practices

4. **Use AI as a tool, not a replacement**:
   - AI is best for boilerplate code, repetitive tasks, or getting started
   - Complex logic, security-critical code, and architecture decisions should be human-reviewed

5. **Appropriate use cases**:
   - Generating test cases
   - Boilerplate code
   - Documentation
   - Refactoring suggestions
   - Learning about unfamiliar APIs

### For AI Agents

This section contains instructions for AI assistants that may be helping with this project:

1. **Issue and PR Management**:
   - Always reference issue numbers in commits and PRs using the format `#123`
   - When a PR resolves an issue, include "Fixes #123" or "Closes #123" in the PR description
   - When replacing a PR with a new one, reference the original PR

2. **Branch Management**:
   - Follow the Gitflow workflow described above
   - Delete feature branches after they are merged
   - Never commit directly to `main` or `develop` branches

3. **Code Generation**:
   - Generate code that follows the project's style guidelines
   - Include comprehensive docstrings and comments
   - Add appropriate error handling
   - Include tests for generated code

4. **Communication**:
   - Clearly explain the reasoning behind implementation choices
   - Highlight any limitations or edge cases in generated code
   - Be explicit about what parts of the code might need human review

5. **Documentation**:
   - Update documentation to reflect changes
   - Ensure README and other docs stay in sync with code changes
   - Document any non-obvious design decisions

By following these guidelines, both human contributors and AI assistants can work together effectively to improve this project.

---

Thank you for contributing to FogisCalendarPhoneBookSync!

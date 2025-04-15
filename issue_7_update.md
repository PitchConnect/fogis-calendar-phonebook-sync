# Set up CI/CD pipeline

## Description

The project currently has a partial CI/CD pipeline implemented through GitHub Actions. We need to complete the remaining components to have a fully functional CI/CD pipeline.

## Current Status

We've already implemented:
- ✅ GitHub Actions workflow files for CI/CD
- ✅ Test automation in the pipeline
- ✅ Code quality checks (flake8, black, etc.)
- ✅ Docker image building
- ✅ Basic deployment workflow structure

## Remaining Tasks

We still need to implement:
1. Docker image publishing to GitHub Container Registry with proper versioning
2. Status badges in README.md
3. Documentation for the CI/CD pipeline

## Technical Specifications

### 1. Docker Image Publishing

**Current Implementation:**
- The `deploy.yml` workflow builds Docker images
- Images are tagged but not published to a registry

**Required Changes:**
- Configure GitHub Container Registry (GHCR) authentication
- Push images to GHCR with proper tags
- Set up image retention policies

**Implementation Details:**

1. Update the `deploy.yml` workflow to publish images to GHCR:

```yaml
- name: Login to GitHub Container Registry
  uses: docker/login-action@v2
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and push Docker image
  uses: docker/build-push-action@v4
  with:
    context: .
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
    build-args: |
      VERSION=${{ steps.version.outputs.version }}
```

2. Configure image tagging strategy:

```yaml
- name: Extract metadata for Docker
  id: meta
  uses: docker/metadata-action@v4
  with:
    images: ghcr.io/${{ github.repository }}
    tags: |
      type=ref,event=branch
      type=ref,event=pr
      type=semver,pattern={{version}}
      type=semver,pattern={{major}}.{{minor}}
      type=sha,format=short
      ${{ env.VERSION }}
```

3. Set up image retention policy in repository settings:
   - Go to repository settings
   - Navigate to "Packages"
   - Configure package retention policy (e.g., keep last 10 versions)

### 2. Status Badges

**Implementation Details:**

Add the following badges to the README.md:

```markdown
# FogisCalendarPhoneBookSync

[![Tests](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/tests.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/tests.yml)
[![Code Quality](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/code-quality.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/code-quality.yml)
[![Docker Build](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/docker-build.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/docker-build.yml)
[![Deploy](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/deploy.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/deploy.yml)
```

### 3. CI/CD Documentation

Create a `docs/ci_cd.md` file with the following sections:

1. **Overview of CI/CD Pipeline**
   - Description of each workflow
   - Trigger conditions
   - Pipeline stages

2. **Workflow Details**
   - `tests.yml`: Unit and integration tests
   - `code-quality.yml`: Code quality checks
   - `docker-build.yml`: Docker image building
   - `deploy.yml`: Deployment workflow

3. **Docker Image Management**
   - Image tagging strategy
   - Registry information
   - Image retention policy

4. **Deployment Process**
   - Environment setup
   - Deployment triggers
   - Rollback procedures

5. **Troubleshooting**
   - Common issues and solutions
   - How to debug failed workflows

## Implementation Steps

### 1. Update Docker Image Publishing

1. Verify GitHub token permissions:
   - Go to repository settings
   - Navigate to "Actions" > "General"
   - Ensure "Read and write permissions" is selected under "Workflow permissions"

2. Update the `deploy.yml` workflow with the changes described above

3. Test the workflow by pushing a change to the develop branch

### 2. Add Status Badges

1. Update the README.md with the badge markdown shown above

2. Verify that the badges display correctly in the repository

### 3. Create CI/CD Documentation

1. Create the `docs/ci_cd.md` file with the sections outlined above

2. Update the main README.md to reference the new documentation

## Acceptance Criteria

- [ ] Docker images are automatically published to GitHub Container Registry
- [ ] Images are properly tagged with version information
- [ ] Status badges are added to README.md
- [ ] Comprehensive CI/CD documentation is created
- [ ] All workflows run successfully on both develop and main branches

## Resources

- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Docker Build and Push Action](https://github.com/docker/build-push-action)
- [GitHub Actions Badges](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/adding-a-workflow-status-badge)

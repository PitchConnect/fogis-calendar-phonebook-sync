# Deployment Guide

This document describes the deployment process for the FogisCalendarPhoneBookSync project.

## Overview

The project uses GitHub Actions for continuous integration and container building. The workflow builds Docker images and pushes them to GitHub Container Registry, making them available for deployment.

The deployment process is currently set up for manual deployment, with the infrastructure for automated deployment ready to be enabled when your server is prepared.

## Deployment Architecture

The deployment architecture consists of:

1. **GitHub Actions** - For building and testing the application
2. **GitHub Container Registry** - For storing Docker images
3. **Docker Compose** - For orchestrating the containers on your deployment server

When your server is ready, the workflow can be updated to include automated deployment.

## GitHub Environments

The project uses two GitHub environments:

1. **Development** - For the development environment
   - Automatically deployed when changes are pushed to the `develop` branch
   - Less strict resource limits
   - Debug mode enabled

2. **Production** - For the production environment
   - Requires manual approval before deployment
   - Deployed when changes are pushed to the `main` branch (after approval)
   - Stricter resource limits
   - Debug mode disabled
   - Includes rollback mechanisms

## Current Workflow

The current workflow consists of the following steps:

1. **Build** - Builds the Docker image and pushes it to GitHub Container Registry
2. **Notify** - Provides information about the built image and how to deploy it manually

### Build Process

The build process:

1. Checks out the code
2. Sets up Docker Buildx
3. Logs in to GitHub Container Registry
4. Generates a version number based on the branch/tag
5. Builds and pushes the Docker image with appropriate tags

### Manual Deployment Process

To deploy the application manually:

1. Pull the latest Docker image from GitHub Container Registry
2. Create an environment-specific `.env` file with your credentials
3. Run Docker Compose with the appropriate configuration file
4. Verify the deployment with health checks

### Future Automated Deployment

The workflow includes commented-out steps for automated deployment that can be enabled when your server is ready:

1. SSH into your deployment server
2. Copy deployment files
3. Pull the latest Docker image
4. Deploy using Docker Compose
5. Verify the deployment with health checks
6. Roll back to the previous version if deployment fails (production only)

## Versioning

The project uses the following versioning scheme:

- **Tagged releases** - Uses the tag as the version (e.g., `v1.0.0`)
- **Main branch** - Uses `main-YYYYMMDD-COMMIT_SHA` (e.g., `main-20230615-a1b2c3d4`)
- **Develop branch** - Uses `dev-YYYYMMDD-COMMIT_SHA` (e.g., `dev-20230615-a1b2c3d4`)

## Rollback Mechanism

The production deployment includes a rollback mechanism that:

1. Creates a backup of the current deployment before updating
2. Monitors the health of the new deployment
3. Automatically rolls back to the previous version if the new deployment fails

## Setting Up for Future Automated Deployment

When your server is ready, you can enable automated deployment. To set this up:

1. Generate an SSH key pair if you don't already have one:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-deployment"
   ```

2. Add the public key to the `~/.ssh/authorized_keys` file on your servers

3. Add the following secrets to your GitHub repository:
   - `SSH_PRIVATE_KEY`: The private key generated in step 1
   - `DEV_SERVER_HOST`: Hostname or IP of your development server
   - `DEV_SERVER_USER`: SSH username for your development server
   - `DEV_SERVER_PATH`: Path where the application should be deployed on your development server
   - `PROD_SERVER_HOST`: Hostname or IP of your production server
   - `PROD_SERVER_USER`: SSH username for your production server
   - `PROD_SERVER_PATH`: Path where the application should be deployed on your production server

4. Uncomment the deployment steps in the `.github/workflows/deploy.yml` file

## Required Secrets

The following secrets need to be set up in your GitHub repository:

### Current Required Secrets

- `FOGIS_USERNAME` - Your FOGIS username
- `FOGIS_PASSWORD` - Your FOGIS password
- `GOOGLE_CLIENT_ID` - Your Google API client ID
- `GOOGLE_CLIENT_SECRET` - Your Google API client secret

### Future Required Secrets (for automated deployment)

- `SSH_PRIVATE_KEY` - SSH private key for deployment
- `DEV_SERVER_HOST` - Hostname or IP of your development server
- `DEV_SERVER_USER` - SSH username for your development server
- `DEV_SERVER_PATH` - Path where the application should be deployed
- `PROD_SERVER_HOST` - Hostname or IP of your production server
- `PROD_SERVER_USER` - SSH username for your production server
- `PROD_SERVER_PATH` - Path where the application should be deployed

## Manual Deployment

You can also trigger a manual deployment using the GitHub Actions workflow dispatch:

1. Go to the "Actions" tab in your GitHub repository
2. Select the "Deploy" workflow
3. Click "Run workflow"
4. Select the branch and environment you want to deploy
5. Click "Run workflow"

## Deployment Scripts

The project includes several deployment scripts:

- `scripts/deploy.sh` - Main deployment script
- `scripts/backup.sh` - Script for backing up the current deployment
- `scripts/rollback.sh` - Script for rolling back to a previous deployment

These scripts can also be used for manual deployment if needed.

## Monitoring Deployments

You can monitor deployments in several ways:

1. **GitHub Actions** - Check the status of the deployment workflow
2. **Container Logs** - Check the logs of the deployed containers
3. **Health Endpoint** - Check the `/health` endpoint of the application

## Troubleshooting

If a deployment fails:

1. Check the GitHub Actions logs for error messages
2. Check the container logs using `docker-compose logs`
3. Verify that all required secrets are set correctly
4. Check the health endpoint to ensure the application is running
5. If necessary, manually trigger a rollback using `scripts/rollback.sh`

#!/bin/bash

# Branch Synchronization Helper Script
# Usage: ./scripts/sync-branches.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
FORCE_SYNC=false
DRY_RUN=false
VERBOSE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Branch Synchronization Helper Script

Usage: $0 [OPTIONS]

OPTIONS:
    -f, --force         Force synchronization (resolve conflicts automatically)
    -d, --dry-run       Show what would be done without making changes
    -v, --verbose       Enable verbose output
    -h, --help          Show this help message

EXAMPLES:
    $0                  # Check sync status and perform clean merge if possible
    $0 --dry-run        # Show what would be done
    $0 --force          # Force sync, resolving conflicts with main's version
    $0 --verbose        # Show detailed output

DESCRIPTION:
    This script helps synchronize the develop branch with main branch changes.
    It's particularly useful for resolving conflicts that arise when changes
    are made directly to main (hotfixes, infrastructure changes, etc.).

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE_SYNC=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function for verbose output
verbose_echo() {
    if [ "$VERBOSE" = true ]; then
        print_status "$1"
    fi
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

print_status "Starting branch synchronization check..."

# Fetch latest changes
verbose_echo "Fetching latest changes from origin..."
git fetch origin

# Check if branches exist
if ! git show-ref --verify --quiet refs/remotes/origin/main; then
    print_error "Main branch not found"
    exit 1
fi

if ! git show-ref --verify --quiet refs/remotes/origin/develop; then
    print_warning "Develop branch not found"
    if [ "$DRY_RUN" = true ]; then
        print_status "Would create develop branch from main"
        exit 0
    else
        print_status "Creating develop branch from main..."
        git checkout -b develop origin/main
        git push origin develop
        print_success "Develop branch created successfully"
        exit 0
    fi
fi

# Get commit SHAs
MAIN_SHA=$(git rev-parse origin/main)
DEVELOP_SHA=$(git rev-parse origin/develop)

verbose_echo "Main SHA: $MAIN_SHA"
verbose_echo "Develop SHA: $DEVELOP_SHA"

# Check if branches are already in sync
if [ "$MAIN_SHA" = "$DEVELOP_SHA" ]; then
    print_success "Branches are already in sync"
    exit 0
fi

# Check for differences
COMMITS_AHEAD=$(git rev-list --count origin/develop..origin/main)
COMMITS_BEHIND=$(git rev-list --count origin/main..origin/develop)

print_status "Branch status:"
echo "  - Main is $COMMITS_AHEAD commits ahead of develop"
echo "  - Develop is $COMMITS_BEHIND commits ahead of main"

if [ "$COMMITS_AHEAD" -eq 0 ]; then
    print_success "Develop is ahead of main - no sync needed"
    print_status "Use the auto-PR workflow to merge develop to main"
    exit 0
fi

# Show commits that would be synced
print_status "Commits to be synced from main to develop:"
git log --oneline origin/develop..origin/main --pretty=format:"  - %s (%h)"
echo

# Check for merge conflicts
verbose_echo "Checking for potential merge conflicts..."
MERGE_BASE=$(git merge-base origin/main origin/develop)
CONFLICT_CHECK=$(git merge-tree $MERGE_BASE origin/main origin/develop)

if echo "$CONFLICT_CHECK" | grep -q "<<<<<<< "; then
    print_warning "Merge conflicts detected!"

    if [ "$DRY_RUN" = true ]; then
        print_status "Would require conflict resolution or force sync"
        echo "Conflicting files:"
        echo "$CONFLICT_CHECK" | grep "<<<<<<< " | cut -d' ' -f2 | sort -u | sed 's/^/  - /'
        exit 0
    fi

    if [ "$FORCE_SYNC" = false ]; then
        print_error "Cannot perform automatic sync due to conflicts"
        print_status "Options:"
        echo "  1. Run with --force to automatically resolve conflicts (uses main's version)"
        echo "  2. Resolve conflicts manually:"
        echo "     git checkout develop"
        echo "     git merge main"
        echo "     # Resolve conflicts in your editor"
        echo "     git commit"
        echo "     git push origin develop"
        exit 1
    else
        print_warning "Force sync enabled - conflicts will be resolved using main's version"
    fi
else
    print_success "No merge conflicts detected"
fi

if [ "$DRY_RUN" = true ]; then
    print_status "Would perform clean merge from main to develop"
    exit 0
fi

# Perform the sync
print_status "Synchronizing develop with main..."

# Switch to develop branch
git checkout develop 2>/dev/null || git checkout -b develop origin/develop
git reset --hard origin/develop

# Perform merge
if [ "$FORCE_SYNC" = true ] && echo "$CONFLICT_CHECK" | grep -q "<<<<<<< "; then
    print_status "Performing force merge..."
    git merge origin/main --strategy-option=theirs --no-edit
    print_warning "Force merge completed - please review changes carefully"
else
    print_status "Performing clean merge..."
    git merge origin/main --no-edit
fi

# Push changes
print_status "Pushing synchronized develop branch..."
git push origin develop

print_success "Branch synchronization completed successfully!"
print_status "Summary:"
echo "  - Synced $COMMITS_AHEAD commits from main to develop"
echo "  - Merge type: $([ "$FORCE_SYNC" = true ] && echo "force" || echo "clean")"
echo "  - Latest develop SHA: $(git rev-parse HEAD)"

# Check for existing auto-PR
if git ls-remote --heads origin | grep -q "refs/heads/develop"; then
    print_status "Note: Check for existing auto-PRs that may need updating"
fi

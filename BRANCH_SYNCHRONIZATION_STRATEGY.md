# Branch Synchronization Strategy

## 🎯 **Overview**

This document outlines the comprehensive branch synchronization strategy for maintaining consistency between `main` and `develop` branches while allowing flexibility for different types of changes.

## 🔄 **Synchronization Workflows**

### **1. Standard Flow: develop → main**
- **Trigger**: Automatic when tests pass on develop
- **Workflow**: `auto-pr-develop-to-main.yml`
- **Purpose**: Regular feature integration

### **2. Reverse Flow: main → develop**
- **Trigger**: Automatic when commits are pushed to main
- **Workflow**: `sync-main-to-develop.yml`
- **Purpose**: Keep develop updated with hotfixes and infrastructure changes

## 📋 **Workflow Details**

### **Auto PR Develop to Main (`auto-pr-develop-to-main.yml`)**

**Triggers:**
- Push to develop branch
- Successful completion of Tests and Code Quality workflows
- Manual dispatch for testing

**Process:**
1. ✅ Verify all required tests pass
2. ✅ Check for existing develop→main PRs
3. ✅ Create new PR or update existing one
4. ✅ Add appropriate labels and notifications

**Enhanced Features:**
- Detects recent sync activity to avoid conflicts
- Provides detailed commit summaries
- Handles existing PR updates gracefully

### **Sync Main to Develop (`sync-main-to-develop.yml`)**

**Triggers:**
- Push to main branch
- PR merged to main
- Manual dispatch with force sync option

**Process:**
1. ✅ Check if develop branch exists (create if missing)
2. ✅ Detect merge conflicts before attempting sync
3. ✅ Perform clean merge or handle conflicts
4. ✅ Update existing auto-PRs with sync information
5. ✅ Create notification issues for manual resolution

**Conflict Resolution:**
- **Clean merge**: Automatic synchronization
- **Conflicts detected**: Create issue for manual resolution
- **Force sync**: Manual override option available

## 🚨 **Conflict Handling**

### **Automatic Detection**
The sync workflow uses `git merge-tree` to detect conflicts before attempting merge:
```bash
git merge-tree $(git merge-base origin/main origin/develop) origin/main origin/develop
```

### **Resolution Options**

#### **Option 1: Manual Resolution (Recommended)**
```bash
git checkout develop
git pull origin develop
git merge main
# Resolve conflicts in your editor
git add .
git commit -m "Resolve merge conflicts from main sync"
git push origin develop
```

#### **Option 2: Force Sync (Use with caution)**
- Trigger the sync workflow manually
- Enable "force_sync" option
- Uses `--strategy-option=theirs` to prefer main changes

#### **Option 3: Reset Develop to Main**
```bash
git checkout develop
git reset --hard main
git push --force origin develop
```

## 📊 **Monitoring and Notifications**

### **Successful Synchronization**
- ✅ Automatic comments on existing auto-PRs
- ✅ Summary of synced commits
- ✅ Merge type indication (clean vs. force)

### **Conflict Detection**
- 🚨 Automatic issue creation
- 📋 List of conflicting files
- 📖 Resolution instructions
- 🏷️ Appropriate labels for tracking

### **Integration with Existing Workflows**
- 🔄 Updates auto-PR descriptions
- 📈 Provides sync statistics
- ⚠️ Warns about force merges

## 🛠️ **Usage Scenarios**

### **Scenario 1: Infrastructure Change (like PR #98)**
1. **Direct to main**: Infrastructure PR targets main
2. **Auto-sync**: Sync workflow automatically updates develop
3. **Clean integration**: No conflicts expected
4. **Notification**: Auto-PR updated with sync info

### **Scenario 2: Hotfix**
1. **Emergency fix**: Hotfix pushed directly to main
2. **Conflict detection**: Sync workflow checks for conflicts
3. **Resolution**: Either automatic sync or manual resolution
4. **Tracking**: Issue created if manual resolution needed

### **Scenario 3: Regular Development**
1. **Feature development**: Work happens on develop
2. **Auto-PR creation**: Tests pass, PR created automatically
3. **Review and merge**: Standard review process
4. **No sync needed**: develop→main flow, no reverse sync required

## 🔧 **Configuration Options**

### **Manual Triggers**
Both workflows support manual triggering:
- **Auto-PR**: For testing PR creation logic
- **Sync**: With force option for conflict override

### **Customizable Behavior**
- **Conflict strategy**: Configurable merge strategies
- **Notification targets**: Customizable issue creation
- **Label management**: Automatic labeling for tracking

## 📈 **Benefits**

### **Consistency**
- ✅ Branches stay synchronized automatically
- ✅ No manual intervention required for clean merges
- ✅ Clear process for conflict resolution

### **Flexibility**
- ✅ Supports both standard and emergency workflows
- ✅ Handles infrastructure changes appropriately
- ✅ Provides override options when needed

### **Visibility**
- ✅ Clear notifications and tracking
- ✅ Detailed sync information
- ✅ Integration with existing PR workflows

## 🚀 **Best Practices**

### **For Developers**
1. **Regular sync**: Pull latest develop before starting work
2. **Conflict awareness**: Watch for sync conflict notifications
3. **Clean commits**: Keep commit history clean for easier merging

### **For Maintainers**
1. **Monitor sync issues**: Address conflict notifications promptly
2. **Review force syncs**: Carefully review any force-merged changes
3. **Update documentation**: Keep sync strategy documentation current

### **For Infrastructure Changes**
1. **Target main directly**: For CI/CD and infrastructure improvements
2. **Comprehensive testing**: Ensure changes work in production pipeline
3. **Document rationale**: Explain why bypassing develop is appropriate

## 🔍 **Troubleshooting**

### **Common Issues**
- **Sync conflicts**: Follow manual resolution process
- **Missing develop**: Workflow automatically creates branch
- **Failed auto-PRs**: Check test status and workflow logs

### **Emergency Procedures**
- **Force sync**: Use manual trigger with force option
- **Reset branches**: Nuclear option for severe conflicts
- **Disable workflows**: Temporary disable for maintenance

---

**This synchronization strategy ensures branch consistency while maintaining development workflow flexibility.**

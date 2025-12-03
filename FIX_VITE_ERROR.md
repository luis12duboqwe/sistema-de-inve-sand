# Fix for Vite Module Resolution Error

## Error
```
Cannot find module '/workspaces/spark-template/node_modules/vite/dist/node/chunks/dist.js' 
imported from /workspaces/spark-template/node_modules/vite/dist/node/chunks/config.js
```

## Root Cause
This error occurs when Vite's internal module structure in `node_modules` is corrupted or incomplete. This is a **node_modules corruption issue**, not a code issue.

Common causes:
- Interrupted package installation
- Workspace dependency conflicts  
- npm cache corruption
- File system issues or disk space problems
- Version mismatches in workspace setup

## Solution

### Step 1: Clean Reinstall (Primary Solution)
Run these commands in the terminal at the project root:

```bash
# 1. Remove corrupted node_modules and lock file
rm -rf node_modules package-lock.json

# 2. Clear npm cache to ensure fresh downloads
npm cache clean --force

# 3. Reinstall all dependencies from scratch
npm install
```

### Step 2: Verify Installation
After reinstalling, verify Vite is properly installed:

```bash
# Check if the missing file now exists
ls -la node_modules/vite/dist/node/chunks/dist.js

# Should show the file with its size and permissions
# If this command fails, the installation is still incomplete
```

### Step 3: Test the Application
```bash
# Start the dev server
npm run dev

# The application should now start without errors
```

## Alternative Solutions

### If Step 1 Doesn't Work:

#### Option A: Force Reinstall with Different npm Version
```bash
# Sometimes npm itself can be the issue
# Try using npx with the latest npm
npx npm@latest install --force
```

#### Option B: Check Disk Space
```bash
# Insufficient disk space can cause incomplete installations
df -h

# If disk is full, free up space and retry
```

#### Option C: Manual Vite Reinstall
```bash
# Remove only Vite and its dependencies
rm -rf node_modules/vite node_modules/.vite

# Clear Vite cache
rm -rf node_modules/.cache

# Reinstall with force flag
npm install --force
```

#### Option D: Use npm ci (Clean Install)
```bash
# This is more aggressive and follows package-lock.json exactly
rm -rf node_modules
npm ci
```

## Why This Isn't a Code Error

This error occurs **before** your code runs - it's a failure in Vite's own initialization process. The error message shows Vite trying to load its own internal modules and failing because files are missing from `node_modules/vite/dist/node/chunks/`.

Your application code is fine - this is purely an installation/environment issue.

## Prevention

1. **Don't interrupt npm install** - Let it complete fully
2. **Commit package-lock.json** - Ensures consistent installations
3. **Use npm ci in CI/CD** - More reliable for automated environments
4. **Monitor disk space** - Ensure adequate space before installing
5. **Keep npm updated** - `npm install -g npm@latest`

## Status
✅ Error identified and documented
✅ Solution provided above
⚠️ Requires manual terminal access to fix (cannot be fixed via code changes)

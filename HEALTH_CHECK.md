# Health Check System - Sistema de Diagnóstico de Salud

## Overview

The inventory management system now includes an automated health check feature that detects corrupted dependencies, data integrity issues, and orphaned records.

## Features

### 1. **Automated Dependency Validation**
- Detects orphaned products referencing non-existent profiles
- Identifies orders with invalid profile references
- Finds order items pointing to deleted products

### 2. **Data Integrity Checks**
- Validates negative stock levels
- Detects invalid prices (zero, negative, NaN, Infinity)
- Checks for corrupted data structures
- Identifies empty or invalid order items

### 3. **Duplicate Detection**
- Finds duplicate SKUs within the same profile
- Detects duplicate profile slugs

### 4. **Consistency Analysis**
- Identifies unused active profiles
- Validates data type consistency

### 5. **Auto-Fix Capabilities**
- Automatically corrects negative stock to zero
- Provides clear indication of which issues can be auto-repaired

## Usage

### Accessing the Health Check

Click the **Pulse icon** (🩺) in the header next to the settings button to open the health check dialog.

### Running a Diagnostic

1. Open the Health Check dialog
2. Click "Ejecutar Diagnóstico" (Run Diagnostic)
3. Wait for the analysis to complete
4. Review the results organized by severity:
   - **Critical**: Issues that need immediate attention
   - **Warnings**: Issues that should be addressed soon
   - **Info**: Informational findings

### Auto-Repair

If auto-repairable issues are detected:

1. Click "Reparación Automática" (Auto-Repair) button
2. The system will automatically fix supported issues
3. A success message will show the number of fixes applied
4. The diagnostic will automatically re-run to verify fixes

## Issue Categories

### Orphan (Huérfano)
Records that reference non-existent parent records:
- Products without valid profiles
- Orders without valid profiles  
- Order items without valid products

### Integrity (Integridad)
Data validation issues:
- Negative stock levels
- Invalid prices
- Corrupted data structures
- Invalid order item quantities or prices

### Duplicate (Duplicado)
Duplicate values where uniqueness is expected:
- Duplicate SKUs within a profile
- Duplicate profile slugs

### Consistency (Consistencia)
Consistency and usage issues:
- Unused active profiles

## Technical Implementation

### Core Components

**`/src/lib/healthCheck.ts`**
- `InventoryHealthCheck` class: Main health check engine
- `HealthCheckResult` interface: Result structure
- `HealthCheckIssue` interface: Individual issue structure
- `autoFixIssues()` function: Auto-repair logic

**`/src/components/HealthCheckDialog.tsx`**
- User interface for health check feature
- Results visualization
- Expandable issue details
- Auto-fix trigger

**`/src/hooks/use-health-check.ts`**
- React hook for health check management
- Async check execution
- Auto-fix wrapper

### Integration

The health check is integrated into `App.tsx`:

```typescript
const { result, isRunning, runCheck, performAutoFix } = useHealthCheck(
  products ?? [],
  orders ?? [],
  profiles ?? []
)
```

### Health Check Process

1. **Data Collection**: Gathers current products, orders, and profiles
2. **Validation**: Runs all check methods
3. **Issue Aggregation**: Collects all detected issues
4. **Categorization**: Organizes issues by severity and category
5. **Results**: Returns comprehensive health report

## Best Practices

### When to Run Health Checks

- After importing data from CSV
- Before major data migrations
- When experiencing unexpected errors
- Periodically (weekly/monthly) for data hygiene
- After bulk operations

### Interpreting Results

- **Healthy System**: Zero critical issues and warnings
- **Minor Issues**: Only info-level findings
- **Needs Attention**: Warnings present but no critical issues
- **Critical State**: Critical issues require immediate action

### Fixing Issues

1. **Auto-Fixable**: Use auto-repair first for safe automatic fixes
2. **Manual Review**: Carefully review orphaned records before deletion
3. **Data Cleanup**: Address duplicates based on business rules
4. **Prevention**: Implement data validation at entry points

## API Reference

### `InventoryHealthCheck`

```typescript
class InventoryHealthCheck {
  constructor(
    products: ProductWithStock[],
    orders: OrderWithItems[],
    profiles: Profile[]
  )
  
  async runFullCheck(): Promise<HealthCheckResult>
}
```

### `HealthCheckResult`

```typescript
interface HealthCheckResult {
  healthy: boolean
  issues: HealthCheckIssue[]
  summary: {
    critical: number
    warnings: number
    info: number
  }
  lastCheck: string
}
```

### `HealthCheckIssue`

```typescript
interface HealthCheckIssue {
  id: string
  severity: 'critical' | 'warning' | 'info'
  category: 'dependency' | 'integrity' | 'orphan' | 'duplicate' | 'consistency'
  message: string
  affectedItems: Array<{
    type: 'product' | 'order' | 'profile' | 'orderItem'
    id: number
    name?: string
  }>
  autoFixable: boolean
  fixAction?: () => void
}
```

## Future Enhancements

- Scheduled automatic health checks
- Health check history tracking
- Email notifications for critical issues
- Custom check rules configuration
- Export health reports to PDF/CSV
- Integration with backup/restore workflow

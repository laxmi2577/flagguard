# Basic Example

This example demonstrates FlagGuard with a simple configuration that has conflicts.

## The Problem

The `flags.json` has:
- `new_checkout` requires `payment_enabled`
- `premium_tier` requires `payment_enabled`
- BUT `payment_enabled` is **disabled**

This creates impossible states that FlagGuard will detect.

## Running the Example

```bash
cd examples/basic
flagguard analyze --config flags.json --source src --no-llm
```

## Expected Output

FlagGuard will detect:
1. **Critical Conflict**: `new_checkout` is enabled but requires `payment_enabled` which is disabled
2. **Critical Conflict**: `premium_tier` is enabled but requires `payment_enabled` which is disabled
3. **Dead Code**: Code paths requiring both `premium_tier` and `payment_enabled` are unreachable

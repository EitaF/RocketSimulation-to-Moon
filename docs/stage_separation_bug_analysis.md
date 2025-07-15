# Stage Separation Bug Analysis

## Summary
The rocket simulation gets stuck in an infinite loop with "Unexpected stage 0 in separation" errors. This analysis identifies the root cause and provides solutions.

## Root Cause Analysis

### 1. **The Critical Bug: Missing `separate_stage()` Call**

The fundamental issue is that the code sets `rocket.phase = MissionPhase.STAGE_SEPARATION` but **never actually calls `rocket.separate_stage()`** to increment the stage index.

**Location of the bug:**
- Line 537: `self.rocket.phase = MissionPhase.STAGE_SEPARATION` (velocity-triggered stage 3)
- Line 921: `self.rocket.phase = MissionPhase.STAGE_SEPARATION` (propellant-critical stage separation)

**What happens:**
1. Phase gets set to `STAGE_SEPARATION`
2. Code enters the stage separation handler (line 564)
3. `current_stage` is still 0 (or whatever it was before)
4. Code hits the `else` clause (line 579) because `current_stage=0` is unexpected
5. Phase is never changed from `STAGE_SEPARATION`
6. **Infinite loop**: Next simulation step repeats the same logic

### 2. **Stage Indexing Logic**

The Saturn V has 3 stages configured as:
- **Stage 0**: S-IC (1st Stage) - should separate to become stage 1
- **Stage 1**: S-II (2nd Stage) - should separate to become stage 2  
- **Stage 2**: S-IVB (3rd Stage) - should separate to become stage 3

The stage separation handler expects:
- `current_stage == 1` after S-IC separation
- `current_stage == 2` after S-II separation
- `current_stage == 3` after S-IVB separation

### 3. **Two Trigger Points for the Bug**

#### Trigger A: Velocity-Triggered Stage 3 (Line 537)
```python
if stage3_velocity_trigger:
    self.rocket.phase = MissionPhase.STAGE_SEPARATION  # BUG: No separate_stage() call
    return
```

#### Trigger B: Propellant-Critical Stage Separation (Line 921)
```python
if propellant_usage_pct > propellant_threshold:
    self.rocket.phase = MissionPhase.STAGE_SEPARATION  # BUG: No separate_stage() call
```

### 4. **Stage Separation Handler Logic Flaw**

The stage separation handler (lines 564-581) assumes that `current_stage` has already been incremented by a previous `separate_stage()` call. However, the triggers above only set the phase without incrementing the stage.

**Expected flow:**
1. Call `rocket.separate_stage(current_time)` → increments `current_stage`
2. Set `rocket.phase = MissionPhase.STAGE_SEPARATION`
3. Handler processes the separation with the new stage index

**Actual flow (buggy):**
1. Set `rocket.phase = MissionPhase.STAGE_SEPARATION` (no stage increment)
2. Handler processes separation with old stage index
3. Old stage index (e.g., 0) is unexpected → warning + no phase change
4. Infinite loop

## Solutions

### Solution 1: Add Missing `separate_stage()` Calls

**Fix for Trigger A (Line 537):**
```python
if stage3_velocity_trigger:
    # Actually perform the stage separation
    if self.rocket.separate_stage(current_time):
        self.rocket.phase = MissionPhase.STAGE_SEPARATION
        self.logger.info(f"*** Stage separated: now at stage {self.rocket.current_stage} ***")
    return
```

**Fix for Trigger B (Line 921):**
```python
if propellant_usage_pct > propellant_threshold:
    # Actually perform the stage separation
    if self.rocket.separate_stage(t):
        self.rocket.phase = MissionPhase.STAGE_SEPARATION
        self.logger.warning(f"Stage {self.rocket.current_stage} separation completed")
    else:
        self.logger.error(f"Stage separation failed - no more stages")
```

### Solution 2: Fix Stage Separation Handler Logic

**Current handler logic (buggy):**
```python
elif current_phase == MissionPhase.STAGE_SEPARATION:
    if self.rocket.current_stage == 1:  # Expects stage already incremented
        self.rocket.phase = MissionPhase.APOAPSIS_RAISE
    # ... etc
```

**Fixed handler logic:**
```python
elif current_phase == MissionPhase.STAGE_SEPARATION:
    # Handle separation based on the stage that was just separated from
    previous_stage = self.rocket.current_stage - 1
    if previous_stage == 0:  # Just separated from S-IC
        self.rocket.phase = MissionPhase.APOAPSIS_RAISE
    elif previous_stage == 1:  # Just separated from S-II
        self.rocket.phase = MissionPhase.COAST_TO_APOAPSIS
    # ... etc
```

### Solution 3: Alternative - Remove Explicit STAGE_SEPARATION Phase

Since `rocket.separate_stage()` already handles the stage transition, the explicit `STAGE_SEPARATION` phase might be unnecessary. The automatic stage separation in `rocket.update_stage()` (line 1048) could handle all cases.

## Recommended Fix

**Apply Solution 1** as it's the most straightforward and preserves the existing architecture:

1. **Line 537 fix**: Add `self.rocket.separate_stage(current_time)` before setting phase
2. **Line 921 fix**: Add `self.rocket.separate_stage(t)` before setting phase  
3. **Add error handling**: Check if `separate_stage()` returns `True` before setting phase

This ensures that:
- Stage index is properly incremented before entering the separation handler
- The handler receives the expected stage indices (1, 2, 3)
- No infinite loops occur
- Existing logic is preserved

## Additional Improvements

1. **Add bounds checking** in the stage separation handler
2. **Add timeout protection** to prevent infinite loops
3. **Improve logging** to track stage transitions more clearly
4. **Add unit tests** for stage separation logic

## Testing Strategy

1. Test normal stage separations (S-IC → S-II → S-IVB)
2. Test velocity-triggered stage 3 ignition
3. Test propellant-critical stage separations
4. Test edge cases (no more stages, separation failures)
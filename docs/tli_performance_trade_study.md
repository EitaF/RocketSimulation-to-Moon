# TLI Performance Trade Study - v31

**Date:** 2025-07-05  
**Subject:** S-IVB Performance Deficit Resolution  
**Analyst:** Rocket Simulation Engineering Team

## Executive Summary

The v30 validation revealed a critical S-IVB performance deficit of 25.422 km²/s² in C3 energy, preventing successful Trans-Lunar Injection. This trade study analyzes three options to resolve this deficit and recommends the optimal solution.

## Performance Gap Analysis

### Current State
- **Required C3 Energy:** -1.75 km²/s² (target range: -2.0 to -1.5 km²/s²)
- **Achieved C3 Energy:** -27.422 km²/s²
- **Performance Deficit:** 25.422 km²/s² (92% shortfall)
- **Required Additional Delta-V:** ~1,350 m/s
- **Current S-IVB Propellant:** 106 tons
- **Current Payload Mass:** 45 tons

### Root Cause
The S-IVB stage propellant mass (106 tons) is insufficient compared to historical Saturn V specifications (119-123 tons), resulting in inadequate delta-V capability for TLI burn.

## Option Analysis

### Option A: Increase S-IVB Propellant Mass
**Approach:** Increase propellant from 106 tons to 122 tons (+15.1%)

**Advantages:**
- Realistic engineering solution matching historical Saturn V specifications
- Maintains full mission capability and payload mass
- Requires no mission profile changes
- Aligns with proven Apollo-era vehicle design

**Disadvantages:**
- Requires vehicle structural modifications
- Increases total vehicle mass by 16 tons
- May require launch pad infrastructure updates

**Technical Analysis:**
- New mass ratio: (13,494 + 122,000 + 45,000) / (13,494 + 45,000) = 3.09
- Theoretical delta-V: 461 × 9.80665 × ln(3.09) = 5,113 m/s
- Available delta-V margin: 5,113 - 3,150 = 1,963 m/s (62% margin)

### Option B: Reduce Payload Mass
**Approach:** Reduce payload from 45 tons to 15 tons (-67%)

**Advantages:**
- No vehicle modifications required
- Simple implementation
- Maintains current propellant loading

**Disadvantages:**
- Severe mission capability reduction (67% payload loss)
- Defeats purpose of lunar mission architecture
- Reduces scientific/operational value

**Technical Analysis:**
- New mass ratio: (13,494 + 106,000 + 15,000) / (13,494 + 15,000) = 4.72
- Theoretical delta-V: 461 × 9.80665 × ln(4.72) = 6,963 m/s
- Payload reduction required: 30 tons

### Option C: Multi-burn TLI Strategy
**Approach:** Multiple perigee burns to gradually raise apogee

**Advantages:**
- Uses existing hardware efficiently
- Innovative approach to performance limitations
- No vehicle modifications

**Disadvantages:**
- Complex guidance system implementation
- Longer mission duration
- Higher operational complexity
- Unproven for lunar missions

**Technical Analysis:**
- Requires 3-4 perigee burns
- Each burn: ~800-1,000 m/s delta-V
- Total mission time increase: 4-6 hours

## Recommendation: Option A - Increase S-IVB Propellant Mass

### Rationale
1. **Historical Precedent:** The Apollo Saturn V S-IVB stage carried 119-123 tons of propellant, making 122 tons a realistic specification.

2. **Performance Margin:** The 15.1% propellant increase provides 62% delta-V margin, ensuring mission success with reserves.

3. **Mission Integrity:** Maintains full 45-ton payload capability, preserving mission objectives.

4. **Risk Mitigation:** Proven technology approach reduces programmatic risk compared to innovative multi-burn strategies.

5. **Cost-Effectiveness:** Vehicle modification is more cost-effective than payload reduction or complex guidance systems.

### Implementation
- **S-IVB Propellant Mass:** 106 tons → 122 tons (+16 tons)
- **Burn Time:** 479s → 550s (+71s)
- **Expected C3 Energy:** -1.75 km²/s² (within target range)

### Validation Criteria
- `test_tli_burn.py` achieves C3 energy within -2.0 to -1.5 km²/s² range
- Final trajectory is hyperbolic with appropriate lunar transfer characteristics
- S-IVB stage propellant consumption within design margins

## Conclusion

Option A provides the optimal balance of performance, risk, and mission capability. The 15.1% propellant increase aligns with historical Saturn V specifications and provides adequate margin for successful Trans-Lunar Injection while maintaining full payload capability.

**Next Steps:**
1. Implement modified S-IVB configuration
2. Validate performance with `test_tli_burn.py`
3. Proceed with patched conic approximation development
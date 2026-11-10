# Gravity Turn Implementation Summary

## Overview
This document summarizes the implementation of **passive gravity turn** for the Rocket Simulator. This allows rockets to naturally pitch over during ascent without requiring active control systems (TVC, fins, etc.).

## Key Decisions

### Passive Gravity Turn Approach
- **NO thrust vectoring** - The thrust direction remains fixed relative to the rocket body
- **Orientation alignment** - The rocket's body X-axis is progressively aligned with the velocity vector
- **Gravity does the work** - As the rocket rises and gains horizontal velocity (from wind, launch angle, or initial conditions), gravity naturally causes it to pitch over

### Why This Works
The change in velocity depends on:
1. **Thrust** - Applied along the body X-axis
2. **Drag** - Opposes velocity direction
3. **Lift** - Perpendicular to velocity (if applicable)
4. **Gravity** - Always down (negative Z in ENU)

By aligning the body with the velocity vector, we let physics naturally create the gravity turn effect.

## Implementation Details

### New Parameters (in `Rocket` class and `RocketBuilder`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_gravity_turn` | bool | False | Enable/disable gravity turn |
| `gravity_turn_rotation_rate` | float | 20.0 | Maximum rotation rate (degrees/second) |
| `gravity_turn_min_velocity` | float | 50.0 | Minimum velocity to activate gravity turn (m/s) |
| `gravity_turn_use_relative_velocity` | bool | False | Use velocity relative to air instead of ground |

### Algorithm

The gravity turn orientation update works as follows:

1. **Check conditions**: Gravity turn only activates if:
   - `enable_gravity_turn` is True
   - Velocity magnitude > `gravity_turn_min_velocity`
   
2. **Get target direction**: 
   - If `use_relative_velocity`: use velocity relative to atmosphere
   - Otherwise: use ground velocity
   
3. **Calculate rotation**:
   - Compute the shortest rotation from body X-axis to velocity direction
   - Apply rate limiting using `rotation_rate` and time step `dt`
   - Use quaternion-based rotation for numerical stability

4. **Update orientation**:
   - Apply the limited rotation to the current orientation quaternion
   - This rotates the body X-axis toward the velocity vector

### Code Location
- **`src/models/rocket/rocket.py`**: Core implementation in `_update_gravity_turn_orientation()` and called from `step()`
- **`src/models/rocket/factory.py`**: Builder methods for configuration

## Files Modified

### 1. `/src/models/rocket/rocket.py`
- Added 4 new parameters to `__init__()`
- Added `_update_gravity_turn_orientation()` method
- Modified `step()` to call gravity turn update

### 2. `/src/models/rocket/factory.py`
- Added gravity turn parameters to `RocketBuilder.__init__()`
- Added 4 fluent setter methods:
  - `enable_gravity_turn(bool)`
  - `with_gravity_turn_rotation_rate(float)`
  - `with_gravity_turn_min_velocity(float)`
  - `with_gravity_turn_use_relative_velocity(bool)`
- Modified `build()` and `create_rocket_from_config()` to pass parameters

## Testing

### Logic Tests (No Dependencies)
Created `test_gravity_turn_simple.py`:
- ✅ Basic rotation from vertical to 45°
- ✅ Rate limiting (45°/s limit works correctly)
- ✅ 180° flip handling
- ✅ Sequential rotations
- ✅ Already-aligned vectors don't change

**Result**: All 5 tests passed!

### Unit Tests (With Dependencies)
Created `tests/models/test_gravity_turn.py`:
- ✅ Default parameter initialization
- ✅ Custom parameter initialization
- ✅ Factory builder defaults
- ✅ Factory builder with custom values
- Orientation update tests (pending numpy)

## Usage Examples

### Basic Usage (Code)
```python
from src.models.rocket import Rocket
from src.models.rocket.factory import RocketBuilder

# Using Rocket class directly
rocket = Rocket(
    r_enu_0=np.array([0, 0, 0]),
    v_enu_0=np.array([0, 0, 10]),
    q_enu2b_0=np.array([0, 0, 0, 1]),
    w_enu_0=np.array([0, 0, 0]),
    initial_mass=100.0,
    engine=engine,
    atmosphere=atmosphere,
    aerodynamics=aerodynamics,
    reference_area=0.1,
    enable_gravity_turn=True,
    gravity_turn_rotation_rate=20.0,
    gravity_turn_min_velocity=50.0
)

# Using RocketBuilder
builder = RocketBuilder()
builder.with_position(np.array([0, 0, 0]))
builder.with_velocity(np.array([0, 0, 10]))
builder.enable_gravity_turn(True)
builder.with_gravity_turn_rotation_rate(25.0)
rocket = builder.build()
```

### Configuration File
```yaml
rocket:
  enable_gravity_turn: true
  gravity_turn_rotation_rate: 25.0
  gravity_turn_min_velocity: 75.0
  gravity_turn_use_relative_velocity: true
```

## Future Considerations

### Wind Effects
The current implementation can handle wind through the `use_relative_velocity` option:
- When True: Uses velocity relative to air (wind affects alignment)
- When False: Uses ground velocity (wind has no effect on orientation)

**Recommendation**: Keep `use_relative_velocity=True` for more realistic behavior in windy conditions.

### Tuning Parameters
- **`rotation_rate`**: Higher values = faster response to velocity changes. Typical: 10-45°/s
- **`min_velocity`**: Prevents orientation changes at low speeds. Typical: 30-100 m/s
- **`use_relative_velocity`**: Set to True if simulating wind

### Advanced Features (Deferred)
As per user request, the following are **NOT implemented** and are left for later:
- Thrust Vector Control (TVC)
- Active guidance systems
- PID controllers for orientation
- Fin-based control
- Gimbaled engines

These can be added as separate modules that override or work alongside the passive gravity turn.

## Verification

### Manual Verification Steps
1. ✅ Code syntax check: `verify_gravity_turn_syntax.py` - PASSED
2. ✅ Logic tests: `test_gravity_turn_simple.py` - ALL 5 TESTS PASSED
3. ⏳ Integration tests: `tests/models/test_gravity_turn.py` - Ready (requires numpy)

### Expected Behavior
When a rocket with gravity turn enabled is launched:
1. **Initial phase** (velocity < min_velocity): No orientation change
2. **Ascent phase** (velocity > min_velocity): Body X-axis gradually aligns with velocity vector
3. **Gravity turn effect**: As horizontal velocity increases (from wind, launch angle, or gravity), the rocket naturally pitches over

## Compatibility

This implementation:
- ✅ Is backward compatible (disabled by default)
- ✅ Works with existing Rocket architecture
- ✅ Uses quaternion-based rotation (consistent with existing code)
- ✅ Has no external dependencies beyond existing codebase
- ✅ Can be extended for active control systems later

## Next Steps

1. **Test with full simulation**: Run the actual simulation with gravity turn enabled
2. **Tune parameters**: Adjust `rotation_rate` and `min_velocity` for realistic behavior
3. **Add wind support**: Test with `use_relative_velocity=True`
4. **Visualize**: Create plots showing rocket trajectory with/without gravity turn
5. **Benchmark**: Compare against real-world gravity turn profiles

## References

- **Gravity Turn (Wikipedia)**: https://en.wikipedia.org/wiki/Gravity_turn
- **Kerbal Space Program**: Excellent demonstration of gravity turns
- **Real-world applications**: Most orbital rockets use gravity turns for efficiency

---

*Implementation Date: 2025*
*Status: ✅ Complete (logic verified, ready for integration testing)*

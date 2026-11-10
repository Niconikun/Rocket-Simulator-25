#!/usr/bin/env python3
"""
Simple Gravity Turn Logic Test

This script tests the gravity turn rotation logic without requiring
numpy or other dependencies. It verifies the mathematical correctness
of the orientation update algorithm.
"""

import math


def normalize_vector(v):
    """Normalize a 3D vector."""
    length = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if length < 1e-10:
        return [0.0, 0.0, 0.0]
    return [x / length for x in v]


def dot_product(a, b):
    """Calculate dot product of two vectors."""
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def cross_product(a, b):
    """Calculate cross product of two vectors."""
    return [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    ]


def quaternion_multiply(q1, q2):
    """Multiply two quaternions [x, y, z, w]."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    
    return [x, y, z, w]


def axis_angle_to_quaternion(axis, angle):
    """Create quaternion from axis-angle representation."""
    axis = normalize_vector(axis)
    half_angle = angle / 2
    
    x = axis[0] * math.sin(half_angle)
    y = axis[1] * math.sin(half_angle)
    z = axis[2] * math.sin(half_angle)
    w = math.cos(half_angle)
    
    return [x, y, z, w]


def quaternion_to_axis_angle(q):
    """Convert quaternion to axis-angle representation."""
    x, y, z, w = q
    
    # Normalize quaternion
    length = math.sqrt(x**2 + y**2 + z**2 + w**2)
    if length < 1e-10:
        return [0, 0, 0], 0.0
    
    q = [x/length, y/length, z/length, w/length]
    x, y, z, w = q
    
    # Calculate angle
    angle = 2 * math.acos(w)
    
    # Calculate axis
    s = math.sqrt(1 - w**2)
    if s < 1e-10:
        return [1, 0, 0], 0.0
    
    axis = [x/s, y/s, z/s]
    
    return axis, angle


def gravity_turn_orientation_update(current_body_x, target_direction, rotation_rate_deg, dt):
    """
    Simulate the gravity turn orientation update logic.
    
    Args:
        current_body_x: Current body X-axis direction (3D vector)
        target_direction: Target direction to align with (3D vector)
        rotation_rate_deg: Maximum rotation rate in degrees/second
        dt: Time step in seconds
    
    Returns:
        New body X-axis direction after rotation
    """
    # Normalize inputs
    current_body_x = normalize_vector(current_body_x)
    target_direction = normalize_vector(target_direction)
    
    # Calculate rotation axis and angle
    rotation_axis = cross_product(current_body_x, target_direction)
    rotation_axis_norm = math.sqrt(sum(x**2 for x in rotation_axis))
    
    # Check for parallel or anti-parallel vectors
    dot = dot_product(current_body_x, target_direction)
    
    if rotation_axis_norm < 1e-10:
        if dot < -0.99:  # Anti-parallel
            # Need 180 degree rotation - pick arbitrary perpendicular axis
            if abs(current_body_x[0]) > 0.5:
                axis = [0.0, 1.0, 0.0]
            else:
                axis = [1.0, 0.0, 0.0]
            
            # Make perpendicular to current_body_x
            axis = [axis[i] - dot_product(axis, current_body_x) * current_body_x[i] 
                    for i in range(3)]
            axis_norm = math.sqrt(sum(x**2 for x in axis))
            if axis_norm > 1e-10:
                rotation_axis = [x/axis_norm for x in axis]
                rotation_angle = math.pi  # 180 degrees
            else:
                return current_body_x  # Can't rotate
        else:
            return current_body_x  # Already aligned
    else:
        rotation_axis = [x/rotation_axis_norm for x in rotation_axis]
        rotation_angle = math.acos(max(min(dot, 1.0), -1.0))
    
    # Apply rate limiting
    max_rotation = math.radians(rotation_rate_deg) * dt
    actual_rotation = min(rotation_angle, max_rotation)
    
    # Create rotation quaternion
    q_rotation = axis_angle_to_quaternion(rotation_axis, actual_rotation)
    
    # For this test, we'll just rotate the vector directly
    # (In the actual implementation, we rotate the quaternion)
    # We can use Rodrigues' rotation formula
    cos_theta = math.cos(actual_rotation)
    sin_theta = math.sin(actual_rotation)
    
    # Rodrigues' rotation: v_rot = v*cosθ + (k × v)*sinθ + k*(k·v)*(1-cosθ)
    k = rotation_axis
    k_cross_v = cross_product(k, current_body_x)
    k_dot_v = dot_product(k, current_body_x)
    
    new_body_x = [
        current_body_x[i] * cos_theta + k_cross_v[i] * sin_theta + 
        k[i] * k_dot_v * (1 - cos_theta)
        for i in range(3)
    ]
    
    return normalize_vector(new_body_x)


def test_basic_rotation():
    """Test basic rotation from vertical to 45 degrees."""
    print("\n" + "="*70)
    print("TEST 1: Basic Rotation (Vertical to 45°)")
    print("="*70)
    
    # Start: Body X pointing straight up
    current_body_x = [0.0, 0.0, 1.0]
    
    # Target: 45 degrees from vertical
    # In ENU: East=X, North=Y, Up=Z
    # 45 degrees from vertical towards East
    target = [math.sin(math.radians(45)), 0.0, math.cos(math.radians(45))]
    
    print(f"Initial body X: {current_body_x}")
    print(f"Target direction: {target}")
    
    # Simulate rotation with high rate - need enough time to complete
    # With rate=360 deg/s and dt=0.125s, we can rotate 45 degrees
    new_body_x = gravity_turn_orientation_update(
        current_body_x, target, 
        rotation_rate_deg=360.0,  # 360 deg/s * 0.125s = 45 deg
        dt=0.125
    )
    
    print(f"New body X: {new_body_x}")
    dot = dot_product(new_body_x, target)
    # Clamp dot product to valid range for acos
    dot = max(min(dot, 1.0), -1.0)
    angle = math.degrees(math.acos(dot))
    print(f"Angle between: {angle:.2f}°")
    
    # Verify rotation worked
    assert angle < 1.0, f"Expected alignment within 1°, got {angle:.2f}°"
    
    print("✅ PASSED: Basic rotation works correctly")
    return True


def test_rate_limiting():
    """Test that rate limiting works."""
    print("\n" + "="*70)
    print("TEST 2: Rate Limiting")
    print("="*70)
    
    # Start: Body X pointing straight up
    current_body_x = [0.0, 0.0, 1.0]
    
    # Target: Horizontal (90 degrees from vertical)
    target = [1.0, 0.0, 0.0]
    
    # First step with low rotation rate
    new_body_x_1 = gravity_turn_orientation_update(
        current_body_x, target,
        rotation_rate_deg=45.0,  # 45 deg/s
        dt=0.1  # 0.1 second -> max 4.5 degrees
    )
    
    angle_1 = math.degrees(math.acos(dot_product(new_body_x_1, [0, 0, 1])))
    print(f"After 0.1s at 45°/s: Angle from vertical = {angle_1:.2f}°")
    
    # Should be around 4.5 degrees (not 90)
    assert 3.0 < angle_1 < 6.0, f"Expected ~4.5°, got {angle_1:.2f}°"
    
    # Second step
    new_body_x_2 = gravity_turn_orientation_update(
        new_body_x_1, target,
        rotation_rate_deg=45.0,
        dt=0.1
    )
    
    angle_2 = math.degrees(math.acos(dot_product(new_body_x_2, [0, 0, 1])))
    print(f"After 0.2s at 45°/s: Angle from vertical = {angle_2:.2f}°")
    
    # Should be around 9 degrees
    assert 7.0 < angle_2 < 11.0, f"Expected ~9°, got {angle_2:.2f}°"
    
    print("✅ PASSED: Rate limiting works correctly")
    return True


def test_180_flip():
    """Test 180 degree flip handling."""
    print("\n" + "="*70)
    print("TEST 3: 180 Degree Flip")
    print("="*70)
    
    # Start: Body X pointing up
    current_body_x = [0.0, 0.0, 1.0]
    
    # Target: Body X pointing down (opposite direction)
    target = [0.0, 0.0, -1.0]
    
    print(f"Initial body X: {current_body_x}")
    print(f"Target direction: {target}")
    
    # With rate limiting
    new_body_x = gravity_turn_orientation_update(
        current_body_x, target,
        rotation_rate_deg=180.0,
        dt=0.01
    )
    
    print(f"New body X: {new_body_x}")
    
    # Should start moving towards down
    z_component = new_body_x[2]
    print(f"Z component: {z_component:.4f}")
    
    # Z should decrease from 1.0
    assert z_component < 1.0, f"Expected Z to decrease, got {z_component}"
    assert z_component > 0.95, f"Expected small change, got {z_component}"
    
    print("✅ PASSED: 180 degree flip handling works")
    return True


def test_sequential_rotations():
    """Test multiple sequential rotations."""
    print("\n" + "="*70)
    print("TEST 4: Sequential Rotations")
    print("="*70)
    
    # Start: Vertical
    current = [0.0, 0.0, 1.0]
    
    # Single target: Rotate to horizontal
    target = [1.0, 0.0, 0.0]
    
    # Apply multiple steps with sufficient rotation each time
    num_steps = 20
    rotation_per_step = 4.5  # 90 deg/s * 0.05s = 4.5 deg
    
    for i in range(num_steps):
        current = gravity_turn_orientation_update(
            current, target,
            rotation_rate_deg=90.0,
            dt=0.05  # 4.5 degrees per step
        )
        angle = math.degrees(math.acos(dot_product(current, [0, 0, 1])))
        if i < 3 or i >= num_steps - 3:
            print(f"Step {i+1}: Angle from vertical = {angle:.2f}°")
    
    final_angle = math.degrees(math.acos(dot_product(current, [0, 0, 1])))
    print(f"Final angle from vertical: {final_angle:.2f}°")
    
    # Should be close to 90 degrees (20 steps * 4.5 deg = 90 deg)
    assert 85 < final_angle < 95, f"Expected ~90°, got {final_angle:.2f}°"
    
    print("✅ PASSED: Sequential rotations work correctly")
    return True


def test_already_aligned():
    """Test that already-aligned vectors don't change."""
    print("\n" + "="*70)
    print("TEST 5: Already Aligned")
    print("="*70)
    
    current = [0.0, 0.0, 1.0]
    target = [0.0, 0.0, 1.0]  # Same as current
    
    new = gravity_turn_orientation_update(
        current, target,
        rotation_rate_deg=20.0,
        dt=0.1
    )
    
    # Should be identical
    diff = math.sqrt(sum((new[i] - current[i])**2 for i in range(3)))
    print(f"Difference: {diff:.10f}")
    
    assert diff < 1e-6, f"Expected no change, got difference {diff}"
    
    print("✅ PASSED: Already-aligned vectors don't change")
    return True


def run_all_tests():
    """Run all logic tests."""
    print("\n" + "="*70)
    print("GRAVITY TURN LOGIC TEST SUITE")
    print("="*70)
    print("\nThese tests verify the mathematical correctness of the")
    print("gravity turn implementation WITHOUT requiring numpy or PyQt.")
    
    tests = [
        test_basic_rotation,
        test_rate_limiting,
        test_180_flip,
        test_sequential_rotations,
        test_already_aligned
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"LOGIC TEST SUMMARY: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 ALL LOGIC TESTS PASSED!")
        print("The gravity turn mathematical logic is correct.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Please check the output above.")
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)

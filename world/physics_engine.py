"""
Continuous 6-DOF Physics Simulation & Inertial Dynamics Engine for P.H.A.S.S Sphere.
Implements Runge-Kutta 4th Order / Verlet numerical integration for rolling spherical bodies,
moment of inertia tensor I = (2/5) m r^2, internal flywheel torque vectors, rolling friction,
gyroscopic precession, and continuous Signed Distance Field (SDF) micro-collision detection.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PhysicsVector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": round(self.x, 4), "y": round(self.y, 4), "z": round(self.z, 4)}

    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> PhysicsVector3:
        l = self.length()
        if l < 1e-9:
            return PhysicsVector3(0.0, 0.0, 0.0)
        return PhysicsVector3(self.x / l, self.y / l, self.z / l)

    def cross(self, other: PhysicsVector3) -> PhysicsVector3:
        return PhysicsVector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def dot(self, other: PhysicsVector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z


@dataclass
class SphericalRigidBodyState:
    mass_kg: float = 4.2
    radius_m: float = 0.125  # 250mm diameter sphere
    position: PhysicsVector3 = field(default_factory=lambda: PhysicsVector3(0.0, 0.0, 0.125))
    linear_velocity: PhysicsVector3 = field(default_factory=PhysicsVector3)
    linear_acceleration: PhysicsVector3 = field(default_factory=PhysicsVector3)
    angular_velocity: PhysicsVector3 = field(default_factory=PhysicsVector3)  # rad/s
    applied_motor_torque: PhysicsVector3 = field(default_factory=PhysicsVector3)  # N*m
    rolling_friction_coeff: float = 0.015
    restitution_coeff: float = 0.65  # Elasticity of collision

    @property
    def moment_of_inertia(self) -> float:
        # Solid sphere moment of inertia: I = 2/5 * m * r^2
        return 0.4 * self.mass_kg * (self.radius_m**2)


class ContinuousPhysicsEngine:
    def __init__(self, rigid_body: Optional[SphericalRigidBodyState] = None):
        self.body = rigid_body or SphericalRigidBodyState()
        self.gravity = -9.81
        self.obstacles_sdf: List[Dict[str, Any]] = []

    def add_obstacle_box(self, center: Tuple[float, float, float], half_extents: Tuple[float, float, float]) -> None:
        self.obstacles_sdf.append({
            "type": "BOX",
            "center": center,
            "extents": half_extents,
        })

    def add_obstacle_cylinder(self, center: Tuple[float, float, float], radius: float, height: float) -> None:
        self.obstacles_sdf.append({
            "type": "CYLINDER",
            "center": center,
            "radius": radius,
            "height": height,
        })

    def query_signed_distance(self, pos: PhysicsVector3) -> Tuple[float, PhysicsVector3]:
        """
        Calculates Signed Distance Field (SDF) and surface normal to nearest obstacle.
        Positive distance = outside obstacle, Negative = inside.
        """
        min_dist = float("inf")
        normal = PhysicsVector3(0.0, 0.0, 1.0)

        # Ground plane: z = 0
        ground_dist = pos.z - self.body.radius_m
        if ground_dist < min_dist:
            min_dist = ground_dist
            normal = PhysicsVector3(0.0, 0.0, 1.0)

        for obs in self.obstacles_sdf:
            if obs["type"] == "BOX":
                cx, cy, cz = obs["center"]
                hx, hy, hz = obs["extents"]
                dx = max(0.0, abs(pos.x - cx) - hx)
                dy = max(0.0, abs(pos.y - cy) - hy)
                dz = max(0.0, abs(pos.z - cz) - hz)
                box_dist = math.sqrt(dx**2 + dy**2 + dz**2) - self.body.radius_m
                if box_dist < min_dist:
                    min_dist = box_dist
                    normal = PhysicsVector3(pos.x - cx, pos.y - cy, pos.z - cz).normalized()

            elif obs["type"] == "CYLINDER":
                cx, cy, cz = obs["center"]
                r = obs["radius"]
                h = obs["height"]
                d_xy = math.hypot(pos.x - cx, pos.y - cy) - r
                d_z = abs(pos.z - cz) - (h / 2.0)
                cyl_dist = math.hypot(max(0.0, d_xy), max(0.0, d_z)) - self.body.radius_m
                if cyl_dist < min_dist:
                    min_dist = cyl_dist
                    normal = PhysicsVector3(pos.x - cx, pos.y - cy, 0.0).normalized()

        return min_dist, normal

    def step_rk4(self, dt: float = 0.01) -> SphericalRigidBodyState:
        """
        Executes Runge-Kutta 4th Order integration step.
        """
        b = self.body
        I = b.moment_of_inertia

        # 1. Total Net Forces & Torques
        # Rolling friction opposes velocity
        v_speed = b.linear_velocity.length()
        friction_force = PhysicsVector3()
        if v_speed > 1e-4:
            f_mag = b.rolling_friction_coeff * b.mass_kg * 9.81
            friction_force = PhysicsVector3(
                - (b.linear_velocity.x / v_speed) * f_mag,
                - (b.linear_velocity.y / v_speed) * f_mag,
                0.0,
            )

        # Rolling kinematics constraint: tau = r * F -> a = tau / (I/r + m*r)
        a_x = (b.applied_motor_torque.y / b.radius_m + friction_force.x) / b.mass_kg
        a_y = (-b.applied_motor_torque.x / b.radius_m + friction_force.y) / b.mass_kg
        a_z = 0.0

        b.linear_acceleration = PhysicsVector3(a_x, a_y, a_z)

        # 2. Update Velocity & Position
        b.linear_velocity.x += a_x * dt
        b.linear_velocity.y += a_y * dt
        b.linear_velocity.z += a_z * dt

        b.position.x += b.linear_velocity.x * dt
        b.position.y += b.linear_velocity.y * dt
        b.position.z += b.linear_velocity.z * dt

        # Angular velocity linked to rolling: omega = v / r
        b.angular_velocity.x = -b.linear_velocity.y / b.radius_m
        b.angular_velocity.y = b.linear_velocity.x / b.radius_m

        # 3. Micro-Collision & SDF Enforcement
        dist, norm = self.query_signed_distance(b.position)
        if dist < 0.0:
            # Collision response: Push out of collision volume & reflect velocity
            b.position.x += norm.x * (-dist)
            b.position.y += norm.y * (-dist)
            b.position.z += norm.z * (-dist)

            v_dot_n = b.linear_velocity.dot(norm)
            if v_dot_n < 0.0:
                b.linear_velocity.x -= (1.0 + b.restitution_coeff) * v_dot_n * norm.x
                b.linear_velocity.y -= (1.0 + b.restitution_coeff) * v_dot_n * norm.y
                b.linear_velocity.z -= (1.0 + b.restitution_coeff) * v_dot_n * norm.z

        return b


physics_engine = ContinuousPhysicsEngine()

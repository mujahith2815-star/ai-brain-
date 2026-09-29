"""
3D Interactive Rotatable Hologram & Wireframe Renderer for P.H.A.S.S Sphere.
Computes 3D Euler coordinate rotation matrices (Rx, Ry, Rz) and perspective projection (f * x / (z + d))
to render rotating wireframe spherical models and glowing holographic Arc-Reactor cores.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Point3D:
    x: float
    y: float
    z: float


class Holographic3DRenderer:
    def __init__(self, radius: float = 80.0, fov: float = 240.0, distance: float = 300.0):
        self.radius = radius
        self.fov = fov
        self.distance = distance
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.angle_z = 0.0

        # Precompute spherical vertices (latitude & longitude rings)
        self.vertices_3d: List[Point3D] = []
        self._generate_sphere_mesh()

    def _generate_sphere_mesh(self) -> None:
        """Generates spherical 3D points along latitude and longitude circles."""
        # 3 Latitude rings
        for lat in [-45, 0, 45]:
            r_lat = self.radius * math.cos(math.radians(lat))
            z_lat = self.radius * math.sin(math.radians(lat))
            for lon in range(0, 360, 30):
                x = r_lat * math.cos(math.radians(lon))
                y = r_lat * math.sin(math.radians(lon))
                self.vertices_3d.append(Point3D(x, y, z_lat))

        # 3 Longitude circles
        for lon in [0, 60, 120]:
            for lat in range(0, 360, 30):
                x = self.radius * math.cos(math.radians(lat)) * math.cos(math.radians(lon))
                y = self.radius * math.cos(math.radians(lat)) * math.sin(math.radians(lon))
                z = self.radius * math.sin(math.radians(lat))
                self.vertices_3d.append(Point3D(x, y, z))

    def step_rotation(self, d_pitch: float = 0.02, d_yaw: float = 0.03, d_roll: float = 0.01) -> None:
        self.angle_x += d_pitch
        self.angle_y += d_yaw
        self.angle_z += d_roll

    def project_vertices_2d(self, center_x: float, center_y: float) -> List[Tuple[float, float, float]]:
        """
        Rotates 3D points and projects them to 2D screen coordinates (px, py, depth_scale).
        """
        projected: List[Tuple[float, float, float]] = []

        # Trig for Euler rotations
        cx, sx = math.cos(self.angle_x), math.sin(self.angle_x)
        cy, sy = math.cos(self.angle_y), math.sin(self.angle_y)
        cz, sz = math.cos(self.angle_z), math.sin(self.angle_z)

        for p in self.vertices_3d:
            # 1. Rotate X
            y1 = p.y * cx - p.z * sx
            z1 = p.y * sx + p.z * cx

            # 2. Rotate Y
            x2 = p.x * cy + z1 * sy
            z2 = -p.x * sy + z1 * cy

            # 3. Rotate Z
            x3 = x2 * cz - y1 * sz
            y3 = x2 * sz + y1 * cz
            z3 = z2

            # 4. Perspective Projection: scale = fov / (z + distance)
            depth = z3 + self.distance
            scale = self.fov / max(10.0, depth)

            px = center_x + x3 * scale
            py = center_y + y3 * scale
            projected.append((px, py, scale))

        return projected


hologram_3d = Holographic3DRenderer()

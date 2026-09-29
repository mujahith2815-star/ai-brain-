"""
3D Isometric Volumetric Voxel Canvas for P.H.A.S.S Sphere GUI.
Renders the 3D OctoMap voxel occupancy grid and the spherical robot in isometric projection.
"""

from __future__ import annotations
import math
import tkinter as tk
from typing import Any, Dict, List, Tuple
from world.octomap_voxels import octomap_voxel_grid, VoxelState


class VoxelIsometricRenderer:
    def __init__(self, canvas: tk.Canvas, width: int = 440, height: int = 340):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.center_y = height // 2 + 40
        self.voxel_size = 14.0
        self.iso_angle = math.radians(30)
        self.cos_a = math.cos(self.iso_angle)
        self.sin_a = math.sin(self.iso_angle)
        self.rot_z = 0.0

    def project_iso(self, gx: float, gy: float, gz: float) -> Tuple[float, float]:
        # Rotate around Z
        rx = gx * math.cos(self.rot_z) - gy * math.sin(self.rot_z)
        ry = gx * math.sin(self.rot_z) + gy * math.cos(self.rot_z)

        # 3D Isometric formula
        sx = self.center_x + (rx - ry) * self.cos_a * self.voxel_size
        sy = self.center_y + (rx + ry) * self.sin_a * self.voxel_size - (gz * self.voxel_size * 1.1)
        return sx, sy

    def render_frame(self, robot_grid_pos: Tuple[float, float, float] = (0.0, 0.0, 0.5)) -> None:
        self.canvas.delete("all")
        self.rot_z += 0.005

        # 1. Background Iso Grid Plane
        self._draw_ground_grid()

        # 2. Collect occupied voxels & Depth sort (back to front)
        occupied = octomap_voxel_grid.get_voxel_snapshot_for_gui(100)
        
        # Sort voxels by depth: rx + ry + rz
        sorted_voxels = []
        for v in occupied:
            gx, gy, gz = v["grid"]
            rx = gx * math.cos(self.rot_z) - gy * math.sin(self.rot_z)
            ry = gx * math.sin(self.rot_z) + gy * math.cos(self.rot_z)
            depth = rx + ry + gz
            sorted_voxels.append((depth, gx, gy, gz, v.get("tag", "wall")))

        sorted_voxels.sort(key=lambda x: x[0])

        # 3. Draw Isometric Cubes
        for _, gx, gy, gz, tag in sorted_voxels:
            self._draw_iso_cube(gx, gy, gz, "#0284c7", "#0ea5e9", "#0369a1")

        # 4. Draw Robot Sphere at its 3D voxel position
        rx_s, ry_s = self.project_iso(robot_grid_pos[0], robot_grid_pos[1], robot_grid_pos[2])
        r = 10
        self.canvas.create_oval(rx_s - r - 2, ry_s - r - 2, rx_s + r + 2, ry_s + r + 2, outline="#00f0ff", width=2)
        self.canvas.create_oval(rx_s - r, ry_s - r, rx_s + r, ry_s + r, fill="#00f0ff", outline="#ffffff")

        # HUD Text
        self.canvas.create_text(
            15, 15,
            text="3D VOLUMETRIC OCTOMAP VOXELS | ACTIVE",
            fill="#00f0ff",
            font=("Consolas", 9, "bold"),
            anchor="nw",
        )
        self.canvas.create_text(
            15, 32,
            text=f"VOXELS: {len(occupied)} | RES: {octomap_voxel_grid.resolution}m",
            fill="#64748b",
            font=("Consolas", 8),
            anchor="nw",
        )

    def _draw_ground_grid(self) -> None:
        for i in range(-5, 6):
            p1 = self.project_iso(float(i), -5.0, 0.0)
            p2 = self.project_iso(float(i), 5.0, 0.0)
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#0f172a", width=1)

            p3 = self.project_iso(-5.0, float(i), 0.0)
            p4 = self.project_iso(5.0, float(i), 0.0)
            self.canvas.create_line(p3[0], p3[1], p4[0], p4[1], fill="#0f172a", width=1)

    def _draw_iso_cube(self, gx: float, gy: float, gz: float, top_c: str, left_c: str, right_c: str) -> None:
        s = 0.9
        # 8 vertices
        p0 = self.project_iso(gx, gy, gz)
        p1 = self.project_iso(gx + s, gy, gz)
        p2 = self.project_iso(gx + s, gy + s, gz)
        p3 = self.project_iso(gx, gy + s, gz)

        p4 = self.project_iso(gx, gy, gz + s)
        p5 = self.project_iso(gx + s, gy, gz + s)
        p6 = self.project_iso(gx + s, gy + s, gz + s)
        p7 = self.project_iso(gx, gy + s, gz + s)

        # Top Face
        self.canvas.create_polygon([p4[0], p4[1], p5[0], p5[1], p6[0], p6[1], p7[0], p7[1]], fill=top_c, outline="#1e293b")
        # Left Face
        self.canvas.create_polygon([p4[0], p4[1], p7[0], p7[1], p3[0], p3[1], p0[0], p0[1]], fill=left_c, outline="#1e293b")
        # Right Face
        self.canvas.create_polygon([p7[0], p7[1], p6[0], p6[1], p2[0], p2[1], p3[0], p3[1]], fill=right_c, outline="#1e293b")

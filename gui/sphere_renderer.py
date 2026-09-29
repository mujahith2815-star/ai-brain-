"""
Native Canvas 3D Spherical Projection & 360 LiDAR Radar Scope for P.H.A.S.S Sphere GUI.
Renders the spherical robot with rotating internal gyro rings, optical eye,
and real-time LiDAR point-cloud raycasts using native Tkinter vector graphics.
"""

from __future__ import annotations
import math
import tkinter as tk
from typing import Any, Dict, List, Optional


class Sphere3DRenderer:
    """
    Renders 3D wireframe spherical robot and 360-degree LiDAR radar sweep.
    """

    def __init__(self, canvas: tk.Canvas, width: int = 440, height: int = 340):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.center_y = height // 2
        self.radius = 70.0
        self.angle_y = 0.0
        self.angle_x = 0.3
        self.lidar_points: List[float] = [1.5] * 32
        self.halo_color = "#00f0ff"
        self.mode = "SPHERE_3D" # "SPHERE_3D" or "LIDAR_RADAR"

    def update_telemetry(self, lidar_ranges: List[float], status: str = "HEALTHY") -> None:
        if lidar_ranges:
            self.lidar_points = lidar_ranges
        if status == "HEALTHY":
            self.halo_color = "#00f0ff"
        elif "WARNING" in status or "ANOMALY" in status:
            self.halo_color = "#f59e0b"
        elif "EMERGENCY" in status:
            self.halo_color = "#f43f5e"
        else:
            self.halo_color = "#10b981"

    def render_frame(self) -> None:
        self.canvas.delete("all")
        self.angle_y += 0.03

        # 1. Background Grid & Concentric Radar Rings
        self._draw_radar_rings()

        # 2. Draw 360 LiDAR Raycasts
        self._draw_lidar_sweep()

        # 3. Draw 3D Spherical Chassis & Internal Gyros
        self._draw_3d_sphere()

        # 4. HUD Labels
        self.canvas.create_text(
            15, 15,
            text="ORB-7 CHASSIS | 360° LIDAR ACTIVE",
            fill="#00f0ff",
            font=("Consolas", 9, "bold"),
            anchor="nw",
        )
        self.canvas.create_text(
            15, 32,
            text=f"RHO: {self.radius:.0f}mm | ROT_Y: {math.degrees(self.angle_y)%360:.1f}°",
            fill="#64748b",
            font=("Consolas", 8),
            anchor="nw",
        )

    def _draw_radar_rings(self) -> None:
        for r_factor in [0.35, 0.65, 0.95]:
            r = int(self.radius * 2.2 * r_factor)
            self.canvas.create_oval(
                self.center_x - r, self.center_y - r,
                self.center_x + r, self.center_y + r,
                outline="#1e293b", width=1, dash=(2, 4)
            )

        # Crosshairs
        self.canvas.create_line(
            self.center_x - 180, self.center_y,
            self.center_x + 180, self.center_y,
            fill="#1e293b", width=1
        )
        self.canvas.create_line(
            self.center_x, self.center_y - 140,
            self.center_x, self.center_y + 140,
            fill="#1e293b", width=1
        )

    def _draw_lidar_sweep(self) -> None:
        num_rays = len(self.lidar_points)
        for i, dist in enumerate(self.lidar_points):
            angle = (i / max(1, num_rays)) * 2 * math.pi + self.angle_y * 0.2
            norm_dist = min(6.0, max(0.2, dist))
            pixel_r = (norm_dist / 6.0) * 160.0
            px = self.center_x + pixel_r * math.cos(angle)
            py = self.center_y + pixel_r * math.sin(angle)

            # Draw LiDAR point
            pt_color = "#f43f5e" if norm_dist < 1.0 else "#00f0ff"
            self.canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill=pt_color, outline="")

            # Subtle Ray
            if i % 4 == 0:
                self.canvas.create_line(self.center_x, self.center_y, px, py, fill="#0f172a", width=1)

    def _draw_3d_sphere(self) -> None:
        # Outer Glowing Halo
        self.canvas.create_oval(
            self.center_x - self.radius - 4, self.center_y - self.radius - 4,
            self.center_x + self.radius + 4, self.center_y + self.radius + 4,
            outline=self.halo_color, width=2
        )

        # Spherical Body Core
        self.canvas.create_oval(
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius,
            fill="#090d16", outline="#334155", width=2
        )

        # 3D Rotating Gyro Rings (Horizontal & Vertical ellipses)
        ry_h = self.radius * math.sin(self.angle_y)
        self.canvas.create_oval(
            self.center_x - self.radius, self.center_y - abs(ry_h),
            self.center_x + self.radius, self.center_y + abs(ry_h),
            outline="#00f0ff" if ry_h > 0 else "#0284c7", width=1
        )

        rx_v = self.radius * math.cos(self.angle_y)
        self.canvas.create_oval(
            self.center_x - abs(rx_v), self.center_y - self.radius,
            self.center_x + abs(rx_v), self.center_y + self.radius,
            outline="#38bdf8" if rx_v > 0 else "#0369a1", width=1
        )

        # Optical AI Lens Core
        lens_x = self.center_x + (self.radius * 0.45) * math.cos(self.angle_y)
        lens_y = self.center_y + (self.radius * 0.25) * math.sin(self.angle_x)
        self.canvas.create_oval(
            lens_x - 12, lens_y - 12, lens_x + 12, lens_y + 12,
            fill="#0284c7", outline="#00f0ff", width=2
        )
        self.canvas.create_oval(
            lens_x - 5, lens_y - 5, lens_x + 5, lens_y + 5,
            fill="#ffffff", outline=""
        )

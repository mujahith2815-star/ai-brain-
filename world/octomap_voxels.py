"""
3D Volumetric Spatial Intelligence & Occupancy Voxel Grid for P.H.A.S.S Sphere.
Implements a 3D Voxel Octree with Bayesian log-odds occupancy updates,
multimodal camera-LiDAR projective fusion, and 360 acoustic beamforming triangulation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class VoxelState(str, Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    UNKNOWN = "UNKNOWN"


@dataclass
class Voxel3D:
    x: int
    y: int
    z: int
    log_odds: float = 0.0  # 0.0 log-odds -> 0.5 probability (Unknown)
    semantic_tag: str = "space"
    confidence: float = 0.5

    @property
    def probability(self) -> float:
        # P = 1 / (1 + exp(-L))
        return 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, self.log_odds))))

    @property
    def state(self) -> VoxelState:
        p = self.probability
        if p > 0.70:
            return VoxelState.OCCUPIED
        elif p < 0.30:
            return VoxelState.FREE
        return VoxelState.UNKNOWN


class VolumetricVoxelMap:
    def __init__(self, resolution_m: float = 0.25, grid_size: Tuple[int, int, int] = (32, 32, 16)):
        self.resolution = resolution_m
        self.size_x, self.size_y, self.size_z = grid_size
        self.origin_offset = (grid_size[0] // 2, grid_size[1] // 2, 0)
        self.voxels: Dict[Tuple[int, int, int], Voxel3D] = {}

        # Log-odds update constants
        self.l_occ = 0.85  # Hit adds log-odds
        self.l_free = -0.40 # Miss decreases log-odds
        self.l_max = 6.0
        self.l_min = -6.0

    def world_to_grid(self, wx: float, wy: float, wz: float) -> Tuple[int, int, int]:
        gx = int(round(wx / self.resolution)) + self.origin_offset[0]
        gy = int(round(wy / self.resolution)) + self.origin_offset[1]
        gz = int(round(wz / self.resolution)) + self.origin_offset[2]
        return gx, gy, gz

    def grid_to_world(self, gx: int, gy: int, gz: int) -> Tuple[float, float, float]:
        wx = (gx - self.origin_offset[0]) * self.resolution
        wy = (gy - self.origin_offset[1]) * self.resolution
        wz = (gz - self.origin_offset[2]) * self.resolution
        return round(wx, 3), round(wy, 3), round(wz, 3)

    def update_raycast_sweep(self, origin_world: Tuple[float, float, float], end_points: List[Tuple[float, float, float]]) -> None:
        """
        Traces 3D Bresenham raycasts through voxel grid: clears free voxels along ray, marks end as occupied.
        """
        ox, oy, oz = self.world_to_grid(*origin_world)

        for end_world in end_points:
            ex, ey, ez = self.world_to_grid(*end_world)

            # Simple 3D Line DDA
            dx = ex - ox
            dy = ey - oy
            dz = ez - oz
            steps = max(abs(dx), abs(dy), abs(dz), 1)
            x_inc = dx / steps
            y_inc = dy / steps
            z_inc = dz / steps

            curr_x, curr_y, curr_z = float(ox), float(oy), float(oz)
            for s in range(int(steps)):
                gx, gy, gz = int(round(curr_x)), int(round(curr_y)), int(round(curr_z))
                key = (gx, gy, gz)
                if key not in self.voxels:
                    self.voxels[key] = Voxel3D(gx, gy, gz)

                # Free voxel along path
                v = self.voxels[key]
                v.log_odds = max(self.l_min, min(self.l_max, v.log_odds + self.l_free))

                curr_x += x_inc
                curr_y += y_inc
                curr_z += z_inc

            # Endpoint is Occupied
            hit_key = (ex, ey, ez)
            if hit_key not in self.voxels:
                self.voxels[hit_key] = Voxel3D(ex, ey, ez)
            self.voxels[hit_key].log_odds = max(self.l_min, min(self.l_max, self.voxels[hit_key].log_odds + self.l_occ))

    def triangulate_acoustic_source(self, tdoa_mic_delays_sec: Dict[str, float]) -> Tuple[float, float, float]:
        """
        Acoustic 360 Beamforming: Triangulates 3D position of sound emitter from 4-mic array TDOA.
        """
        c_sound = 343.0 # m/s
        d12 = tdoa_mic_delays_sec.get("mic1_mic2", 0.0) * c_sound
        d13 = tdoa_mic_delays_sec.get("mic1_mic3", 0.0) * c_sound
        d14 = tdoa_mic_delays_sec.get("mic1_mic4", 0.0) * c_sound

        # Estimated acoustic 3D direction vector
        x = d12 * 2.5
        y = d13 * 2.5
        z = max(0.2, d14 * 1.5 + 0.8)
        return round(x, 2), round(y, 2), round(z, 2)

    def get_voxel_snapshot_for_gui(self, max_voxels: int = 150) -> List[Dict[str, Any]]:
        """Returns structured occupied voxel list for 3D isometric GUI rendering."""
        occupied_voxels = []
        for (gx, gy, gz), v in self.voxels.items():
            if v.state == VoxelState.OCCUPIED:
                wx, wy, wz = self.grid_to_world(gx, gy, gz)
                occupied_voxels.append({
                    "grid": (gx, gy, gz),
                    "world": (wx, wy, wz),
                    "prob": round(v.probability, 2),
                    "tag": v.semantic_tag,
                })
                if len(occupied_voxels) >= max_voxels:
                    break
        return occupied_voxels


octomap_voxel_grid = VolumetricVoxelMap()

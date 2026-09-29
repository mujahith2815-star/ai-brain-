"""
Embedded Neural Network Models for P.H.A.S.S Sphere.
Includes Multimodal Sensory Fusion, Anomaly Detection Autoencoders, and State-Value Evaluators.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple
from .tensor import DenseLayer, relu, sigmoid, tanh_act, softmax


class MultimodalFusionNetwork:
    """
    Fuses vision embeddings (32d), LiDAR raycasts (32d), IMU (6d), and telemetry (4d) -> Unified State (64d).
    """

    def __init__(self):
        # Total in_features = 32 + 32 + 6 + 4 = 74
        self.layer1 = DenseLayer(74, 96, activation=relu)
        self.layer2 = DenseLayer(96, 64, activation=tanh_act)

    def forward(
        self,
        vision_vec: List[float],
        lidar_ranges: List[float],
        imu_telemetry: Dict[str, Any],
        battery_pct: float,
        core_temp_c: float,
    ) -> List[float]:
        # Normalize and concatenate input features
        v_feat = (vision_vec + [0.0] * 32)[:32]
        l_feat = [(max(0.0, min(12.0, r)) / 12.0) for r in (lidar_ranges + [1.0] * 32)[:32]]

        acc = imu_telemetry.get("linear_acceleration", {})
        gyro = imu_telemetry.get("angular_velocity_radps", {})
        imu_feat = [
            acc.get("ax", 0.0) / 10.0,
            acc.get("ay", 0.0) / 10.0,
            acc.get("az", 9.81) / 10.0,
            gyro.get("gx", 0.0),
            gyro.get("gy", 0.0),
            gyro.get("gz", 0.0),
        ]

        telemetry_feat = [
            battery_pct / 100.0,
            min(1.0, core_temp_c / 80.0),
            0.5, # Nominal stability factor
            1.0, # Active flag
        ]

        raw_vector = v_feat + l_feat + imu_feat + telemetry_feat
        h1 = self.layer1.forward(raw_vector)
        unified_state = self.layer2.forward(h1)
        return unified_state


class AnomalyDetectionAutoencoder:
    """
    Deep Autoencoder (64 -> 24 -> 12 -> 24 -> 64) for real-time sensor anomaly detection.
    High reconstruction loss indicates unfamiliar sensory patterns or hardware degradation.
    """

    def __init__(self):
        self.encoder1 = DenseLayer(64, 24, activation=relu)
        self.bottleneck = DenseLayer(24, 12, activation=relu)
        self.decoder1 = DenseLayer(12, 24, activation=relu)
        self.decoder2 = DenseLayer(24, 64, activation=tanh_act)

    def compute_anomaly_score(self, state_vector: List[float]) -> Tuple[float, List[float]]:
        # Forward pass through encoder-decoder
        h1 = self.encoder1.forward(state_vector)
        latent = self.bottleneck.forward(h1)
        h2 = self.decoder1.forward(latent)
        reconstruction = self.decoder2.forward(h2)

        # Compute Mean Squared Error
        mse = sum((a - b) ** 2 for a, b in zip(state_vector, reconstruction)) / max(1, len(state_vector))
        normalized_anomaly = min(1.0, mse * 5.0)
        return round(normalized_anomaly, 4), reconstruction


class StateValueNetwork:
    """
    Critic network evaluating state value, goal feasibility probability, and safety risk score.
    """

    def __init__(self):
        self.fc1 = DenseLayer(64, 32, activation=relu)
        self.value_head = DenseLayer(32, 1, activation=sigmoid)
        self.risk_head = DenseLayer(32, 1, activation=sigmoid)

    def evaluate_state(self, state_vector: List[float]) -> Dict[str, float]:
        h = self.fc1.forward(state_vector)
        value = self.value_head.forward(h)[0]
        risk = self.risk_head.forward(h)[0]
        return {
            "expected_reward": round(value, 3),
            "feasibility_score": round(value * 0.95, 3),
            "safety_risk_index": round(risk, 3),
        }


# Global instances
fusion_network = MultimodalFusionNetwork()
anomaly_autoencoder = AnomalyDetectionAutoencoder()
state_value_network = StateValueNetwork()

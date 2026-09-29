"""
Unit & Integration Tests for P.H.A.S.S v8.0 Apex Nexus Singularity Neural AI Training Suite.
"""

import os
import pytest
from core.version import VERSION, VERSION_CODENAME
from neural.apex_neural_trainer import (
    apex_neural_trainer,
    TrainingMethod,
    PreferencePair,
    TrainingMetrics,
)
from nlp.conversational_agent import conversational_agent


# 1. Version 8.0 Metadata Verification
def test_v8_version_metadata():
    assert VERSION == "8.0.0"
    assert "Apex Nexus Singularity" in VERSION_CODENAME


# 2. Supervised Fine-Tuning (SFT)
def test_supervised_fine_tuning_sft():
    metrics = apex_neural_trainer.train_supervised_sft(epochs=5, lr=0.01)
    assert isinstance(metrics, TrainingMetrics)
    assert metrics.method == TrainingMethod.SUPERVISED_FINE_TUNING_SFT
    assert metrics.final_loss < metrics.initial_loss
    assert metrics.loss_reduction_pct > 30.0
    assert metrics.parameters_updated == 128 * 16
    assert os.path.exists(metrics.checkpoint_path)

    rep_text = apex_neural_trainer.format_training_report_text(metrics)
    assert "P.H.A.S.S v8.0 APEX NEURAL TRAINING REPORT" in rep_text
    assert "SUPERVISED_FINE_TUNING_SFT" in rep_text


# 3. Direct Preference Optimization (DPO)
def test_direct_preference_optimization_dpo():
    metrics = apex_neural_trainer.train_direct_preference_optimization(beta=0.1, epochs=5)
    assert isinstance(metrics, TrainingMetrics)
    assert metrics.method == TrainingMethod.DIRECT_PREFERENCE_OPTIMIZATION_DPO
    assert metrics.final_loss < metrics.initial_loss
    assert metrics.dpo_preference_margin > 0.0
    assert os.path.exists(metrics.checkpoint_path)


# 4. Elastic Weight Consolidation (EWC) Continual Learning
def test_continual_learning_ewc():
    metrics = apex_neural_trainer.train_continual_learning_ewc(ewc_lambda=0.5, epochs=5)
    assert isinstance(metrics, TrainingMetrics)
    assert metrics.method == TrainingMethod.ELASTIC_WEIGHT_CONSOLIDATION_EWC
    assert metrics.final_loss < metrics.initial_loss
    assert metrics.loss_reduction_pct > 20.0
    assert os.path.exists(metrics.checkpoint_path)


# 5. Synthetic Self-Play Data Generation
def test_synthetic_self_play_dataset():
    dataset = apex_neural_trainer.generate_synthetic_self_play_dataset(count=8)
    assert len(dataset) == 8
    assert all(isinstance(p, PreferencePair) for p in dataset)
    assert any("P.H.A.S.S" in p.chosen_response for p in dataset)


# 6. Conversational v8.0 AI Training Directives
def test_conversational_v8_training_directives():
    # A. General Training
    res_sft = conversational_agent.handle_natural_conversation("train ai model")
    assert res_sft is not None
    assert res_sft["type"] == "APEX_NEURAL_SFT_TRAINING"

    # B. DPO Alignment
    res_dpo = conversational_agent.handle_natural_conversation("train with dpo")
    assert res_dpo is not None
    assert res_dpo["type"] == "APEX_NEURAL_DPO_TRAINING"

    # C. Continual Learning
    res_ewc = conversational_agent.handle_natural_conversation("continual learning")
    assert res_ewc is not None
    assert res_ewc["type"] == "APEX_NEURAL_EWC_TRAINING"

    # D. Status
    res_stat = conversational_agent.handle_natural_conversation("training methods status")
    assert res_stat is not None
    assert res_stat["type"] == "APEX_NEURAL_TRAINING_STATUS"

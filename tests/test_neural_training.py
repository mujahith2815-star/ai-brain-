"""
Unit & Integration Tests for P.H.A.S.S Neural LLM/MLLM Model Training Engine & Pure Identity Alignment.
"""

import os
import pytest
from neural.model_trainer import neural_model_trainer, LoRAAttentionAdapter
from nlp.conversational_agent import conversational_agent


# 1. LoRA Attention Adapter Mechanics
def test_lora_attention_adapter():
    adapter = LoRAAttentionAdapter(dim=32, rank=4, alpha=8.0)
    x = [0.5] * 32
    delta_init = adapter.forward_delta(x)
    # Since matrix B is initialized to 0, initial delta should be zero
    assert all(abs(d) < 1e-6 for d in delta_init)

    # Perform gradient update
    grad_out = [0.1] * 32
    adapter.update_gradients(grad_out, x, lr=0.05)
    delta_after = adapter.forward_delta(x)
    assert any(abs(d) > 1e-6 for d in delta_after)


# 2. Cross-Entropy Loss & Backpropagation
def test_cross_entropy_loss_and_gradients():
    logits = [1.0, 2.0, 0.5, 3.0]
    target_idx = 3
    loss, grad = neural_model_trainer.compute_cross_entropy_loss(logits, target_idx)

    assert loss > 0.0
    assert len(grad) == len(logits)
    # The gradient at the target index should be negative (probs - 1.0)
    assert grad[target_idx] < 0.0


# 3. Multi-Epoch Training & Loss Reduction
def test_neural_training_loss_reduction():
    prompt = "What is P.H.A.S.S Sphere?"
    completion = "P.H.A.S.S is an autonomous physical 6-DOF robot with humanoid cognitive intelligence."

    metrics = neural_model_trainer.train_on_text(prompt, completion, epochs=6, lr=0.03)

    assert metrics.epoch == 6
    assert metrics.total_tokens_trained > 0
    assert metrics.final_loss <= metrics.initial_loss
    assert metrics.loss_reduction_pct >= 0.0
    assert metrics.lora_parameters_updated > 0


# 4. Checkpoint Serialization & Deserialization
def test_checkpoint_save_and_load(tmp_path):
    chk_file = str(tmp_path / "test_phass_checkpoint.json")
    saved_path = neural_model_trainer.save_checkpoint(chk_file)
    assert os.path.exists(saved_path)

    loaded = neural_model_trainer.load_checkpoint(saved_path)
    assert loaded is True


# 5. Pure P.H.A.S.S Identity Verification
def test_pure_phass_identity():
    res = conversational_agent.handle_natural_conversation("who are you")
    assert res is not None
    assert res["type"] == "CHITCHAT"
    assert "P.H.A.S.S Sphere" in res["speech_text"]
    # Verify it does not introduce itself as JARVIS
    assert not res["speech_text"].startswith("I am JARVIS")


# 6. Conversational Training Directives
def test_conversational_training_directive():
    cmd = "train When I ask for system status -> Report all 11 neural and physical subsystems nominal"
    res = conversational_agent.handle_natural_conversation(cmd)

    assert res is not None
    assert res["type"] == "NEURAL_MODEL_TRAINING"
    assert res["action_executed"] == "TRAIN_NEURAL_WEIGHTS"
    assert "TRAINING REPORT" in res["speech_text"]

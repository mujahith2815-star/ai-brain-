"""
Unit & Integration Tests for Software-to-AI-Model Distillation & Multi-Format Exporter.
"""

import os
import pytest
from neural.software_to_model_distiller import (
    software_to_model_distiller,
    DistillationReport,
    ModelArchitectureConfig,
)
from neural.model_exporter import model_exporter, ExportPackageManifest
from neural.phass_neural_llm import phass_neural_llm, NeuralGenerationOutput
from nlp.conversational_agent import conversational_agent


# 1. Software-to-Model Distillation
def test_software_to_model_distillation():
    report = software_to_model_distiller.distill_codebase_to_model()
    assert isinstance(report, DistillationReport)
    assert report.total_software_modules_distilled >= 10
    assert report.total_code_lines_tokenized > 500
    assert report.total_tools_embedded > 20
    assert report.distilled_parameters_count > 1_000_000
    assert report.model_config.num_hidden_layers == 16
    assert report.model_config.hidden_size == 1024

    rep_text = software_to_model_distiller.format_distillation_report_text(report)
    assert "P.H.A.S.S SOFTWARE-TO-AI-MODEL DISTILLATION" in rep_text
    assert "P.H.A.S.S-v8.0-Apex-Singularity" in rep_text


# 2. Multi-Format AI Model Export
def test_multi_format_model_export():
    manifest = model_exporter.export_full_ai_model_package()
    assert isinstance(manifest, ExportPackageManifest)
    assert os.path.exists(manifest.export_directory)
    assert "config.json" in manifest.exported_files
    assert "generation_config.json" in manifest.exported_files
    assert "tokenizer.json" in manifest.exported_files
    assert "phass-v8.0-q4_k_m.gguf.json" in manifest.exported_files
    assert "Modelfile" in manifest.exported_files

    # Verify physical file existence
    for fname in manifest.exported_files:
        assert os.path.exists(os.path.join(manifest.export_directory, fname))

    # Verify root Modelfile for Ollama
    assert os.path.exists(os.path.join(os.getcwd(), "Modelfile"))


# 3. Native Neural Inference Engine
def test_native_neural_inference_engine():
    # Math tool call prompt
    out_math = phass_neural_llm.generate("calculate sqrt(144) + 10")
    assert isinstance(out_math, NeuralGenerationOutput)
    assert out_math.tokens_generated > 0
    assert out_math.generation_time_ms > 0.0
    assert len(out_math.tool_calls_detected) >= 1
    assert out_math.tool_calls_detected[0]["name"] == "advanced_calculator"

    # Cyber threat prompt
    out_cyber = phass_neural_llm.generate("simulate cyber attack and check shield")
    assert len(out_cyber.tool_calls_detected) >= 1
    assert out_cyber.tool_calls_detected[0]["name"] == "intrusion_shield"

    # General prompt
    out_gen = phass_neural_llm.generate("who are you")
    assert "P.H.A.S.S" in out_gen.generated_text


# 4. Conversational Model Conversion Directives
def test_conversational_model_export_directive():
    res = conversational_agent.handle_natural_conversation("convert software into ai model")
    assert res is not None
    assert res["type"] == "SOFTWARE_TO_AI_MODEL_EXPORT"
    assert "P.H.A.S.S AI MODEL ARTIFACT EXPORT COMPLETE" in res["speech_text"]
    assert "Modelfile" in res["speech_text"]

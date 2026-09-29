"""
Unit & Integration Tests for Universal Scientific, Symbolic, Financial, and Unit Calculator Suite.
"""

import pytest
from tools.advanced_calculator import advanced_calculator, CalculatorResult
from sensors.cross_platform_adapter import cross_platform_adapter
from nlp.conversational_agent import conversational_agent


# 1. Scientific Calculator Calculations
def test_scientific_calculator_evaluations():
    # Power and Square Root
    res_sqrt = advanced_calculator.evaluate_scientific_expression("sqrt(144) + 2^4")
    assert res_sqrt.numeric_result == 28.0
    assert "sqrt(144) + 2^4 = 28" in res_sqrt.formatted_output

    # Trigonometry & Constants
    res_trig = advanced_calculator.evaluate_scientific_expression("sin(pi / 2)")
    assert abs(res_trig.numeric_result - 1.0) < 1e-5

    # Logarithms
    res_log = advanced_calculator.evaluate_scientific_expression("log(1000) + ln(e)")
    assert abs(res_log.numeric_result - 4.0) < 1e-5


# 2. Symbolic Algebraic Equation Solver
def test_symbolic_algebra_solver():
    # Linear equation: 2x + 10 = 30 -> x = 10
    res_lin = advanced_calculator.solve_algebraic_equation("2x + 10 = 30")
    assert res_lin.calculation_type == "SYMBOLIC_ALGEBRA"
    assert res_lin.numeric_result == 10.0
    assert "x = 10" in res_lin.formatted_output

    # Quadratic equation: x^2 = 16 -> x = 4, -4
    res_quad = advanced_calculator.solve_algebraic_equation("x^2 = 16")
    assert "x₁ = 4" in res_quad.formatted_output
    assert "x₂ = -4" in res_quad.formatted_output


# 3. Unit & Physical Dimension Conversions
def test_unit_conversions():
    # Length: Miles to Kilometers
    res_len = advanced_calculator.convert_units(50.0, "miles", "km")
    assert res_len.numeric_result is not None
    assert abs(res_len.numeric_result - 80.4672) < 0.01

    # Temperature: Celsius to Fahrenheit
    res_temp = advanced_calculator.convert_units(100.0, "c", "f")
    assert res_temp.numeric_result == 212.0

    # Data: Gigabytes to Megabytes
    res_data = advanced_calculator.convert_units(4.0, "gb", "mb")
    assert res_data.numeric_result == 4096.0


# 4. Financial Compound Interest
def test_financial_compound_interest():
    res_fin = advanced_calculator.calculate_compound_interest(principal=10000.0, annual_rate_pct=5.0, years=3.0)
    assert res_fin.numeric_result is not None
    assert res_fin.numeric_result > 11500.0 # 10000 * 1.05^3 = 11576.25
    assert "Future Balance:" in res_fin.formatted_output


# 5. Statistical Distribution Analysis
def test_statistical_analysis():
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    res_stat = advanced_calculator.calculate_statistics(data)
    assert res_stat.numeric_result == 30.0 # Mean
    assert "Mean: 30" in res_stat.formatted_output
    assert "Median: 30" in res_stat.formatted_output


# 6. Cross-Platform Hardware Telemetry Adapter
def test_cross_platform_adapter():
    telemetry = cross_platform_adapter.get_unified_platform_telemetry()
    assert telemetry.os_name in ("Windows", "Linux", "Darwin")
    assert telemetry.cpu_logical_cores >= 1
    assert telemetry.total_ram_gb > 0.5
    assert telemetry.total_disk_gb > 1.0


# 7. Conversational Directives for Universal Calculator
def test_conversational_calculator_directives():
    # A. Solve Algebraic Equation
    res_eq = conversational_agent.handle_natural_conversation("solve equation 2x + 10 = 30")
    assert res_eq is not None
    assert res_eq["type"] == "SYMBOLIC_ALGEBRA_CALCULATION"
    assert "x = 10" in res_eq["speech_text"]

    # B. Unit Conversion
    res_conv = conversational_agent.handle_natural_conversation("convert 50 miles to km")
    assert res_conv is not None
    assert res_conv["type"] == "UNIT_CONVERSION_CALCULATION"
    assert "80.4672" in res_conv["speech_text"]

    # C. Compound Interest
    res_fin = conversational_agent.handle_natural_conversation("calculate compound interest for 10000 at 5% for 3 years")
    assert res_fin is not None
    assert res_fin["type"] == "FINANCIAL_CALCULATION"

    # D. Statistics
    res_stat = conversational_agent.handle_natural_conversation("calculate statistics for 10, 20, 30, 40, 50")
    assert res_stat is not None
    assert res_stat["type"] == "STATISTICAL_CALCULATION"
    assert "Mean: 30" in res_stat["speech_text"]

    # E. Scientific Math
    res_sci = conversational_agent.handle_natural_conversation("calculate sqrt(144) + 2^4")
    assert res_sci is not None
    assert res_sci["type"] == "SCIENTIFIC_CALCULATION"
    assert "28" in res_sci["speech_text"]

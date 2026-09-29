import sys
sys.path.insert(0, ".")

print("Testing core.error_analyzer...")
import core.error_analyzer
print("OK error_analyzer")

print("Testing core.fix_generator...")
import core.fix_generator
print("OK fix_generator")

print("Testing core.fix_validator...")
import core.fix_validator
print("OK fix_validator")

print("Testing core.rollback_manager...")
import core.rollback_manager
print("OK rollback_manager")

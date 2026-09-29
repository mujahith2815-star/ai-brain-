"""
Positive Integer Finder & Filter in Python
Identifies, validates, and extracts positive integers (> 0) from any input dataset or user input stream.
"""

from typing import Any, List, Union


def find_positive_integers(data: List[Any]) -> List[int]:
    """
    Filters and returns only strictly positive integers (n > 0) from an arbitrary list.
    Handles numeric strings, floats (converted if whole), and ignores negative/zero values.
    """
    positive_integers: List[int] = []
    
    for item in data:
        try:
            # Handle string conversions
            val = float(item) if isinstance(item, str) else item
            
            # Check if integer-equivalent and strictly positive
            if isinstance(val, (int, float)) and val.is_integer() if isinstance(val, float) else isinstance(val, int):
                int_val = int(val)
                if int_val > 0:
                    positive_integers.append(int_val)
        except (ValueError, TypeError):
            continue
            
    return positive_integers


def is_positive_integer(value: Any) -> bool:
    """Checks whether a single value is a positive integer."""
    try:
        val = int(value)
        return val > 0
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    test_data = [-10, 0, 15, "42", 3.0, -2.5, "abc", 100, -1, 7]
    positives = find_positive_integers(test_data)
    print(f"Original Data: {test_data}")
    print(f"Positive Integers Found: {positives}")

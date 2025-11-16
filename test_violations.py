# test_violations.py
import sys
import os  # Wrong order - should trigger I201

def bad_function(x=[]):  # Should trigger B006 (mutable default)
    """Missing return type in docstring - should trigger D400/D401"""
    very_long_line = "This line is intentionally much much much longer than seventy nine characters to trigger E501"
    if True:
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            print("Deep nesting")  # Should trigger complexity
    return x

class MyClass:  # Should trigger D101 (missing class docstring)
    pass
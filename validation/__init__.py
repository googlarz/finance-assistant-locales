"""
Validation suite: official tax-authority test cases for all locale engines.

Each sub-package (de, uk, fr, nl, pl) contains:
  - cases.json  — ground-truth cases sourced from official publications
  - validate.py — runner that calls the locale engine and checks expected values

Use runner.run_all_validations() to run everything at once.
"""

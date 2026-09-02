"""Promptfoo test-case entry point.

Referenced from promptfooconfig.yaml as:

    tests: file://finxpia_tests.py:generate_tests

A thin shim so that the file promptfoo resolves stays stable while the implementation lives in
the installed package.
"""

from finxpia.packaging.promptfoo_dataset import generate_tests

__all__ = ["generate_tests"]

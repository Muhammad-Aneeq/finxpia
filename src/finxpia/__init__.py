"""FinXPIA - finance-document prompt-injection corpus with a co-equal benign twin corpus.

Defensive security tooling. Every case is synthetic and generated from seeded templates, and
every case exists so that teams can test and harden their own document-processing agents. Use
only against systems you own or are explicitly authorized to test (see LICENSE).
"""

from __future__ import annotations

__version__ = "0.1.0"

SYNTHETIC_DATA_NOTICE = (
    "All data is synthetic and generated from seeded templates. "
    "Any resemblance to a real organization is coincidental."
)

AUTHORIZED_USE_NOTICE = "Use only against systems you own or are explicitly authorized to test."

__all__ = [
    "AUTHORIZED_USE_NOTICE",
    "SYNTHETIC_DATA_NOTICE",
    "__version__",
]

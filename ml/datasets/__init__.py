"""Unified loaders for public ECG datasets used to train HeartScan.

Each dataset in :mod:`ml.datasets.registry` declares:

- canonical name + version pin (so downstream manifests are reproducible);
- license string (used by the CLI to warn before commercial use);
- ``download(target_dir)`` callable — prints what to do for restricted
  datasets, runs ``wget``/``zip``/``physionet`` for open ones;
- ``parse(target_dir)`` callable returning a :class:`SampleStream` of
  ``Sample`` records with the harmonised HeartScan label.

The submodules are intentionally side-effect-free at import time so a
laptop without 300 GB of disk can still ``python -m ml.datasets.cli list``.
"""

from ml.datasets.registry import REGISTRY, Dataset, Sample, SampleStream  # noqa: F401

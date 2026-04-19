# Model weights

Place a PyTorch checkpoint here, e.g. `ecg_cnn1d.pt`, and set `HEARTSCAN_MODEL_PATH` to its path.

Expected format:

- Either a raw `state_dict`
- Or a dict with keys `state_dict` and optional `version`

Train with `scripts/train_cnn1d.py` (MIT-BIH / PhysioNet workflow is project-specific).

License: comply with dataset licenses (e.g. PhysioNet credentialed access where required).

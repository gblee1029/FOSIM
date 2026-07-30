# Known Limitations

- The original `/mnt/data` prompt and PDF paths were not available in this
  Windows workspace, so this prototype uses the requirements embedded in the
  current Codex request and the referenced conversation summary.
- Real SH-2 communication is intentionally excluded from this MVP.
- Rule thresholds are starter values, not production calibration.
- Optimization now evaluates candidates across a repeated-cycle group, which
  removes overfitting to one arbitrarily chosen waveform and quantifies
  cycle-to-cycle scatter. It does not reduce the simulator's own model error.
  Proving the true effect of a setting change still requires controlled
  before/after trials on real SH-2 equipment.
- Target Torque changes are simulated but should be disabled unless product
  torque limits are known.
- The generated sample data is synthetic and only validates application flow.
- The simulator does not model motor current control, bit compliance, screw
  pitch, material lot, friction variation, or robot alignment.
- SQLite stores analysis history, but waveform storage is optimized only for an
  MVP-scale local prototype.
- Frontend charts are validated by build/type checks, not by browser screenshot
  inspection in this run.

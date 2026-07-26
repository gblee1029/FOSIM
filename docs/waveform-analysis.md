# Waveform Analysis

## Segmentation Pseudocode

```text
sort waveform by time
calculate baseline torque from first samples
calculate torque gradient
start = first speed or torque movement
engage = first torque above baseline + small threshold
seating = first sustained torque and gradient threshold crossing
target_reach = first torque >= 96% of target torque after seating
hold_end = target_reach + configured torque_hold_time
stop = first low speed sample after target, or end of waveform
```

If event codes are available in later data, they can override or validate the
rule-based markers. The MVP uses signal rules only.

## Feature Groups

- Overall: total time, max torque, final torque, RMS, integral, peak-to-peak.
- Free Run: duration, mean torque, vibration energy.
- Engage: duration, gradient, speed drop.
- Seating: time, torque, angle, speed, confidence, impact peak.
- Clamp: clamp time, gradient, angle, linearity, oscillation.
- Hold: mean torque, standard deviation, decay, vibration energy.
- Result: target error, overshoot, undershoot, stability score, anomaly score.

## Diagnosis Rules

The MVP diagnosis engine flags:

- Torque Overshoot,
- Torque Undershoot,
- Early or Late Seating Suspected,
- Hold Instability,
- Normal.

These are deliberately conservative and should be calibrated with real SH-2
cycles before production use.

# Simulation Model

## Purpose

The MVP simulator is a rule-based what-if model. It shows the likely direction
of waveform change when a user changes settings. It does not guarantee real
fastening behavior.

## Inputs

- current waveform,
- current settings,
- candidate settings,
- detected segments,
- current features.

## Supported Setting Effects

Target Speed:

- lower speed stretches pre-seating time,
- lower speed can reduce seating impact,
- lower speed increases predicted total time.

Clamp Rising Time:

- larger value stretches the clamp region,
- larger value lowers clamp gradient,
- larger value reduces predicted overshoot.

Torque Hold Time:

- larger value extends the hold segment,
- larger value can slightly improve stability.

Target Torque:

- changes the clamp target and hold mean,
- warns because product torque limits must be verified.

## Reconstruction Pseudocode

```text
detect current segments
extract current features
calculate setting deltas
predict changed clamp time, overshoot, final torque, stability
generate time axis from median sampling interval
build pre-seating curve
build clamp curve with exponential rise
build hold curve with damped oscillation
build stop curve with exponential decay
return predicted samples and feature comparison
```

Clamp uses:

```text
T(t) = T_seating + (T_target - T_seating) * (1 - exp(-k * t))
```

The curve is normalized so the target point is reached at the predicted clamp
end time.

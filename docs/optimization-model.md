# Optimization Model

## Candidate Generation

MVP variables:

- target_speed,
- clamp_rising_time,
- torque_hold_time,
- target_torque when explicitly allowed.

Default search:

- Target Speed: current x 0.90, 0.95, 1.00, 1.05.
- Clamp Rising Time: current -20, current, current +20, +40, +60 ms.
- Torque Hold Time: current, current +10, +20, +30 ms.
- Target Torque: unchanged unless allowed by objectives.

## Constraint Filter

Candidates are rejected when:

- predicted final torque is outside objective limits,
- predicted overshoot exceeds the limit,
- predicted fastening time exceeds the limit,
- predicted stability is below the limit,
- prediction confidence is too low.

Every candidate is simulated on every cycle in the group, and the gate is
applied to the group rather than to one waveform:

- fewer than 20 cycles use the `worst` gate, where every cycle must satisfy
  the constraints. Small samples are not relaxed: with few cycles the worst
  case is the only information available, and relaxing it produces
  unjustifiably optimistic results.
- 20 or more cycles use the `p95` gate, so a single extreme value cannot
  reject every candidate.

## Scoring

Total score is 100 points:

- constraint satisfaction: 30,
- target torque accuracy: 15 (group mean),
- reproducibility: 20 (predicted peak-torque spread across cycles),
- overshoot: 15 (worst cycle),
- stability: 15 (worst cycle),
- fastening time: 3 (group mean),
- setting change size: 2.

Reproducibility scores the spread of predicted outcomes under the observed
cycle-to-cycle variation. It is not a prediction that a candidate reduces
process scatter.

It uses predicted peak torque rather than predicted final torque. The
rule-based simulator derives final torque from the candidate settings alone,
so its spread across cycles is always zero and would score every candidate
identically. Peak torque is derived from each cycle's observed overshoot and
therefore carries the cycle-to-cycle variation the score is meant to capture.

## Cost

Preprocessing (normalization, segmentation, feature extraction) depends only on
the observed waveform and the current settings, so it runs once per waveform
rather than once per candidate. Predicted waveforms are generated only for the
candidates returned to the client. Measured on a local desktop with 80
candidates: 1 cycle 1.4s, 10 cycles 2.9s, 20 cycles 4.8s, against a 10s budget.
Re-check with `python scripts/measure_optimization_cost.py 20`.

## Recommendations

The optimizer returns three labeled candidates:

- `quality_stable`: best overshoot and stability balance,
- `cycle_time`: fastest constrained candidate,
- `minimum_change`: smallest change that still satisfies constraints.

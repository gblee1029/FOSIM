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

## Scoring

Total score is 100 points:

- constraint satisfaction: 35,
- target torque accuracy: 20,
- overshoot: 15,
- clamp stability: 10,
- hold stability: 10,
- fastening time: 5,
- setting change size: 5.

## Recommendations

The optimizer returns three labeled candidates:

- `quality_stable`: best overshoot and stability balance,
- `cycle_time`: fastest constrained candidate,
- `minimum_change`: smallest change that still satisfies constraints.

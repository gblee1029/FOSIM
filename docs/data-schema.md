# Data Schema

## Settings CSV

Required columns:

```csv
cycle_id,target_speed,target_torque,clamp_rising_time,torque_hold_time
```

Optional columns:

```csv
product_model,process_id,screw_position,joint_type,seating_sensitivity,speed_adjust_time
```

Example:

```csv
cycle_id,product_model,process_id,screw_position,joint_type,target_speed,target_torque,clamp_rising_time,torque_hold_time,seating_sensitivity,speed_adjust_time
CYCLE-NORMAL-001,MODEL-A,P10,S01,HARD,820,1.20,100,30,50,25
```

## Waveform CSV

Required columns:

```csv
cycle_id,sample_index,time_ms,torque
```

Optional columns:

```csv
speed,angle,current,event_code
```

Units:

- torque: Nm
- speed: RPM
- angle: degrees
- time_ms: milliseconds
- current: A

## API Shape

`POST /api/import/csv` accepts settings and waveform CSV strings and returns:

- cycle metadata,
- processed waveform samples,
- detected segments,
- extracted features,
- rule-based diagnosis.

`POST /api/simulations` accepts waveform samples, current settings, and candidate
settings, then returns a predicted waveform and predicted features.

`POST /api/optimizations` accepts waveform samples, current settings, and
objectives, then returns three labeled recommendations.

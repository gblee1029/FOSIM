from fastapi.testclient import TestClient

from app.main import app


def test_import_simulation_and_optimization_api_flow():
    client = TestClient(app)
    settings_csv = "\n".join(
        [
            "cycle_id,product_model,process_id,screw_position,joint_type,target_speed,target_torque,clamp_rising_time,torque_hold_time,seating_sensitivity,speed_adjust_time",
            "CYCLE-API,MODEL-A,P10,S01,HARD,820,1.20,100,30,50,25",
        ]
    )
    rows = [
        "cycle_id,sample_index,time_ms,torque,speed,angle,current,event_code",
        "CYCLE-API,0,0,0.03,0,0,0.2,",
        "CYCLE-API,1,20,0.04,420,2,0.22,",
        "CYCLE-API,2,80,0.08,800,7,0.26,",
        "CYCLE-API,3,140,0.25,720,12,0.4,",
        "CYCLE-API,4,190,0.72,510,16,0.8,",
        "CYCLE-API,5,240,1.05,300,19,1.0,",
        "CYCLE-API,6,280,1.21,120,20,1.2,",
        "CYCLE-API,7,320,1.20,20,20.5,1.1,",
        "CYCLE-API,8,380,0.8,0,20.5,0.8,",
    ]
    waveform_csv = "\n".join(rows)

    imported = client.post(
        "/api/import/csv",
        json={"settings_csv": settings_csv, "waveform_csv": waveform_csv},
    )
    assert imported.status_code == 200
    body = imported.json()
    assert body["cycle"]["cycle_id"] == "CYCLE-API"
    assert body["analysis"]["features"]["peak_torque"] >= 1.2

    simulation = client.post(
        "/api/simulations",
        json={
            "waveform": body["cycle"]["waveform"],
            "current_settings": body["cycle"]["settings"],
            "candidate_settings": {
                **body["cycle"]["settings"],
                "target_speed": 760,
                "clamp_rising_time": 150,
                "torque_hold_time": 50,
            },
        },
    )
    assert simulation.status_code == 200
    sim_body = simulation.json()
    assert sim_body["simulation_type"] == "rule_based"
    assert len(sim_body["predicted_waveform"]) > 5

    optimization = client.post(
        "/api/optimizations",
        json={
            "waveform": body["cycle"]["waveform"],
            "current_settings": body["cycle"]["settings"],
            "objectives": {
                "target_torque_min": 1.16,
                "target_torque_max": 1.24,
                "max_overshoot_percent": 6,
                "max_fastening_time": 700,
            },
        },
    )
    assert optimization.status_code == 200
    opt_body = optimization.json()
    assert {item["label"] for item in opt_body["recommended"]} == {
        "quality_stable",
        "cycle_time",
        "minimum_change",
    }

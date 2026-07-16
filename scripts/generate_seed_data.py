"""
Generates all seed data for Sanket AI (deterministic — safe to re-run):

  backend/data/demo_pid_graph.json     Extended P&ID topology (cooling-water + lube-oil/compressor)
  backend/data/iso14224_taxonomy.json  ISO 14224 failure-mode taxonomy (7 equipment classes)
  backend/data/work_orders.json        30 CMMS work orders
  backend/data/inspection_logs.json    50 inspection logs
  backend/data/compliance_clauses.json Indian + international regulatory clauses mapped to equipment

The eight narrative-critical records for the P-101A / V-201 cavitation demo are
authored by hand; the remainder are generated procedurally with a fixed seed so
the corpus is large, varied and reproducible.

Run:  python scripts/generate_seed_data.py
"""
import json
import os
import random
from datetime import date, timedelta

random.seed(1729)
OUT = os.path.join(os.path.dirname(__file__), "..", "backend", "data")
os.makedirs(OUT, exist_ok=True)


def dump(name, obj, label):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    n = len(obj) if isinstance(obj, list) else (
        len(obj.get("equipment", obj)) if isinstance(obj, dict) else "")
    print(f"  [ok] {name} ({n} records)" if n != "" else f"  [ok] {name}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. ISO 14224 FAILURE-MODE TAXONOMY  (7 classes)
# ══════════════════════════════════════════════════════════════════════════════
iso14224 = {
    "version": "ISO 14224:2016",
    "equipment_classes": [
        {"class": "CENTRIFUGAL_PUMP", "iso_code": "PU-C", "failure_modes": [
            {"code": "PU-C-VIB", "description": "Excessive vibration",
             "mechanisms": ["Unbalance", "Misalignment", "Cavitation", "Bearing wear", "Resonance"],
             "upstream_causes": ["Upstream cavitation from control valve", "NPSH margin loss", "Suction strainer blockage"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Vibration monitoring (mm/s RMS)", "Acoustic emission", "Temperature"],
             "typical_frequency_hz": [10, 25, 47, 100]},
            {"code": "PU-C-LEK", "description": "External leakage — mechanical seal",
             "mechanisms": ["Seal face wear", "O-ring degradation", "Thermal cycling"],
             "upstream_causes": ["Dry running", "Excessive vibration", "Abrasive media"],
             "iso14224_frequency": "MEDIUM", "detection_methods": ["Visual inspection", "Leak detection sensor"], "typical_frequency_hz": []},
            {"code": "PU-C-CAP", "description": "Reduced capacity / low flow",
             "mechanisms": ["Impeller wear", "Recirculation", "Air entrainment"],
             "upstream_causes": ["Upstream valve restriction", "Suction cavitation", "Suction strainer blockage"],
             "iso14224_frequency": "MEDIUM", "detection_methods": ["Flow meter", "Pressure gauges", "Power consumption"], "typical_frequency_hz": []},
            {"code": "PU-C-BRG", "description": "Bearing failure",
             "mechanisms": ["Fatigue", "Lubrication failure", "Contamination", "Overloading"],
             "upstream_causes": ["Transmitted vibration from upstream equipment", "Misalignment during installation"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Temperature (>80°C)", "Vibration >7.1 mm/s RMS", "Noise"],
             "typical_frequency_hz": [47, 94]},
        ]},
        {"class": "CONTROL_VALVE", "iso_code": "VA-C", "failure_modes": [
            {"code": "VA-C-CAV", "description": "Cavitation",
             "mechanisms": ["High pressure differential", "Trim wear", "Flashing"],
             "downstream_effects": ["Transmitted vibration to connected pumps", "Pipe erosion", "Noise"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Noise (crackling/popping)", "Vibration on body", "Trim inspection"], "typical_frequency_hz": []},
            {"code": "VA-C-STK", "description": "Valve stuck / fails to open or close",
             "mechanisms": ["Actuator failure", "Stem packing tight", "Process deposits"],
             "downstream_effects": ["Loss of flow control", "Process deviation"],
             "iso14224_frequency": "MEDIUM", "detection_methods": ["Positioner feedback", "Control room deviation alarm"], "typical_frequency_hz": []},
            {"code": "VA-C-LEK", "description": "Internal leakage (seat leakage)",
             "mechanisms": ["Seat erosion", "Trim wear", "Cavitation damage"],
             "downstream_effects": ["Reduced pressure differential", "Flow measurement error"],
             "iso14224_frequency": "MEDIUM", "detection_methods": ["Acoustic emission", "Thermal imaging", "Seat test"], "typical_frequency_hz": []},
        ]},
        {"class": "HEAT_EXCHANGER", "iso_code": "HE", "failure_modes": [
            {"code": "HE-FOL", "description": "Fouling / reduced heat transfer",
             "mechanisms": ["Scale deposition", "Biological fouling", "Corrosion products"],
             "upstream_causes": ["Poor water treatment", "High turbidity"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Outlet temperature deviation", "Pressure drop increase", "HEI"], "typical_frequency_hz": []},
            {"code": "HE-TUB", "description": "Tube failure / leakage",
             "mechanisms": ["Corrosion", "Erosion", "Vibration fatigue", "Pitting"],
             "upstream_causes": ["High velocity flow", "Flow-induced vibration"],
             "iso14224_frequency": "LOW", "detection_methods": ["Pressure test", "Helium leak test", "Process contamination"], "typical_frequency_hz": []},
        ]},
        {"class": "CENTRIFUGAL_COMPRESSOR", "iso_code": "CO-C", "failure_modes": [
            {"code": "CO-C-SRG", "description": "Surge / flow instability",
             "mechanisms": ["Low flow operation", "Anti-surge valve fault", "Discharge blockage"],
             "upstream_causes": ["Suction filter blockage", "Process upset"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Flow oscillation", "Axial vibration", "Discharge pressure swing"], "typical_frequency_hz": []},
            {"code": "CO-C-VIB", "description": "High vibration / rotor instability",
             "mechanisms": ["Unbalance", "Oil whirl", "Blade fouling", "Coupling wear"],
             "upstream_causes": ["Lube oil contamination", "Bearing degradation"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Proximity probe (µm)", "Bearing temperature"], "typical_frequency_hz": [50, 100, 150]},
            {"code": "CO-C-SEAL", "description": "Dry-gas seal failure",
             "mechanisms": ["Seal face contamination", "Reverse pressurisation", "Particle ingress"],
             "upstream_causes": ["Seal gas filter fouling", "Lube oil migration"],
             "iso14224_frequency": "MEDIUM", "detection_methods": ["Seal gas flow", "Vent leakage rate"], "typical_frequency_hz": []},
        ]},
        {"class": "ELECTRIC_MOTOR", "iso_code": "EM", "failure_modes": [
            {"code": "EM-WND", "description": "Stator winding insulation failure",
             "mechanisms": ["Thermal ageing", "Moisture ingress", "Voltage transients"],
             "upstream_causes": ["Overloading", "Cooling loss"],
             "iso14224_frequency": "MEDIUM", "detection_methods": ["Insulation resistance", "Partial discharge", "Winding temperature"], "typical_frequency_hz": []},
            {"code": "EM-BRG", "description": "Motor bearing failure",
             "mechanisms": ["Lubrication failure", "Shaft currents", "Contamination"],
             "upstream_causes": ["Transmitted vibration", "VFD bearing currents"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Vibration envelope", "Temperature", "SPM"], "typical_frequency_hz": [120, 240]},
        ]},
        {"class": "STRAINER", "iso_code": "ST", "failure_modes": [
            {"code": "ST-BLK", "description": "Strainer blockage / high differential pressure",
             "mechanisms": ["Debris accumulation", "Scale", "Corrosion products"],
             "downstream_effects": ["Suction starvation", "Pump cavitation", "Flow reduction"],
             "iso14224_frequency": "HIGH", "detection_methods": ["Differential pressure", "Flow reduction"], "typical_frequency_hz": []},
        ]},
        {"class": "STORAGE_VESSEL", "iso_code": "VE", "failure_modes": [
            {"code": "VE-COR", "description": "Internal corrosion / wall thinning",
             "mechanisms": ["Pitting", "Microbially induced corrosion", "Erosion-corrosion"],
             "upstream_causes": ["Water chemistry excursion", "Coating breakdown"],
             "iso14224_frequency": "MEDIUM", "detection_methods": ["UT thickness survey", "Visual/borescope"], "typical_frequency_hz": []},
        ]},
    ],
    "co_failure_statistics": [
        {"primary": "VA-C-CAV", "secondary": "PU-C-VIB", "correlation": 0.72,
         "note": "Control-valve cavitation is the leading upstream cause of centrifugal-pump vibration in cooling-water circuits", "occurrences_per_100_plant_years": 68},
        {"primary": "PU-C-VIB", "secondary": "PU-C-BRG", "correlation": 0.85,
         "note": "Sustained vibration >7.1 mm/s leads to bearing failure within 2–6 weeks", "occurrences_per_100_plant_years": 55},
        {"primary": "ST-BLK", "secondary": "PU-C-VIB", "correlation": 0.61,
         "note": "Suction-strainer blockage starves pump suction and induces cavitation-driven vibration", "occurrences_per_100_plant_years": 41},
        {"primary": "HE-FOL", "secondary": "PU-C-CAP", "correlation": 0.48,
         "note": "Heat-exchanger fouling increases back-pressure, reducing pump effective head", "occurrences_per_100_plant_years": 30},
        {"primary": "CO-C-VIB", "secondary": "EM-BRG", "correlation": 0.57,
         "note": "Compressor rotor vibration transmits to the driver motor bearings via the coupling", "occurrences_per_100_plant_years": 26},
        {"primary": "CO-C-SRG", "secondary": "CO-C-VIB", "correlation": 0.66,
         "note": "Repeated surge events accelerate rotor instability and blade fouling", "occurrences_per_100_plant_years": 22},
        {"primary": "ST-BLK", "secondary": "CO-C-VIB", "correlation": 0.58,
         "note": "Lube-oil filter blockage starves compressor bearings and drives rotor vibration/oil whirl", "occurrences_per_100_plant_years": 24},
    ],
}
dump("iso14224_taxonomy.json", iso14224, "taxonomy")


# ══════════════════════════════════════════════════════════════════════════════
# 2. EXTENDED P&ID GRAPH  (cooling-water circuit + lube-oil/compressor train)
# ══════════════════════════════════════════════════════════════════════════════
def eq(tag, name, typ, crit, area, desc, **extra):
    return {"tag": tag, "name": name, "type": typ, "iso15926_class": typ.title().replace("_", ""),
            "isa95_level": "EQUIPMENT_MODULE", "area": area, "criticality": crit, "description": desc, **extra}


def conn(a, b, pipe, medium="cooling_water", flow="SUPPLY", dia=10, ctype=None):
    d = {"from_tag": a, "to_tag": b, "pipe_tag": pipe, "medium": medium,
         "flow_direction": flow, "nominal_diameter_in": dia, "spec": "CS-150#"}
    if ctype:
        d["connection_type"] = ctype
    return d


demo_graph = {
    "pid_id": "PID-CWS-001", "title": "Cooling Water & Compressor Train — Unit 01",
    "revision": "Rev D", "plant": "Octave Demo Plant", "area": "A-01",
    "equipment": [
        eq("TK-401", "Cooling Water Storage Tank", "STORAGE_VESSEL", "MEDIUM", "A-01",
           "Open atmospheric cooling water storage, lined carbon steel", capacity_m3=500),
        eq("ST-101", "CW Suction Strainer", "STRAINER", "MEDIUM", "A-01",
           "Duplex basket strainer on pump suction header, 40 mesh"),
        eq("V-201", "CW Supply Control Valve", "CONTROL_VALVE", "HIGH", "A-01",
           "Pneumatically actuated globe control valve on CW supply header", cv=120, trim_type="EQUAL_PERCENTAGE"),
        eq("P-101A", "Cooling Water Pump A", "CENTRIFUGAL_PUMP", "HIGH", "A-01",
           "Primary CW supply pump, horizontal end-suction centrifugal", design_flow_m3h=350, motor_kw=55),
        eq("P-101B", "Cooling Water Pump B (Standby)", "CENTRIFUGAL_PUMP", "HIGH", "A-01",
           "Standby CW supply pump, auto-start on P-101A trip", design_flow_m3h=350, motor_kw=55),
        eq("M-101A", "P-101A Drive Motor", "ELECTRIC_MOTOR", "HIGH", "A-01",
           "55 kW TEFC induction motor driving P-101A", motor_kw=55),
        eq("HE-301", "Process Cooling Heat Exchanger", "HEAT_EXCHANGER", "HIGH", "A-01",
           "Shell & tube, cooling water on shell side, process fluid on tube side", duty_kw=1200),
        eq("FT-101", "CW Supply Flow Transmitter", "FLOW_TRANSMITTER", "MEDIUM", "A-01",
           "Magnetic flow meter on CW supply header downstream of pumps"),
        eq("PT-101", "CW Supply Pressure Transmitter", "PRESSURE_TRANSMITTER", "MEDIUM", "A-01",
           "Pressure transmitter at P-101A/B discharge header"),
        eq("VT-101", "P-101A Vibration Transmitter", "VIBRATION_TRANSMITTER", "HIGH", "A-01",
           "Radial vibration sensor on P-101A drive-end bearing", alarm_high_mm_s=4.5, trip_mm_s=7.1),
        # Lube-oil / compressor train
        eq("TK-501", "Lube Oil Reservoir", "STORAGE_VESSEL", "MEDIUM", "A-02",
           "Compressor lube-oil reservoir with heater and level control", medium="lube_oil"),
        eq("P-501", "Lube Oil Pump", "CENTRIFUGAL_PUMP", "HIGH", "A-02",
           "Main lube-oil pump feeding compressor bearings", medium="lube_oil"),
        eq("F-501", "Lube Oil Filter", "STRAINER", "HIGH", "A-02",
           "Duplex 10-micron lube-oil filter upstream of compressor bearings", medium="lube_oil"),
        eq("K-501", "Process Gas Compressor", "CENTRIFUGAL_COMPRESSOR", "HIGH", "A-02",
           "Two-stage centrifugal process-gas compressor, dry-gas sealed"),
        eq("M-501", "K-501 Drive Motor", "ELECTRIC_MOTOR", "HIGH", "A-02",
           "1.2 MW induction motor driving K-501 via gearbox"),
        eq("VT-501", "K-501 Vibration Probe", "VIBRATION_TRANSMITTER", "HIGH", "A-02",
           "Proximity probe on K-501 outboard bearing", alarm_high_um=50, trip_um=75),
        eq("V-501", "Anti-Surge Valve", "CONTROL_VALVE", "HIGH", "A-02",
           "Fast-acting anti-surge recycle valve for K-501", cv=200),
    ],
    "connections": [
        conn("TK-401", "ST-101", "CWS-01-12IN", dia=12),
        conn("ST-101", "V-201", "CWS-02-12IN", dia=12),
        conn("V-201", "P-101A", "CWS-03-10IN"),
        conn("V-201", "P-101B", "CWS-04-10IN"),
        conn("P-101A", "HE-301", "CWS-05-10IN", flow="DISCHARGE"),
        conn("P-101B", "HE-301", "CWS-06-10IN", flow="DISCHARGE"),
        conn("P-101A", "FT-101", "CWS-05-10IN", flow="DISCHARGE"),
        conn("P-101A", "PT-101", "CWS-05-10IN", flow="DISCHARGE"),
        conn("M-101A", "P-101A", "", medium="mechanical", flow="DRIVE", dia=0, ctype="MECHANICAL_DRIVE"),
        conn("P-101A", "VT-101", "", medium=None, flow=None, dia=0, ctype="MECHANICAL_SENSOR"),
        # lube-oil / compressor
        conn("TK-501", "P-501", "LO-01-4IN", medium="lube_oil", dia=4),
        conn("P-501", "F-501", "LO-02-4IN", medium="lube_oil", dia=4, flow="DISCHARGE"),
        conn("F-501", "K-501", "LO-03-3IN", medium="lube_oil", dia=3, flow="SUPPLY"),
        conn("M-501", "K-501", "", medium="mechanical", flow="DRIVE", dia=0, ctype="MECHANICAL_DRIVE"),
        conn("K-501", "VT-501", "", medium=None, flow=None, dia=0, ctype="MECHANICAL_SENSOR"),
        conn("K-501", "V-501", "PG-01-8IN", medium="process_gas", dia=8, flow="RECYCLE"),
    ],
}
dump("demo_pid_graph.json", demo_graph, "graph")


# ══════════════════════════════════════════════════════════════════════════════
# 3. WORK ORDERS  (8 narrative + 22 procedural = 30)
# ══════════════════════════════════════════════════════════════════════════════
work_orders = [
    {"id": "WO-2025-0234", "equipment_tag": "V-201", "title": "V-201 Scheduled Valve Inspection — Trim Assessment",
     "type": "PREVENTIVE", "status": "CLOSED", "priority": "MEDIUM", "date_raised": "2025-01-15", "date_closed": "2025-01-18",
     "technician": "Rajesh Kumar", "iso14224_failure_mode": "VA-C-CAV",
     "findings": "Trim inspection revealed 8% wear on upper seating surface. Slight scoring visible on plug face. No leakage detected. Cavitation marks consistent with high differential pressure operation. Recommended: monitor at next 6-month interval.",
     "action_taken": "Cleaned valve internals, lubricated packing, set positioner calibration. Returned to service.", "labour_hours": 6},
    {"id": "WO-2025-0891", "equipment_tag": "V-201", "title": "V-201 Unplanned — Noise and Vibration Complaint from Field",
     "type": "CORRECTIVE", "status": "CLOSED", "priority": "HIGH", "date_raised": "2025-04-03", "date_closed": "2025-04-04",
     "technician": "Priya Mehta", "iso14224_failure_mode": "VA-C-CAV",
     "findings": "Crackling noise confirmed from V-201 valve body during field walk. Vibration reading on valve body: 6.8 mm/s RMS. Trim inspection: 15% wear on plug, significant scoring on seat ring. Flow restriction estimated at 15% below Cv design. Active cavitation confirmed by acoustic emission probe.",
     "action_taken": "Trim replacement quoted — parts ordered. Installed downstream restriction orifice as temporary cavitation mitigation. Reduced valve opening from 78% to 65% to decrease ΔP.", "labour_hours": 8, "follow_up_wo": "WO-2025-1034"},
    {"id": "WO-2025-1034", "equipment_tag": "V-201", "title": "V-201 Trim Replacement — Follow-up to WO-2025-0891",
     "type": "CORRECTIVE", "status": "OPEN", "priority": "HIGH", "date_raised": "2025-04-10", "date_closed": None,
     "technician": "Rajesh Kumar", "iso14224_failure_mode": "VA-C-CAV",
     "findings": "Trim parts received. Replacement scheduled for next planned shutdown window (May 2025). Current workaround (reduced opening) limiting cavitation but not eliminating it. Vibration on P-101A discharge header remains elevated at 4.7 mm/s.",
     "action_taken": "Pending shutdown window — parts staged in warehouse.", "labour_hours": 0, "estimated_completion": "2025-05-15"},
    {"id": "WO-2025-0456", "equipment_tag": "P-101A", "title": "P-101A Vibration High Alarm Investigation",
     "type": "CORRECTIVE", "status": "CLOSED", "priority": "HIGH", "date_raised": "2025-02-20", "date_closed": "2025-02-21",
     "technician": "Suresh Nair", "iso14224_failure_mode": "PU-C-VIB",
     "findings": "Vibration alarm triggered at 4.5 mm/s RMS (alarm setpoint). Spectral analysis shows dominant peak at 47 Hz. Bearing temperature normal at 62°C. Alignment checked — within 0.05mm tolerance. Upstream V-201 identified as likely source.",
     "action_taken": "Increased vibration monitoring frequency to daily. Referred to V-201 WO-2025-0891 for upstream root cause. Bearing lubrication topped up.", "labour_hours": 4},
    {"id": "WO-2025-1102", "equipment_tag": "P-101A", "title": "P-101A Current Vibration Reading — Monitoring",
     "type": "CONDITION_MONITORING", "status": "OPEN", "priority": "HIGH", "date_raised": "2025-06-01", "date_closed": None,
     "technician": "Auto-generated (CMMS)", "iso14224_failure_mode": "PU-C-VIB",
     "findings": "VT-101 reading: 4.7 mm/s RMS. Dominant frequency: 47 Hz. Trend: steady increase over 6 weeks from baseline 2.1 mm/s. Drive-end bearing temperature: 68°C (elevated). ISO 10816 alarm zone B/C boundary approaching. Upstream cavitation from V-201 not yet resolved (WO-2025-1034 open).",
     "action_taken": "Escalated to maintenance supervisor. Contingency plan: switch to P-101B if vibration exceeds 6.0 mm/s.", "labour_hours": 1},
    {"id": "WO-2024-2234", "equipment_tag": "HE-301", "title": "HE-301 Annual Performance Assessment",
     "type": "PREVENTIVE", "status": "CLOSED", "priority": "LOW", "date_raised": "2024-11-01", "date_closed": "2024-11-03",
     "technician": "Anil Sharma", "iso14224_failure_mode": "HE-FOL",
     "findings": "Heat transfer effectiveness: 84% (design 92%). Pressure drop shell side: 1.8 bar (design 1.1 bar). Fouling factor estimated at 0.00018 m²K/W vs design 0.00012. Mild scaling observed on tube sheets. CW outlet temperature 2.3°C above design.",
     "action_taken": "Chemical clean scheduled for next opportunity. Water treatment program reviewed — dosage increased.", "labour_hours": 12},
    {"id": "WO-2024-1890", "equipment_tag": "P-101B", "title": "P-101B Standby Readiness Check",
     "type": "PREVENTIVE", "status": "CLOSED", "priority": "MEDIUM", "date_raised": "2024-09-15", "date_closed": "2024-09-15",
     "technician": "Deepa Rao", "iso14224_failure_mode": None,
     "findings": "P-101B bump test completed. Auto-start interlock verified. Vibration during test run: 1.8 mm/s (healthy). Bearing temperature: 58°C. Ready for standby service.",
     "action_taken": "Returned to standby mode. All interlocks confirmed.", "labour_hours": 2},
    {"id": "WO-2024-1203", "equipment_tag": "V-201", "title": "V-201 Positioner Calibration + Seat Inspection",
     "type": "PREVENTIVE", "status": "CLOSED", "priority": "LOW", "date_raised": "2024-07-10", "date_closed": "2024-07-10",
     "technician": "Rajesh Kumar", "iso14224_failure_mode": "VA-C-LEK",
     "findings": "Seat inspection: minor erosion on downstream face. Positioner recalibrated — 3% offset corrected. No cavitation signs at this inspection.",
     "action_taken": "Positioner calibrated. Seat erosion logged as initiation of trim wear trend.", "labour_hours": 3},
]

# ---- procedural work orders across the wider asset base ----------------------
WO_TEMPLATES = [
    ("PREVENTIVE", "LOW", "Routine {n}-month PM — {name}", "Executed planned maintenance checklist. All parameters within limits. No abnormality noted.", None),
    ("PREVENTIVE", "MEDIUM", "Lubrication & alignment check — {name}", "Re-greased bearings, verified coupling alignment to 0.04 mm. Vibration baseline re-recorded.", "EM-BRG"),
    ("CORRECTIVE", "MEDIUM", "Minor leak rectification — {name}", "Gland packing re-tightened, flange gasket replaced. Leak stopped. Monitor at next round.", "PU-C-LEK"),
    ("CONDITION_MONITORING", "MEDIUM", "Thermography survey — {name}", "IR survey completed. No hot spots above 10°C over ambient. Terminations sound.", None),
    ("CORRECTIVE", "HIGH", "High differential pressure — {name}", "Strainer/filter element found blocked. Cleaned and reinstalled. ΔP restored to normal.", "ST-BLK"),
    ("PREVENTIVE", "MEDIUM", "Dry-gas seal gas filter change — {name}", "Replaced seal-gas filter, verified vent flow. Seal parameters nominal.", "CO-C-SEAL"),
]
TAGS_FOR_WO = ["ST-101", "P-101B", "M-101A", "HE-301", "TK-401", "TK-501", "P-501", "F-501",
               "K-501", "M-501", "V-501", "FT-101", "PT-101", "P-101A", "V-201"]
NAMES = {e["tag"]: e["name"] for e in demo_graph["equipment"]}
TECHS = ["Rajesh Kumar", "Priya Mehta", "Suresh Nair", "Anil Sharma", "Deepa Rao", "Imran Sheikh", "Kavya Menon"]

wo_id = 1500
d0 = date(2023, 6, 1)
for i in range(22):
    tag = TAGS_FOR_WO[i % len(TAGS_FOR_WO)]
    typ, prio, title, findings, fm = random.choice(WO_TEMPLATES)
    raised = d0 + timedelta(days=random.randint(0, 900))
    closed = raised + timedelta(days=random.randint(0, 5))
    status = random.choice(["CLOSED", "CLOSED", "CLOSED", "OPEN"])
    work_orders.append({
        "id": f"WO-{raised.year}-{wo_id}", "equipment_tag": tag,
        "title": title.format(n=random.choice([3, 6, 12]), name=NAMES.get(tag, tag)),
        "type": typ, "status": status, "priority": prio,
        "date_raised": raised.isoformat(), "date_closed": None if status == "OPEN" else closed.isoformat(),
        "technician": random.choice(TECHS), "iso14224_failure_mode": fm,
        "findings": findings, "action_taken": "Work completed per procedure; equipment returned to service.",
        "labour_hours": random.randint(1, 10)})
    wo_id += 1
dump("work_orders.json", work_orders, "work orders")


# ══════════════════════════════════════════════════════════════════════════════
# 4. INSPECTION LOGS  (8 narrative + 42 procedural = 50)
# ══════════════════════════════════════════════════════════════════════════════
inspection_logs = [
    {"id": "INS-2025-0847", "equipment_tag": "V-201", "inspection_type": "CONDITION_MONITORING", "date": "2025-04-03",
     "inspector": "Priya Mehta", "iso14224_failure_mode_detected": "VA-C-CAV", "severity": "HIGH",
     "findings": "Active cavitation confirmed on V-201 during field inspection. Acoustic emission probe reading: 72 dB (cavitation threshold >65 dB). Cracking noise audible from 5m distance. Body vibration: 6.8 mm/s RMS. Valve trim photographed — 15% plug wear visible.",
     "recommendation": "Immediate trim replacement required. Temporary mitigation: reduce valve opening to decrease ΔP across trim.", "next_inspection": "2025-05-01"},
    {"id": "INS-2025-0312", "equipment_tag": "P-101A", "inspection_type": "VIBRATION_ANALYSIS", "date": "2025-03-15",
     "inspector": "Suresh Nair", "iso14224_failure_mode_detected": "PU-C-VIB", "severity": "MEDIUM",
     "findings": "Vibration spectrum analysis on P-101A. Overall: 3.8 mm/s RMS. Dominant peak at 47 Hz. Sub-synchronous components at 23.5 Hz detected. Bearing envelope spectrum normal — no bearing defect frequencies. Source likely external (upstream hydraulic excitation from V-201).",
     "recommendation": "Address upstream cavitation source (V-201). Re-assess after V-201 repair.", "next_inspection": "2025-04-15"},
    {"id": "INS-2025-0601", "equipment_tag": "P-101A", "inspection_type": "VIBRATION_ANALYSIS", "date": "2025-06-01",
     "inspector": "Suresh Nair", "iso14224_failure_mode_detected": "PU-C-VIB", "severity": "HIGH",
     "findings": "P-101A current condition: VT-101 reads 4.7 mm/s RMS. Trending upward from 2.1 (baseline) → 3.8 (Mar) → 4.7 (Jun). 47 Hz peak still dominant — consistent with hydraulic excitation from V-201 cavitation. Drive-end bearing temperature now 68°C (up from 58°C at baseline). ISO 10816 Zone B/C boundary. If V-201 not repaired, bearing failure expected within 3–5 weeks.",
     "recommendation": "URGENT: Expedite V-201 trim replacement (WO-2025-1034). Consider switching to P-101B immediately.", "next_inspection": "2025-06-15"},
    {"id": "INS-2024-1105", "equipment_tag": "V-201", "inspection_type": "VISUAL_INSPECTION", "date": "2024-11-05",
     "inspector": "Rajesh Kumar", "iso14224_failure_mode_detected": None, "severity": "LOW",
     "findings": "Routine inspection. No abnormal noise. Positioner operating correctly. Body vibration 1.2 mm/s (acceptable). Minor surface corrosion on bonnet — painted.",
     "recommendation": "Continue routine monitoring. Next full trim inspection at 12-month interval.", "next_inspection": "2025-05-01"},
    {"id": "INS-2024-0901", "equipment_tag": "P-101A", "inspection_type": "BASELINE_VIBRATION", "date": "2024-09-01",
     "inspector": "Deepa Rao", "iso14224_failure_mode_detected": None, "severity": "NONE",
     "findings": "Baseline vibration measurement post-overhaul. VT-101: 2.1 mm/s RMS (ISO 10816 Zone A — good). Spectrum clean. Bearing temperature 58°C. Alignment verified at 0.03mm. All readings within design parameters.",
     "recommendation": "Healthy baseline established. Standard monitoring schedule.", "next_inspection": "2025-03-01"},
    {"id": "INS-2024-0702", "equipment_tag": "HE-301", "inspection_type": "FOULING_ASSESSMENT", "date": "2024-07-02",
     "inspector": "Anil Sharma", "iso14224_failure_mode_detected": "HE-FOL", "severity": "MEDIUM",
     "findings": "Tube side outlet temperature deviation: +1.8°C from design setpoint. Shell-side pressure drop increased 45% from design. Video borescope of tube bundle shows light-to-moderate scale on tube sheets. Overall heat transfer coefficient down 12% from design.",
     "recommendation": "Chemical clean at next planned shutdown. Increase inhibitor dosing.", "next_inspection": "2024-11-01"},
    {"id": "INS-2023-1201", "equipment_tag": "P-101A", "inspection_type": "OVERHAUL_INSPECTION", "date": "2023-12-01",
     "inspector": "Suresh Nair", "iso14224_failure_mode_detected": "PU-C-BRG", "severity": "HIGH",
     "findings": "Pre-overhaul teardown. Drive-end bearing failure confirmed: inner race fatigue spalling, 40% loss of rolling element. Non-drive end bearing in good condition. Impeller clearance: 0.8mm (design 0.5mm — worn). Mechanical seal: replaced as precaution.",
     "recommendation": "Replace DE bearing, redress impeller, replace mechanical seal. Realign to motor.", "next_inspection": "2024-09-01"},
    {"id": "INS-2023-0820", "equipment_tag": "V-201", "inspection_type": "ACOUSTIC_EMISSION", "date": "2023-08-20",
     "inspector": "Priya Mehta", "iso14224_failure_mode_detected": "VA-C-CAV", "severity": "MEDIUM",
     "findings": "Acoustic emission survey. V-201 reads 61 dB AE — approaching cavitation threshold (65 dB). High frequency noise 38–42 kHz consistent with incipient cavitation. Trim visually normal at this stage.",
     "recommendation": "Monitor at 3-month intervals. Consider reducing operating ΔP if AE increases.", "next_inspection": "2023-11-20"},
    # Compressor-train narrative thread (a second robust scenario)
    {"id": "INS-2025-0505", "equipment_tag": "K-501", "inspection_type": "VIBRATION_ANALYSIS", "date": "2025-05-05",
     "inspector": "Imran Sheikh", "iso14224_failure_mode_detected": "CO-C-VIB", "severity": "MEDIUM",
     "findings": "K-501 outboard proximity probe reads 38 µm (alarm 50 µm). Sub-synchronous component at 0.45× running speed suggests incipient oil whirl. Lube-oil sample flagged particle count ISO 20/18/15 — above target. Upstream lube-oil filter F-501 ΔP elevated.",
     "recommendation": "Investigate lube-oil cleanliness and F-501 filter condition. Trend probe daily.", "next_inspection": "2025-05-20"},
    {"id": "INS-2025-0508", "equipment_tag": "F-501", "inspection_type": "CONDITION_MONITORING", "date": "2025-05-08",
     "inspector": "Kavya Menon", "iso14224_failure_mode_detected": "ST-BLK", "severity": "HIGH",
     "findings": "F-501 lube-oil filter differential pressure 2.1 bar vs 0.4 bar clean. Bypass indicator near activation — unfiltered oil risk to K-501 bearings. Element loaded with varnish and metallic particles.",
     "recommendation": "Change filter element immediately; escalate oil-cleanliness program. Root cause of K-501 vibration (INS-2025-0505).", "next_inspection": "2025-05-15"},
]

INS_TEMPLATES = [
    ("VISUAL_INSPECTION", "LOW", None, "Routine visual inspection. No leaks, no abnormal noise, guarding intact. Housekeeping satisfactory.", "Continue routine schedule."),
    ("VIBRATION_ANALYSIS", "LOW", None, "Overall vibration within ISO 10816 Zone A. Spectrum clean, no defect frequencies.", "Maintain current interval."),
    ("THICKNESS_SURVEY", "MEDIUM", "VE-COR", "UT thickness survey. Localised wall thinning 6% below nominal at bottom quadrant. Within retirement limit.", "Re-survey in 12 months; monitor water chemistry."),
    ("THERMOGRAPHY", "LOW", None, "IR thermography of motor terminations and bearings. No hotspots above 8°C over ambient.", "No action; next survey per plan."),
    ("LUBE_OIL_ANALYSIS", "MEDIUM", "EM-BRG", "Oil sample: viscosity nominal, water 120 ppm (slightly high), wear metals within limits.", "Investigate moisture ingress; resample in 1 month."),
    ("BASELINE_VIBRATION", "NONE", None, "Post-maintenance baseline recorded. All readings within design parameters.", "Healthy baseline established."),
]
TAGS_FOR_INS = ["TK-401", "ST-101", "P-101B", "M-101A", "HE-301", "TK-501", "P-501",
                "K-501", "M-501", "V-501", "VT-101", "FT-101", "PT-101", "P-101A", "V-201"]
ins_id = 400
d0 = date(2023, 3, 1)
for i in range(42):
    tag = TAGS_FOR_INS[i % len(TAGS_FOR_INS)]
    itype, sev, fm, findings, rec = random.choice(INS_TEMPLATES)
    dt = d0 + timedelta(days=random.randint(0, 1000))
    nxt = dt + timedelta(days=random.choice([90, 180, 365]))
    inspection_logs.append({
        "id": f"INS-{dt.year}-{ins_id}", "equipment_tag": tag, "inspection_type": itype,
        "date": dt.isoformat(), "inspector": random.choice(TECHS),
        "iso14224_failure_mode_detected": fm, "severity": sev,
        "findings": findings, "recommendation": rec, "next_inspection": nxt.isoformat()})
    ins_id += 1
dump("inspection_logs.json", inspection_logs, "inspection logs")


# ══════════════════════════════════════════════════════════════════════════════
# 5. COMPLIANCE CLAUSES  (Indian + international, mapped to equipment types)
# ══════════════════════════════════════════════════════════════════════════════
clauses = [
    {"id": "OISD-130-6.2", "standard": "OISD-STD-130", "title": "Inspection of Rotating Equipment",
     "authority": "Oil Industry Safety Directorate (India)", "applies_to": ["CENTRIFUGAL_PUMP", "CENTRIFUGAL_COMPRESSOR", "ELECTRIC_MOTOR"],
     "requirement": "Vibration and bearing-temperature monitoring of critical rotating equipment at defined intervals; records to be maintained and trended.",
     "evidence_required": ["VIBRATION_ANALYSIS", "CONDITION_MONITORING"], "max_interval_days": 90, "severity_on_gap": "HIGH"},
    {"id": "OISD-144-5.1", "standard": "OISD-STD-144", "title": "Inspection of Pressure Vessels & Storage",
     "authority": "Oil Industry Safety Directorate (India)", "applies_to": ["STORAGE_VESSEL", "HEAT_EXCHANGER"],
     "requirement": "Periodic thickness survey and internal/external inspection of vessels and exchangers to detect corrosion/thinning.",
     "evidence_required": ["THICKNESS_SURVEY", "FOULING_ASSESSMENT", "VISUAL_INSPECTION"], "max_interval_days": 365, "severity_on_gap": "HIGH"},
    {"id": "FACT-1948-21", "standard": "Factories Act 1948 §21", "title": "Fencing & Safe Condition of Machinery",
     "authority": "Ministry of Labour & Employment (India)", "applies_to": ["CENTRIFUGAL_PUMP", "CENTRIFUGAL_COMPRESSOR", "ELECTRIC_MOTOR"],
     "requirement": "Moving parts of prime movers and transmission machinery must be securely fenced and maintained in safe condition.",
     "evidence_required": ["VISUAL_INSPECTION"], "max_interval_days": 180, "severity_on_gap": "MEDIUM"},
    {"id": "PESO-SMPV-9", "standard": "PESO / SMPV(U) Rules", "title": "Pressure System Integrity",
     "authority": "Petroleum & Explosives Safety Organisation (India)", "applies_to": ["CENTRIFUGAL_COMPRESSOR", "STORAGE_VESSEL", "CONTROL_VALVE"],
     "requirement": "Pressure-containing systems handling hazardous fluids to be inspected and certified; relief and isolation devices tested.",
     "evidence_required": ["THICKNESS_SURVEY", "CONDITION_MONITORING"], "max_interval_days": 365, "severity_on_gap": "HIGH"},
    {"id": "ISO-10816-3", "standard": "ISO 10816-3", "title": "Mechanical Vibration Evaluation",
     "authority": "International Organization for Standardization", "applies_to": ["CENTRIFUGAL_PUMP", "CENTRIFUGAL_COMPRESSOR", "ELECTRIC_MOTOR"],
     "requirement": "Evaluation of machine vibration by measurements on non-rotating parts; operation beyond Zone C requires corrective action.",
     "evidence_required": ["VIBRATION_ANALYSIS", "BASELINE_VIBRATION"], "max_interval_days": 90, "severity_on_gap": "MEDIUM"},
    {"id": "API-610-lube", "standard": "API 610 / API 614", "title": "Lube-Oil System Cleanliness",
     "authority": "American Petroleum Institute", "applies_to": ["CENTRIFUGAL_COMPRESSOR"],
     "requirement": "Lube-oil systems for critical machinery to maintain specified cleanliness class; filtration ΔP monitored.",
     "evidence_required": ["LUBE_OIL_ANALYSIS", "CONDITION_MONITORING"], "max_interval_days": 90, "severity_on_gap": "HIGH"},
    {"id": "CPCB-WATER-3", "standard": "CPCB Consent Conditions", "title": "Cooling-Water Discharge Quality",
     "authority": "Central Pollution Control Board (India)", "applies_to": ["HEAT_EXCHANGER", "STORAGE_VESSEL"],
     "requirement": "Cooling-water treatment and blowdown to meet consent limits; scaling/biofouling controls documented.",
     "evidence_required": ["FOULING_ASSESSMENT"], "max_interval_days": 180, "severity_on_gap": "MEDIUM"},
]
dump("compliance_clauses.json", clauses, "compliance clauses")


# ══════════════════════════════════════════════════════════════════════════════
# 6. TELEMETRY  (condition-monitoring readings powering the HMI gauges/trends)
#    Values are consistent with the inspection-log narrative.
# ══════════════════════════════════════════════════════════════════════════════
telemetry = {
    "P-101A": {
        "parameter": "Radial Vibration", "unit": "mm/s RMS", "sensor": "VT-101",
        "current": 4.7, "alarm": 4.5, "trip": 7.1, "baseline": 2.1,
        "standard": "ISO 10816-3",
        "zones": [
            {"zone": "A", "label": "Good", "min": 0.0, "max": 2.8, "status": "ok"},
            {"zone": "B", "label": "Acceptable", "min": 2.8, "max": 4.5, "status": "normal"},
            {"zone": "C", "label": "Unsatisfactory", "min": 4.5, "max": 7.1, "status": "warn"},
            {"zone": "D", "label": "Unacceptable", "min": 7.1, "max": 11.2, "status": "crit"}
        ],
        "trend": [
            {"date": "2024-09-01", "value": 2.1}, {"date": "2024-12-01", "value": 2.4},
            {"date": "2025-03-15", "value": 3.8}, {"date": "2025-04-20", "value": 4.2},
            {"date": "2025-06-01", "value": 4.7}
        ],
        "dominant_hz": 47
    },
    "K-501": {
        "parameter": "Shaft Vibration", "unit": "µm pk-pk", "sensor": "VT-501",
        "current": 38, "alarm": 50, "trip": 75, "baseline": 18,
        "standard": "API 617",
        "zones": [
            {"zone": "A", "label": "Good", "min": 0, "max": 25, "status": "ok"},
            {"zone": "B", "label": "Acceptable", "min": 25, "max": 50, "status": "normal"},
            {"zone": "C", "label": "Alarm", "min": 50, "max": 75, "status": "warn"},
            {"zone": "D", "label": "Trip", "min": 75, "max": 100, "status": "crit"}
        ],
        "trend": [
            {"date": "2024-11-01", "value": 18}, {"date": "2025-02-01", "value": 22},
            {"date": "2025-04-01", "value": 30}, {"date": "2025-05-05", "value": 38}
        ],
        "dominant_hz": None
    },
    "HE-301": {
        "parameter": "Shell ΔP", "unit": "bar", "sensor": "PDT-301",
        "current": 1.8, "alarm": 1.5, "trip": 2.5, "baseline": 1.1,
        "standard": "TEMA",
        "zones": [
            {"zone": "A", "label": "Clean", "min": 0.0, "max": 1.3, "status": "ok"},
            {"zone": "B", "label": "Normal", "min": 1.3, "max": 1.5, "status": "normal"},
            {"zone": "C", "label": "Fouling", "min": 1.5, "max": 2.5, "status": "warn"},
            {"zone": "D", "label": "Blocked", "min": 2.5, "max": 3.5, "status": "crit"}
        ],
        "trend": [
            {"date": "2024-01-01", "value": 1.1}, {"date": "2024-07-02", "value": 1.5},
            {"date": "2024-11-01", "value": 1.8}
        ],
        "dominant_hz": None
    }
}
dump("telemetry.json", telemetry, "telemetry")


# ══════════════════════════════════════════════════════════════════════════════
# 7. SAMPLE RAW DOCUMENTS  (heterogeneous formats for the ingestion demo)
#    Each carries embedded entities — equipment tags, dates, personnel,
#    regulatory references, process parameters, failure terms — for extraction.
# ══════════════════════════════════════════════════════════════════════════════
sample_documents = [
    {"id": "SAMPLE-INSPECTION", "doc_type": "Inspection Report", "format": "PDF / scanned form",
     "expected_tags": ["P-101A", "VT-101", "V-201"],
     "title": "Vibration inspection — cooling water pump",
     "text": "INSPECTION REPORT\nDate: 2025-06-01\nInspector: Suresh Nair\nEquipment: P-101A (Cooling Water Pump A)\n"
             "Finding: VT-101 radial vibration measured at 4.7 mm/s RMS, dominant frequency 47 Hz. Drive-end bearing "
             "temperature 68 °C. Trend rising from 2.1 mm/s baseline. ISO 10816-3 Zone C. Suspected upstream hydraulic "
             "excitation from control valve V-201 cavitation. Recommend expediting V-201 trim replacement per OISD-STD-130 "
             "rotating-equipment monitoring requirements. Next inspection due 2025-06-15."},
    {"id": "SAMPLE-EMAIL", "doc_type": "Email Archive", "format": ".mbox / .eml", "expected_tags": ["V-201", "P-101A"],
     "title": "RE: V-201 noise complaint — shutdown planning",
     "text": "From: Priya Mehta <priya.mehta@octaveplant.in>\nTo: Rajesh Kumar\nDate: 2025-04-04\nSubject: RE: V-201 noise\n\n"
             "Rajesh — confirmed crackling/cavitation on V-201 during today's field walk. Body vibration 6.8 mm/s, acoustic "
             "emission 72 dB. Trim is ~15% worn. I've raised WO-2025-0891. We need the trim replacement in the May shutdown "
             "window. This is now driving elevated vibration on P-101A downstream. Please stage parts. — Priya"},
    {"id": "SAMPLE-MANUAL", "doc_type": "OEM Manual", "format": "PDF (text)", "expected_tags": [],
     "title": "Centrifugal pump O&M manual — vibration limits",
     "text": "SECTION 7 — CONDITION MONITORING\nModel: HES-350 end-suction centrifugal pump\nPer ISO 10816-3, alarm at "
             "4.5 mm/s RMS and trip at 7.1 mm/s RMS for this machine class. Sustained operation above 4.5 mm/s indicates "
             "misalignment, unbalance, cavitation or bearing wear. Inspect suction strainer and upstream control valve for "
             "cavitation. Bearing temperature should not exceed 80 °C. Refer failure modes PU-C-VIB and PU-C-BRG."},
    {"id": "SAMPLE-REGULATORY", "doc_type": "Regulatory Submission", "format": "PDF (form)", "expected_tags": ["P-101A", "P-101B", "K-501", "M-101A", "M-501"],
     "title": "OISD-STD-130 compliance declaration — rotating equipment",
     "text": "COMPLIANCE DECLARATION — OISD-STD-130\nFacility: Octave Demo Plant, Area A-01\nClause 6.2 requires vibration "
             "and bearing-temperature monitoring of critical rotating equipment at intervals not exceeding 90 days, with "
             "trended records maintained. Equipment in scope: P-101A, P-101B, K-501, M-101A, M-501. Prepared by Anil Sharma, "
             "2025-05-20. Also references Factories Act 1948 §21 and PESO SMPV(U) Rules for pressure systems."},
    {"id": "SAMPLE-INCIDENT", "doc_type": "Incident / Near-Miss", "format": "Scanned form + OCR", "expected_tags": ["HE-301", "P-101A", "P-101B"],
     "title": "Near-miss — heat exchanger fouling excursion",
     "text": "NEAR-MISS RECORD\nDate: 2024-11-01\nReported by: Anil Sharma\nEquipment: HE-301 (Process Cooling Heat Exchanger)\n"
             "Shell-side pressure drop rose to 1.8 bar versus 1.1 bar design; CW outlet temperature +2.3 °C. Fouling factor "
             "elevated. Root cause: inadequate water treatment. Failure mode HE-FOL. Recommend chemical clean and CPCB "
             "cooling-water quality review. Potential downstream impact on P-101A/B effective head."},
    {"id": "SAMPLE-HANDOVER", "doc_type": "Shift Handover / Tribal", "format": "Free text", "expected_tags": ["P-101A", "V-201", "VT-101", "P-101B"],
     "title": "Night-shift handover note",
     "text": "HANDOVER — Night Shift, 2025-06-01, Operator: Deepa Rao\nWatch P-101A — vibration creeping up (4.7 mm/s tonight). "
             "Old trick from the retiring foreman: after any V-201 cavitation event, always re-clearance the P-101A impeller, "
             "it never seats right otherwise. If VT-101 crosses 6.0, switch to P-101B before it trips at 7.1."},
]
dump("sample_documents.json", sample_documents, "sample documents")

print("\nSeed generation complete.")
print(f"  equipment={len(demo_graph['equipment'])}  work_orders={len(work_orders)}  "
      f"inspections={len(inspection_logs)}  clauses={len(clauses)}  "
      f"failure_modes={sum(len(c['failure_modes']) for c in iso14224['equipment_classes'])}")

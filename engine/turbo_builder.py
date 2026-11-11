import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/turbo-injector-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8").strip()
CUSTOM_TURBO = os.environ.get("CUSTOM_TURBO", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_turbos.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Build / Turbo / Injector Scenario, Target Crank HP, Cylinders, BSFC [0.55 Gas / 0.72 E85], Boost PSI, Fuel Type, Turbo Frame Spec)
SEED_TURBOS = [
    ("5.3L / 6.0L Chevy LS Turbo (650 HP on E85 Flex-Fuel)", 650, 8, 0.72, 14, "E85 Ethanol", "7875 Billet T4 (0.96 A/R)"),
    ("5.3L / 6.0L Chevy LS Turbo (800 HP on E85 Flex-Fuel)", 800, 8, 0.72, 18, "E85 Ethanol", "BorgWarner S475 / S480 T4/T6"),
    ("5.3L / 6.0L Chevy LS Turbo (550 HP on 93 Octane Pump Gas)", 550, 8, 0.55, 11, "93 Octane Gas", "VS Racing 7875 / GT45 T4"),
    ("Ford 5.0L Coyote Twin-Turbo / Whipple (750 HP on E85)", 750, 8, 0.72, 14, "E85 Ethanol", "Twin 6262 / 3.0L Supercharger"),
    ("Honda K20 / K24 Turbo 4-Cylinder (500 HP on E85)", 500, 4, 0.72, 22, "E85 Ethanol", "GTX3076R / GT3582R (0.82 A/R)"),
    ("Honda K20 / K24 & B18C Turbo (400 HP on 93 Octane)", 400, 4, 0.55, 16, "93 Octane Gas", "GTX3071R / GT2871R Ball-Bearing"),
    ("Toyota 2JZ-GTE / 1JZ-GTE Single Turbo (700 HP on E85)", 700, 6, 0.72, 24, "E85 Ethanol", "Precision 6466 / BorgWarner S366"),
    ("BMW B58 / N54 / N55 Single & Hybrid Turbo (600 HP on E85)", 600, 6, 0.72, 22, "E85 Ethanol", "Pure 800 / Pulsar GTX3582R"),
    ("Subaru EJ257 WRX STI Turbo (450 HP on E85 Flex-Fuel)", 450, 4, 0.72, 21, "E85 Ethanol", "FP Blue/Green / GTX3076R"),
    ("Garrett GT3582R & GTX3582R Gen II (600–750 HP) Sizing", 650, 6, 0.72, 20, "E85 Ethanol", "62mm Inducer / 82mm Exducer"),
    ("Garrett GTX3076R Gen II (450–600 HP) Airflow & Injector", 525, 4, 0.72, 20, "E85 Ethanol", "58mm Inducer / 76mm Exducer"),
    ("Garrett GT2860RS (Disco Potato) & GTX2867R (350–450 HP)", 380, 4, 0.55, 16, "93 Octane Gas", "50mm Inducer / T25 V-Band"),
    ("BorgWarner AirWerks S366 SX-E (66mm — 550 to 800 HP)", 700, 6, 0.72, 22, "E85 Ethanol", "66mm Inducer / 0.91 Divided T4"),
    ("BorgWarner AirWerks S475 & S480 (75mm/80mm — 750 to 1,100 HP)", 900, 8, 0.72, 20, "E85 Ethanol", "75mm Inducer / 1.10 T4 / 1.32 T6"),
    ("VS Racing & Pulsar 7875 Billet Gen 2.5 (550 to 850 HP LS)", 750, 8, 0.72, 16, "E85 Ethanol", "78mm Inducer / 75mm Turbine T4"),
    ("GT45 T4 Flange Budget Turbo (450 to 650 HP V8 / I6)", 550, 8, 0.55, 12, "93 Octane Gas", "69mm Inducer / 1.05 A/R T4"),
    ("Walbro 450 LPH (F90000267 / 274) E85 Fuel Pump HP Limit", 650, 8, 0.72, 16, "E85 Ethanol", "Single vs Dual 450 LPH In-Tank"),
    ("Walbro 525 LPH Hellcat (F90000285) E85 Fuel Pump HP Limit", 780, 8, 0.72, 18, "E85 Ethanol", "TI Automotive 525 LPH In-Tank"),
    ("Walbro 255 LPH (GSS342) vs Aeromotive 340 Stealth HP Limit", 480, 8, 0.55, 12, "93 Octane Gas", "255 LPH / 340 LPH In-Tank"),
    ("Dual Bosch 044 / AEM 400 LPH Inline Fuel Pump Surge Tank", 1000, 8, 0.72, 24, "E85 Ethanol", "-8AN Feed / -6AN Return"),
    ("1000cc (95 lb/hr) Fuel Injectors Max Horsepower (Gas vs E85)", 700, 8, 0.72, 16, "E85 Ethanol", "EV14 High-Impedance 1000cc"),
    ("850cc (80 lb/hr) Fuel Injectors Max Horsepower (Gas vs E85)", 600, 8, 0.72, 14, "E85 Ethanol", "Siemens Deka / Bosch 80 lb/hr"),
    ("1300cc (125 lb/hr) & 1500cc Fuel Injectors E85 HP Limit", 950, 8, 0.72, 22, "E85 Ethanol", "ID1300x / Bosch 1300cc E85"),
    ("650cc (60 lb/hr) Fuel Injectors Max Horsepower Calculator", 500, 8, 0.55, 12, "93 Octane Gas", "60 lb/hr EV1 / EV6 / EV14"),
    ("2,200cc (210 lb/hr) Race Fuel & Methanol Injector Sizing", 1200, 8, 0.75, 28, "E85 / Methanol", " Bosch 210 lb/hr High-Z"),
    ("5.7L / 6.4L Dodge Hemi Turbo & Hellcat Supercharger Fueling", 750, 8, 0.72, 15, "E85 Ethanol", "1050cc Injectors + Dual Pumps"),
    ("Mazda Miata BP 1.8L & Ford EcoBoost 2.3L Turbo Sizing", 350, 4, 0.58, 16, "93 Octane Gas", "GTX2860R / GT2871R (0.64 A/R)"),
    ("Nissan SR20DET, RB25DET & VQ35DE Turbo Injector Sizing", 500, 6, 0.68, 18, "E85 Ethanol", "GTX3076R / S362 SX-E"),
    ("VW/Audi EA888 2.0T & VR6 3.2L Big-Turbo Fueling Calculator", 550, 6, 0.72, 22, "E85 Ethanol", "GTX3576R / Precision 6266"),
    ("Front-Mount Intercooler (FMIC) Core Volume & Charge Pipe Size", 650, 8, 0.70, 16, "E85 Ethanol", "24\"×12\"×4\" Bar-and-Plate Core")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=600.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Model Free Tier Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_turbo_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Engine × HP × Fuel Permutator.
    """
    discovered = []
    seeds = [
        "what size injectors for ",
        "fuel injector calculator ",
        "turbo size calculator for ",
        "walbro 450 hp limit "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        hp_m = re.search(r"\b(300|350|400|450|500|550|600|650|700|750|800|900|1000)\b", cleaned)
                        hp_v = int(hp_m.group(1)) if hp_m else 600
                        cyl_v = 4 if hp_v <= 450 else 8
                        discovered.append((cleaned.title(), hp_v, cyl_v, 0.70, 16, "E85 / 93 Octane", "Billet Ball-Bearing Turbo"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    engine_configs = [
        (4, "4-Cylinder Turbo Engine"),
        (6, "6-Cylinder Inline/V6 Turbo"),
        (8, "8-Cylinder V8 Turbo/Supercharged")
    ]
    hp_targets = [350, 450, 550, 650, 750, 850, 1000]
    fuels = [
        ("93 Octane Pump Gas", 0.55, 12),
        ("E85 Ethanol Flex-Fuel", 0.72, 18)
    ]
    for cyl_c, eng_desc in engine_configs:
        for hp_t in hp_targets:
            if cyl_c == 4 and hp_t > 750:
                continue
            if cyl_c == 8 and hp_t < 450:
                continue
            for f_name, bsfc_v, bst_psi in fuels:
                combo_title = f"{hp_t} HP {eng_desc} on {f_name}"
                test_slug = slugify(f"{combo_title}-injector-turbo-pump-calculator")
                if test_slug not in published_slugs:
                    t_frame = "GTX3076R / GT3582R" if hp_t <= 600 else ("7875 Billet / S366" if hp_t <= 800 else "BorgWarner S475 / S480")
                    discovered.append((combo_title, hp_t, cyl_c, bsfc_v, bst_psi, f_name, t_frame))
                    if len(discovered) >= 25:
                        return discovered
    return discovered


def build_deterministic_turbo_data(trb_tuple):
    """
    LAPIS 3: Mesin Fisika BSFC Injector (80% IDC), Compressor Map lb/min & High-Pressure LPH Fuel Pump (100% Bebas Gagal).
    """
    build_name, target_hp, cylinders, bsfc, boost_psi, fuel_type, turbo_spec = trb_tuple

    # 1. Aliran Udara Kompresor Turbo (Mass Airflow lb/min & Volumetric CFM):
    # Rata-rata 10.0 HP per 1.0 lb/min udara (BSAC = 0.10 lb/hp-min); 1 lb/min udara standar = 14.27 CFM
    airflow_lb_min = round(target_hp * 0.10, 1)
    airflow_cfm = int(round(airflow_lb_min * 14.27, -1))
    # Pressure Ratio (PR = (14.7 + Boost_PSI + 2.0_Intercooler_Drop) / 14.7):
    pressure_ratio = round((14.7 + boost_psi + 2.0) / 14.7, 2)

    # 2. Ukuran Fuel Injector pada Batas Aman 80% Injector Duty Cycle (IDC) & Tekanan Rel Standar 43.5 PSI (3 Bar):
    # Injector lb/hr = (Target_HP * BSFC) / (Cylinders * 0.80)
    inj_lb_hr = int(round((target_hp * bsfc) / (cylinders * 0.80)))
    inj_cc_min = int(round((inj_lb_hr * 10.5), -1))

    # 3. Ukuran Pompa Bensin (LPH pada Tekanan Boost 43.5 PSI Base + Boost_PSI):
    # Total LPH = ((Target_HP * BSFC * 0.4536 kg/lb) / 0.745 kg/L) * 1.22 Safety Headroom at High Rail Pressure
    total_fuel_lph = int(round(((target_hp * bsfc * 0.4536) / 0.745) * 1.22, -1))
    rail_pressure_at_boost_psi = int(round(43.5 + boost_psi))

    if total_fuel_lph <= 230:
        pump_recommendation = "Single 255 LPH / 340 LPH In-Tank Pump (Walbro GSS342 / Aeromotive 340)"
    elif total_fuel_lph <= 360:
        pump_recommendation = "Single Walbro 450 LPH (F90000274) or 525 LPH Hellcat (F90000285) E85 Pump"
    else:
        pump_recommendation = "Dual Walbro 450/525 LPH In-Tank Pumps + -8AN PTFE Feed / -6AN Return"

    charge_pipe_in = "2.5-Inch Aluminum" if target_hp <= 550 else "3.0-Inch Aluminum"

    return {
        "build_name": build_name,
        "turbo_spec": turbo_spec,
        "seo_title": f"{build_name} Injector Size (cc/lb), Turbo CFM & Fuel Pump Calculator (2026)",
        "meta_description": f"Calculate exact fuel injector size ({inj_cc_min:,} cc/min / {inj_lb_hr} lb/hr @ 80% IDC), turbocharger airflow ({airflow_lb_min} lb/min / {airflow_cfm:,} CFM @ {pressure_ratio} PR), and {total_fuel_lph} LPH fuel pump for {build_name}.",
        "specs": {
            "target_crank_hp": target_hp,
            "cylinder_count": cylinders,
            "fuel_type": fuel_type,
            "bsfc_factor": bsfc,
            "boost_pressure_psi": boost_psi,
            "compressor_pressure_ratio": pressure_ratio,
            "turbo_airflow_lb_min": airflow_lb_min,
            "turbo_airflow_cfm": airflow_cfm,
            "injector_flow_cc_min": inj_cc_min,
            "injector_flow_lb_hr": inj_lb_hr,
            "required_pump_lph_at_boost": total_fuel_lph,
            "rail_pressure_under_boost_psi": rail_pressure_at_boost_psi,
            "recommended_pump_setup": pump_recommendation,
            "charge_pipe_spec": charge_pipe_in,
            "turbo_frame_spec": turbo_spec
        },
        "dyno_verdict": f"Supporting {target_hp:,} Crank HP (~{int(round(target_hp * 0.85)):,} WHP) across {cylinders} cylinders on {fuel_type} ({bsfc} BSFC at {boost_psi} PSI boost / {pressure_ratio}:1 compressor pressure ratio) requires {airflow_lb_min} lb/min ({airflow_cfm:,} CFM) of turbocharger airflow ({turbo_spec}). To keep Injector Duty Cycle (IDC) safely at or below 80% at 43.5 PSI (3-Bar) base pressure, install a matched set of {cylinders}× {inj_cc_min:,} cc/min ({inj_lb_hr} lb/hr) high-impedance fuel injectors fed by at least {total_fuel_lph} LPH of fuel pump capacity at {rail_pressure_at_boost_psi} PSI total rail pressure ({pump_recommendation}).",
        "hardware_bundle": [
            {
                "badge": f"{inj_cc_min:,}cc ({inj_lb_hr} lb/hr) Set of {cylinders}",
                "title": f"Matched Set of {cylinders}× {inj_cc_min:,}cc ({inj_lb_hr} lb/hr) EV14 High-Impedance Fuel Injectors (Gas & E85 Compatible)",
                "price_range": "$259 - $899",
                "amazon_query": f"{inj_cc_min}cc {inj_lb_hr} lb hr Fuel Injectors Set of {cylinders} E85 Bosch DeatschWerks",
                "trb_note": f" stainless internals resist E85 corrosion and hold {target_hp:,} HP at a safe 80% duty cycle without leaning out."
            },
            {
                "badge": f"{airflow_lb_min} lb/min ({target_hp} HP) Turbo",
                "title": f"{turbo_spec} Billet-Wheel Turbocharger + V-Band / T4 Exhaust Housing",
                "price_range": "$329 - $1,699",
                "amazon_query": f"{turbo_spec} Billet Turbocharger T4 V Band",
                "trb_note": f"Flows {airflow_lb_min}+ lb/min ({airflow_cfm:,} CFM) in the 74% adiabatic efficiency island at {pressure_ratio}:1 pressure ratio."
            },
            {
                "badge": f"{total_fuel_lph}+ LPH E85 Pump & FPR",
                "title": "TI Automotive Walbro 450 / 525 LPH E85 In-Tank Fuel Pump + Boost-Referenced EFI Fuel Pressure Regulator",
                "price_range": "$139 - $389",
                "amazon_query": "Walbro 450 525 LPH E85 Fuel Pump Kit EFI Fuel Pressure Regulator AN6",
                "trb_note": f"Maintains 1:1 rising fuel pressure ({rail_pressure_at_boost_psi} PSI at {boost_psi} PSI boost) so injector flow never drops under boost."
            },
            {
                "badge": "FMIC, Wastegate & Wideband",
                "title": f"Bar-and-Plate Front-Mount Intercooler + 44mm/50mm V-Band Wastegate & AEM X-Series Wideband AFR Gauge",
                "price_range": "$179 - $499",
                "amazon_query": "Front Mount Intercooler 3 Inch Piping Kit 44mm Wastegate AEM Wideband Gauge",
                "trb_note": "Drops intake air temperatures (IAT) by 110°F+ and monitors real-time Lambda/AFR to save pistons from detonation."
            }
        ],
        "tuner_checklist": [
            f"Never Size Fuel Injectors Above 80% Duty Cycle (IDC): above 85%–90% IDC, the injector pintle cannot fully close between intake strokes, going static and losing pulse-width control. For {target_hp} HP on {fuel_type} ({bsfc} BSFC), use {inj_cc_min:,} cc/min ({inj_lb_hr} lb/hr) injectors.",
            f"Account for Boost Pressure on Your Fuel Pump Curve: with a 1:1 boost-referenced regulator at 43.5 PSI base pressure plus {boost_psi} PSI boost, your fuel pump must push against {rail_pressure_at_boost_psi} PSI! A pump that flows 450 LPH at 40 PSI drops to ~340 LPH at 65 PSI.",
            "Run a Dedicated 10 AWG Direct Battery Relay Wire (Hotwire Kit) to high-output 450/525 LPH fuel pumps: stock 16 AWG factory fuel pump wires drop 2.0+ volts at 18 Amps, cutting fuel pump output by 25% right at peak boost.",
            "Add 30%–35% Extra Injector & Pump Capacity When Switching from 93 Octane Gas (0.55 BSFC) to E85 Ethanol (0.72 BSFC): E85 has a stoichiometric air-fuel ratio of 9.8:1 (vs. 14.7:1 for gasoline) and requires 33% more liquid volume under boost."
        ],
        "faqs": [
            {
                "q": f"What size fuel injectors do I need for {build_name} ({target_hp} HP)?",
                "a": f"Using the forced-induction BSFC formula ($\\text{{lb/hr}} = [\\text{{HP}} \\times \\text{{BSFC}}] \\div [\\text{{Cylinders}} \\times 0.80\\text{{ IDC}}]$), {target_hp} HP × {bsfc} BSFC ÷ ({cylinders} cylinders × 0.80) equals {inj_lb_hr} lb/hr ({inj_cc_min:,} cc/min) per injector at 43.5 PSI base fuel pressure."
            },
            {
                "q": f"How many lb/min and CFM of turbo airflow does {target_hp} HP require?",
                "a": f"A modern turbocharged engine produces approximately 10 Crank HP per 1.0 lb/min of mass airflow. Reaching {target_hp} HP requires ~{airflow_lb_min} lb/min ({airflow_cfm:,} CFM) at a compressor pressure ratio of {pressure_ratio}:1 ({boost_psi} PSI manifold boost)."
            },
            {
                "q": f"What size LPH fuel pump do I need for {target_hp} HP on {fuel_type}?",
                "a": f"At {target_hp} HP and {bsfc} BSFC, your injectors consume ~{int(round(total_fuel_lph / 1.22))} LPH at wide-open throttle. Adding a 22% safety buffer at {rail_pressure_at_boost_psi} PSI rail pressure requires {total_fuel_lph} LPH ({pump_recommendation})."
            }
        ]
    }


def generate_turbo_data(trb_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_turbo_data(trb_tuple)

    build_name, target_hp, cylinders, bsfc, boost_psi, fuel_type, turbo_spec = trb_tuple
    det_fallback = build_deterministic_turbo_data(trb_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a SAE Certified Forced-Induction Motorsport Engine Builder & EFI Calibration Engineer. Create an accurate 2026 turbocharger airflow (lb/min & CFM), BSFC fuel injector sizing (cc/min & lb/hr at 80% IDC), and high-pressure LPH fuel pump guide for: "{build_name}".
Baseline specs: Target Power={target_hp} Crank HP ({cylinders} Cylinders on {fuel_type}, BSFC={bsfc}), Boost={boost_psi} PSI (Pressure Ratio={sp['compressor_pressure_ratio']}:1), Turbo Airflow={sp['turbo_airflow_lb_min']} lb/min ({sp['turbo_airflow_cfm']} CFM, {turbo_spec}), Required Injectors @ 80% IDC={sp['injector_flow_cc_min']} cc/min ({sp['injector_flow_lb_hr']} lb/hr), Fuel Pump @ {sp['rail_pressure_under_boost_psi']} PSI Rail={sp['required_pump_lph_at_boost']} LPH ({sp['recommended_pump_setup']}).
Return ONLY a valid JSON object matching this exact schema:
{{
  "build_name": "{build_name}",
  "turbo_spec": "{turbo_spec}",
  "seo_title": "{build_name} Injector Size (cc/lb), Turbo CFM & Fuel Pump Calculator (2026)",
  "meta_description": "Calculate exact fuel injector cc/min and lb/hr at 80% duty cycle, turbocharger lb/min and CFM airflow, and LPH fuel pump sizing for {build_name}.",
  "specs": {{
    "target_crank_hp": {target_hp},
    "cylinder_count": {cylinders},
    "fuel_type": "{fuel_type}",
    "bsfc_factor": {bsfc},
    "boost_pressure_psi": {boost_psi},
    "compressor_pressure_ratio": {sp['compressor_pressure_ratio']},
    "turbo_airflow_lb_min": {sp['turbo_airflow_lb_min']},
    "turbo_airflow_cfm": {sp['turbo_airflow_cfm']},
    "injector_flow_cc_min": {sp['injector_flow_cc_min']},
    "injector_flow_lb_hr": {sp['injector_flow_lb_hr']},
    "required_pump_lph_at_boost": {sp['required_pump_lph_at_boost']},
    "rail_pressure_under_boost_psi": {sp['rail_pressure_under_boost_psi']},
    "recommended_pump_setup": "{sp['recommended_pump_setup']}",
    "charge_pipe_spec": "{sp['charge_pipe_spec']}",
    "turbo_frame_spec": "{turbo_spec}"
  }},
  "dyno_verdict": "3-sentence technical summary stating turbo airflow in lb/min and CFM at {sp['compressor_pressure_ratio']}:1 pressure ratio, required injector size in cc/min and lb/hr at 80% duty cycle, and LPH fuel pump requirement at {sp['rail_pressure_under_boost_psi']} PSI rail pressure.",
  "hardware_bundle": [
    {{
      "badge": "{sp['injector_flow_cc_min']:,}cc ({sp['injector_flow_lb_hr']} lb/hr) Injectors",
      "title": "Matched Set of {cylinders}× {sp['injector_flow_cc_min']:,}cc ({sp['injector_flow_lb_hr']} lb/hr) High-Z Fuel Injectors (Gas & E85)",
      "price_range": "$259 - $899",
      "amazon_query": "{sp['injector_flow_cc_min']}cc {sp['injector_flow_lb_hr']} lb hr Fuel Injectors Set of {cylinders} E85",
      "trb_note": "1-sentence 80% duty cycle and E85 stainless compatibility note"
    }},
    {{
      "badge": "{sp['turbo_airflow_lb_min']} lb/min ({target_hp} HP) Turbo",
      "title": "{turbo_spec} Billet-Wheel Turbocharger + V-Band / T4 Housing",
      "price_range": "$329 - $1,699",
      "amazon_query": "{turbo_spec} Billet Turbocharger T4 V Band",
      "trb_note": "1-sentence compressor map efficiency and spool note"
    }},
    {{
      "badge": "{sp['required_pump_lph_at_boost']}+ LPH E85 Pump & FPR",
      "title": "Walbro 450 / 525 LPH E85 In-Tank Fuel Pump + Boost-Referenced EFI Regulator",
      "price_range": "$139 - $389",
      "amazon_query": "Walbro 450 525 LPH E85 Fuel Pump Kit EFI Fuel Pressure Regulator",
      "trb_note": "1-sentence 1:1 boost-referenced rail pressure note"
    }},
    {{
      "badge": "FMIC, Wastegate & Wideband",
      "title": "Bar-and-Plate Front-Mount Intercooler + 44mm/50mm Wastegate & AEM Wideband AFR Gauge",
      "price_range": "$179 - $499",
      "amazon_query": "Front Mount Intercooler Piping Kit 44mm Wastegate AEM Wideband",
      "trb_note": "1-sentence charge cooling and AFR safety monitoring note"
    }}
  ],
  "tuner_checklist": [
    "Step 1 regarding 80% max Injector Duty Cycle (IDC) to prevent static injector lockup",
    "Step 2 regarding 1:1 boost-referenced fuel pressure (43.5 PSI base + {boost_psi} PSI boost = {sp['rail_pressure_under_boost_psi']} PSI)",
    "Step 3 regarding 10 AWG fuel pump relay hotwire kit to prevent voltage drop under boost",
    "Step 4 regarding +33% fuel volume increase when switching from 93 octane gas to E85"
  ],
  "faqs": [
    {{"q": "What size fuel injectors do I need for {build_name}?", "a": "Exact BSFC formula in lb/hr and cc/min at 80% duty cycle."}},
    {{"q": "How many lb/min and CFM of turbo airflow does {target_hp} HP require?", "a": "Exact lb/min, CFM, boost PSI, and compressor pressure ratio."}},
    {{"q": "Will a single Walbro 450 or 525 LPH fuel pump support {target_hp} HP on {fuel_type}?", "a": "Exact LPH required at {sp['rail_pressure_under_boost_psi']} PSI rail pressure vs single/dual pump output."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{build_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{build_name}': {e}")
                break

    return det_fallback


def build_turbo_html_page(data, slug, mon_cfg):
    build_name = data.get("build_name", "Turbocharger & Fuel Injector Setup")
    sp = data.get("specs", {})
    hp = int(safe_float(sp.get("target_crank_hp", 650), 650))
    cyl = int(safe_float(sp.get("cylinder_count", 8), 8))
    bsfc = round(safe_float(sp.get("bsfc_factor", 0.72), 0.72), 2)
    boost_p = int(safe_float(sp.get("boost_pressure_psi", 16), 16))
    pr_rat = round(safe_float(sp.get("compressor_pressure_ratio", 2.22), 2.22), 2)
    lb_min = round(safe_float(sp.get("turbo_airflow_lb_min", 65.0), 65.0), 1)
    cfm = int(safe_float(sp.get("turbo_airflow_cfm", 930), 930))
    cc_min = int(safe_float(sp.get("injector_flow_cc_min", 820), 820))
    lb_hr = int(safe_float(sp.get("injector_flow_lb_hr", 78), 78))
    lph = int(safe_float(sp.get("required_pump_lph_at_boost", 350), 350))
    trb_s = sp.get("turbo_frame_spec", "7875 Billet / S366")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Turbocharger+1000cc+Fuel+Injectors+Walbro+450+Fuel+Pump"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{build_name} Injector, Turbo Airflow & Fuel Pump Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "1000cc Fuel Injectors Turbo")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-red-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Boost Hardware')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$139+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🏎️ {item.get('trb_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-red-500 hover:bg-red-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Injector Size vs Max Horsepower (4-Cyl, 6-Cyl, 8-Cyl on 93 Gas vs E85) Reference Matrix Table
    inj_tiers = [
        ("550cc (52 lb/hr)", "300 HP Gas / 230 HP E85", "450 HP Gas / 345 HP E85", "600 HP Gas / 460 HP E85", "Walbro 255 / 340 LPH"),
        ("650cc (62 lb/hr)", "360 HP Gas / 275 HP E85", "540 HP Gas / 410 HP E85", "720 HP Gas / 550 HP E85", "Aeromotive 340 / Walbro 450"),
        ("850cc (80 lb/hr)", "465 HP Gas / 355 HP E85", "700 HP Gas / 530 HP E85", "930 HP Gas / 710 HP E85", "Walbro 450 LPH E85"),
        ("1000cc (95 lb/hr)", "550 HP Gas / 420 HP E85", "825 HP Gas / 630 HP E85", "1,100 HP Gas / 840 HP E85", "Walbro 525 Hellcat / Dual 450"),
        ("1300cc (125 lb/hr)", "725 HP Gas / 555 HP E85", "1,080 HP Gas / 830 HP E85", "1,450 HP Gas / 1,110 HP E85", "Dual Walbro 450/525 LPH"),
        ("1500cc (142 lb/hr)", "825 HP Gas / 630 HP E85", "1,240 HP Gas / 945 HP E85", "1,650 HP Gas / 1,260 HP E85", "Dual 525 LPH / Mechanical")
    ]
    matrix_rows_html = ""
    for i_lbl, c4_lbl, c6_lbl, c8_lbl, p_lbl in inj_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{i_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{c4_lbl}</td>
          <td class="py-3 px-4 font-bold text-red-400">{c6_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{c8_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{p_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("tuner_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-red-500 rounded cursor-pointer trb-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>EFI Dyno Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', build_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', build_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-red-500 text-zinc-950 px-2 py-0.5 rounded font-black">TURBO</span>InjectorIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-red-500 hover:bg-red-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Turbos, Injectors & Pumps →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-red-500 text-zinc-950 px-3 py-1 rounded-full">{cc_min:,}cc ({lb_hr} lb/hr) × {cyl} Injectors</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Turbo: {lb_min} lb/min ({cfm:,} CFM @ {pr_rat} PR)</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">Pump: {lph}+ LPH | {hp:,} Crank HP</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', build_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-red-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>SAE Forced-Induction & EFI BSFC Verdict:</strong> {data.get('dyno_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE FUEL INJECTOR (CC/LB), TURBO AIRFLOW (LB/MIN & CFM) & FUEL PUMP CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {build_name} Injector, Turbo & Fuel Pump Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your target crank horsepower, cylinder count, fuel type (BSFC), and manifold boost pressure to calculate required fuel injector size (at 80% IDC), turbocharger lb/min & CFM airflow, and LPH fuel pump flow.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="hpSlider" class="text-zinc-300">Target Crank Horsepower (HP)</label>
              <span class="text-red-400 font-bold"><span id="hpVal">{hp:,}</span> HP (~<span id="whpVal">{int(hp * 0.85):,}</span> WHP)</span>
            </div>
            <input id="hpSlider" type="range" min="250" max="1500" step="25" value="{hp}" class="w-full accent-red-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="cylSelect" class="block text-xs font-medium text-zinc-400 mb-1">Engine Cylinder Count</label>
              <select id="cylSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500">
                <option value="4" {"selected" if cyl == 4 else ""}>4-Cylinder (K24 / EJ25 / 2.0T)</option>
                <option value="6" {"selected" if cyl == 6 else ""}>6-Cylinder (2JZ / B58 / VR6 / RB)</option>
                <option value="8" {"selected" if cyl == 8 else ""}>8-Cylinder V8 (LS / Coyote / Hemi)</option>
              </select>
            </div>
            <div>
              <label for="fuelSelect" class="block text-xs font-medium text-zinc-400 mb-1">Fuel Type & BSFC</label>
              <select id="fuelSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500">
                <option value="0.55|93 Octane Gas" {"selected" if bsfc <= 0.60 else ""}>91/93 Octane Pump Gas (0.55 BSFC)</option>
                <option value="0.72|E85 Ethanol" {"selected" if 0.60 < bsfc <= 0.80 else ""}>E85 Flex-Fuel Ethanol (0.72 BSFC)</option>
                <option value="1.05|Methanol Race" {"selected" if bsfc > 0.80 else ""}>M1 Methanol Race Fuel (1.05 BSFC)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="boostSlider" class="text-zinc-300">Target Manifold Boost Pressure (PSI)</label>
              <span class="text-red-400 font-bold"><span id="boostVal">{boost_p}</span> PSI (<span id="prVal">{pr_rat}</span>:1 PR)</span>
            </div>
            <input id="boostSlider" type="range" min="6" max="36" step="1" value="{boost_p}" class="w-full accent-red-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-red-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-red-400 font-bold">Injector Size (@80% IDC)</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="ccOut">{cc_min:,}</span> <span class="text-xs font-normal text-zinc-400">cc/min</span></div>
            <p id="lbHrNoteOut" class="text-xs text-red-400 font-semibold mt-1">{lb_hr} lb/hr (@43.5 PSI Base)</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Turbo Airflow & Pump</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1"><span id="lbMinOut">{lb_min}</span> <span class="text-xs font-normal text-zinc-400">lb/min</span></div>
            <p id="cfmLphOut" class="text-xs text-zinc-300 font-semibold mt-1">{cfm:,} CFM | {lph}+ LPH Pump</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-red-950/40 border border-red-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="trbAdviceBanner" class="text-sm text-red-100 font-medium"></div>
        <a id="dynamicTrbBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-red-500 hover:bg-red-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Injectors, Turbo & Pump on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {build_name} Injectors, Turbo & Fuel System Bundle</h2>
        <span class="text-xs text-zinc-400">EV14 High-Z Matched & E85 Ethanol Safe</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Fuel Injector Size (cc/min & lb/hr) Max Horsepower Chart at 80% Duty Cycle (Gas vs. E85)</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Injector Rating (@43.5 PSI)</th>
              <th class="py-3.5 px-4">4-Cylinder Max HP</th>
              <th class="py-3.5 px-4 text-red-400">6-Cylinder Max HP</th>
              <th class="py-3.5 px-4 text-emerald-400">8-Cylinder V8 Max HP</th>
              <th class="py-3.5 px-4">Matched Fuel Pump</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Master EFI Tuner 80% IDC, 1:1 Rising Fuel Pressure & E85 Hotwire Checklist</h2>
        <span id="trbBadge" class="text-xs font-bold bg-zinc-800 text-red-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({build_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} TurboInjectorIndex. Independent Forced-Induction Airflow & EFI Fuel System Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const hpSlider = document.getElementById('hpSlider');
    const cylSelect = document.getElementById('cylSelect');
    const fuelSelect = document.getElementById('fuelSelect');
    const boostSlider = document.getElementById('boostSlider');
    const hpVal = document.getElementById('hpVal');
    const whpVal = document.getElementById('whpVal');
    const boostVal = document.getElementById('boostVal');
    const prVal = document.getElementById('prVal');
    const ccOut = document.getElementById('ccOut');
    const lbHrNoteOut = document.getElementById('lbHrNoteOut');
    const lbMinOut = document.getElementById('lbMinOut');
    const cfmLphOut = document.getElementById('cfmLphOut');
    const trbAdviceBanner = document.getElementById('trbAdviceBanner');
    const dynamicTrbBtn = document.getElementById('dynamicTrbBtn');

    function recalculateTurbo() {{
      const hp = parseInt(hpSlider.value, 10);
      const cyls = parseInt(cylSelect.value, 10);
      const fuelParts = fuelSelect.value.split('|');
      const bsfc = parseFloat(fuelParts[0]);
      const fuelName = fuelParts[1];
      const boostPsi = parseInt(boostSlider.value, 10);

      hpVal.textContent = hp.toLocaleString();
      whpVal.textContent = Math.round(hp * 0.85).toLocaleString();
      boostVal.textContent = boostPsi;

      const pr = ((14.7 + boostPsi + 2.0) / 14.7).toFixed(2);
      prVal.textContent = pr;

      const lbMin = (hp * 0.10).toFixed(1);
      const cfm = Math.round(parseFloat(lbMin) * 14.27);

      const injLbHr = Math.round((hp * bsfc) / (cyls * 0.80));
      const injCcMin = Math.ceil((injLbHr * 10.5) / 10) * 10;

      // Standard commercial injector tier
      let stdCc = 550;
      if (injCcMin <= 550) stdCc = 550;
      else if (injCcMin <= 660) stdCc = 650;
      else if (injCcMin <= 860) stdCc = 850;
      else if (injCcMin <= 1050) stdCc = 1000;
      else if (injCcMin <= 1320) stdCc = 1300;
      else if (injCcMin <= 1550) stdCc = 1500;
      else stdCc = 2200;

      const reqLph = Math.ceil((((hp * bsfc * 0.4536) / 0.745) * 1.22) / 10) * 10;
      const railPsi = Math.round(43.5 + boostPsi);
      const pumpTier = reqLph <= 360 ? "Single Walbro 450/525 LPH" : "Dual Walbro 450/525 LPH";

      ccOut.textContent = injCcMin.toLocaleString();
      lbHrNoteOut.textContent = `${{injLbHr}} lb/hr (Buy ${{stdCc}}cc Set)`;
      lbMinOut.textContent = lbMin;
      cfmLphOut.textContent = `${{cfm.toLocaleString()}} CFM | ${{reqLph}}+ LPH Pump`;

      trbAdviceBanner.innerHTML = `🏎️ <strong>EFI Dyno Spec:</strong> Making ${{hp.toLocaleString()}} HP on ${{fuelName}} (${{boostPsi}} PSI / ${{pr}}:1 PR) requires a <strong>Set of ${{cyls}}× ${{stdCc}}cc Fuel Injectors</strong>, a <strong>${{lbMin}} lb/min (${{cfm.toLocaleString()}} CFM) Turbocharger</strong>, and a <strong>${{pumpTier}} E85 Fuel Pump (${{reqLph}}+ LPH @ ${{railPsi}} PSI rail)</strong>.`;
      dynamicTrbBtn.href = `https://${{amzDomain}}/s?k=${{stdCc}}cc+Fuel+Injectors+Set+of+${{cyls}}+Walbro+450+Fuel+Pump+Turbocharger&tag=${{amzTag}}`;
    }}

    hpSlider.addEventListener('input', recalculateTurbo);
    cylSelect.addEventListener('change', recalculateTurbo);
    fuelSelect.addEventListener('change', recalculateTurbo);
    boostSlider.addEventListener('input', recalculateTurbo);
    recalculateTurbo();

    const checks = document.querySelectorAll('.trb-check');
    const badge = document.getElementById('trbBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Turbocharger+1000cc+Fuel+Injectors+Walbro+450+Fuel+Pump"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-red-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-red-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('cc', 850):,}cc ({item.get('lb_hr', 80)} lb/hr)</span>
            <span class="text-xs text-zinc-400">{item.get('lb_min', 65.0)} lb/min | {item.get('lph', 350)} LPH</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-red-400 transition">{item['build_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-red-400">Calculate Injectors, Turbo CFM & Pump →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TurboInjectorIndex — Fuel Injector Size (cc/lb), Turbo Airflow (lb/min & CFM) & Fuel Pump Calculator (2026)</title>
  <meta name="description" content="Calculate exact forced-induction fuel injector size (cc/min and lb/hr at 80% duty cycle for 93 octane gas and E85), turbocharger compressor airflow (lb/min and CFM), and Walbro LPH fuel pump capacity for LS, Coyote, K24, 2JZ, and B58 builds.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="TurboInjectorIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-red-500 text-zinc-950 px-2 py-0.5 rounded font-black">TURBO</span>InjectorIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-red-500 hover:bg-red-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Turbos, Injectors & Pumps →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Turbo Airflow (lb/min & CFM), Fuel Injector & LPH Pump Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your engine platform, turbocharger model, or horsepower target below to calculate BSFC fuel injector flow (cc/min & lb/hr at 80% IDC), compressor pressure ratio, and E85 LPH fuel pump requirements.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search engine, turbo, or injector size (e.g. 5.3 LS Turbo, K24, 2JZ, GT3582R, S475, 1000cc Injectors, Walbro 450, E85...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-red-500">
      </div>
    </div>

    <div id="trbGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} TurboInjectorIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('trbGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>TurboInjectorIndex Turbocharger Airflow & EFI Fuel Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Turbocharger Airflow (lb/min & CFM), Fuel Injector cc/lb & LPH Pump Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_TURBO:
        candidates.append((CUSTOM_TURBO.strip(), 650, 8, 0.72, 16, "E85 Ethanol", "7875 Billet / S366"))
    candidates.extend(SEED_TURBOS)
    candidates.extend(discover_google_turbo_queries(published_slugs))

    new_urls = []
    count = 0

    for trb_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        b_name = trb_tuple[0]
        slug = slugify(f"{b_name}-injector-turbo-pump-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating turbocharger airflow & fuel injector calculator for: {b_name}...")
        try:
            data = generate_turbo_data(trb_tuple)
            build_turbo_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "build_name": data.get("build_name", b_name),
                "slug": slug,
                "title": data.get("seo_title", f"{b_name} Turbo & Injector Calculator"),
                "description": data.get("meta_description", ""),
                "cc": int(safe_float(sp.get("injector_flow_cc_min", 820), 820)),
                "lb_hr": int(safe_float(sp.get("injector_flow_lb_hr", 78), 78)),
                "lb_min": round(safe_float(sp.get("turbo_airflow_lb_min", 65.0), 65.0), 1),
                "lph": int(safe_float(sp.get("required_pump_lph_at_boost", 350), 350)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {b_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new turbocharger airflow & fuel injector calculator pages.")


if __name__ == "__main__":
    main()

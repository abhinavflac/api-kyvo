from typing import Any, Dict, Optional, Tuple
import json
from mistralai import Mistral
# from groq import Groq
from .supabase_client import get_supabase
from .settings import MISTRAL_API_KEY, ENTITY_EXTRACT_SYSTEM_PROMPT
from groq import Groq
import math

#client = Groq(api_key=MISTRAL_API_KEY)

#response = client.chat.completions.create(   model="llama-3.1-8b-instant",
#    messages=[
#        {"role": "user", "content": "Hello"}
#    ]
#)

APPLICATION_RPM_TABLE: Dict[str, Tuple[int, int]] = {

    # Very slow / heavy duty
    "slewing_ring": (10, 100),
    "turntable_heavy": (10, 100),
    "wind_turbine_yaw": (5, 50),
    "excavator_swing": (5, 80),

    # Heavy industrial
    "conveyor": (100, 500),
    "bucket_elevator": (50, 300),
    "roller_table": (100, 500),
    "mining_crusher": (100, 400),
    "cement_mill": (100, 300),
    "paper_dryer": (200, 500),
    "large_pump": (200, 500),

    # General industrial
    "gearbox": (500, 2000),
    "centrifugal_pump": (500, 2000),
    "industrial_fan": (500, 2000),
    "motor": (500, 2000),
    "compressor": (500, 2000),

    # Automotive / medium speed
    "wheel_hub": (2000, 5000),
    "propeller_shaft": (2000, 5000),
    "reducer": (2000, 5000),
    "machine_tool_spindle": (2000, 5000),

    # High speed
    "household": (5000, 10000),
    "washing_machine": (5000, 10000),
    "blower": (5000, 10000),
    "automotive_transmission": (5000, 10000),

    # Very high speed
    "medical_equipment": (10000, 20000),
    "turbocharger": (10000, 20000),
    "dental_drill": (10000, 30000),
}


# -------------------------------------------------
# APPLICATION → DEFAULT DESIGN LIFE (hours)
# -------------------------------------------------

APPLICATION_LIFE_TABLE: Dict[str, Tuple[int, int]] = {

    # Household / agriculture / medical instruments
    "household": (300, 3000),
    "agriculture": (300, 3000),
    "medical_equipment": (300, 3000),
    "instruments": (300, 3000),

    # Short period / intermittent
    "hand_tools": (3000, 8000),
    "lifting_tackle": (3000, 8000),
    "construction_equipment": (3000, 8000),

    # Intermittent but high reliability
    "lift": (8000, 12000),
    "crane_packaged": (8000, 12000),

    # 8 hours/day – not fully utilized
    "gearbox": (10000, 25000),
    "motor": (10000, 25000),
    "rotary_crusher": (10000, 25000),

    # 8 hours/day – fully utilized
    "machine_tool": (20000, 30000),
    "woodworking_machine": (20000, 30000),
    "engineering_machine": (20000, 30000),
    "bulk_crane": (20000, 30000),
    "ventilator_fan": (20000, 30000),
    "conveyor": (20000, 30000),
    "printing_machine": (20000, 30000),
    "separator": (20000, 30000),
    "centrifuge": (20000, 30000),

    # Continuous 24 hour use
    "rolling_mill": (40000, 50000),
    "compressor": (40000, 50000),
    "pump": (40000, 50000),
    "textile_machine": (40000, 50000),
    "mine_hoist": (40000, 50000),

    # Wind energy
    "wind_turbine": (30000, 100000),

    # Water / marine / furnace
    "water_works": (60000, 100000),
    "rotary_furnace": (60000, 100000),
    "ship_propulsion": (60000, 100000),

    # Heavy power plant / mining
    "large_generator": (100000, 150000),
    "power_plant": (100000, 150000),
    "mine_pump": (100000, 150000),
    # Heavy positioning / construction
    "slewing_ring": (20000, 50000),
    "excavator_swing": (15000, 40000),
    "wind_turbine_yaw": (30000, 100000),

}


# -------------------------------------------------
# APPLICATION → EXPECTED RADIAL LOAD RANGE (kN)
# MATCHES DB SCALE (like 8.4 kN, 4.45 kN etc.)
# -------------------------------------------------

APPLICATION_LOAD_TABLE: Dict[str, Tuple[float, float]] = {

    # 0 – 100 RPM (Very slow, heavy duty)
    "slewing_ring": (70, 300),
    "turntable_heavy": (15, 80),
    "wind_turbine_yaw": (15, 70),
    "excavator_swing": (150, 500),
    "gun_mount": (30, 120),
    "heavy_rotary_table": (40, 150),

    # 100 – 500 RPM (Heavy industrial)
    "conveyor": (5.5, 23),
    "mining_crusher": (55, 180),
    "cement_mill": (120, 380),
    "rolling_mill_stand": (250, 650),
    "paper_dryer": (50, 130),
    "large_pump": (15, 60),

    # 500 – 2,000 RPM (General industrial)
    "gearbox": (7, 45),
    "industrial_pump": (8, 35),
    "industrial_fan": (13, 55),
    "low_speed_motor": (10, 33),
    "rubber_mixer": (35, 100),
    "passenger_axle": (60, 200),
    "compressor": (15, 50),

    # 2,000 – 5,000 RPM
    "wheel_hub": (7, 23),
    "propeller_shaft": (8, 30),
    "two_stroke_engine": (3, 13),
    "rocker_arm": (1.5, 7),
    "reducer": (8, 45),
    "machine_tool_spindle": (7, 30),

    # 5,000 – 10,000 RPM
    "household": (0.2, 1.5),
    "small_motor": (1.5, 8),
    "blower": (3, 12),
    "light_rolling_mill": (15, 45),
    "automotive_transmission": (8, 25),

    # 10,000 – 20,000 RPM
    "high_speed_spindle": (3, 15),
    "turbocharger": (5, 20),
    "high_speed_pump": (8, 30),
    "dental_drill": (0.3, 2),
    "small_turbine": (2, 9),

    # 20,000 – 30,000 RPM
    "high_speed_compressor": (3, 13),
    "high_performance_motor": (4, 18),
    "precision_grinder": (1.5, 8),
    "textile_spindle": (0.7, 3),

    # 30,000 – 100,000 RPM
    "gas_turbine": (6, 40),
    "aerospace_component": (2.5, 25),
    "high_speed_precision_spindle": (0.7, 5),
    "gyroscope": (0.3, 3),

    # > 100,000 RPM
    "ultra_high_speed_motor": (0.3, 3),
    "micro_turbine": (5.5, 35),
    "laboratory_centrifuge": (0.1, 1.5),
}

class KyvoEngine:
    def __init__(self):
        self.mistral_client = Groq(api_key=MISTRAL_API_KEY)

    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------
    def safe_json_load(self, s: str) -> Dict[str, Any]:
        s = s.strip()
        try:
            return json.loads(s)
        except Exception:
            if "{" in s and "}" in s:
                s = s[s.index("{"): s.rindex("}") + 1]
                return json.loads(s)
            raise

    # --------------------------------------------------
    # Entity extraction
    # --------------------------------------------------
    def extract_entities(self, user_query: str) -> Dict[str, Any]:
        resp = self.mistral_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": ENTITY_EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            temperature=0.0,
        )

        content = resp.choices[0].message.content
        data = self.safe_json_load(content)

        template = {
            "bore_d_mm": None,
            "outer_D_mm": None,
            "width_B_mm": None,
            "life_hours": None,
            "rpm": None,
            "radial_load_kN": None,
            "axial_load_kN": None,
            "bearing_type": None,
            "brand": None,
            "designation": None,
            "application_hint": None,
        }

        for k in template:
            if k not in data:
                data[k] = None

        return data

    # --------------------------------------------------
    # Intent
    # --------------------------------------------------
    def decide_intent(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        life = entities.get("life_hours")
        radial = entities.get("radial_load_kN")
        rpm = entities.get("rpm")
        application_hint = entities.get("application_hint")

        # Engineering intent triggers
        if life is not None or radial is not None or rpm is not None:
            return {
                "intent": "ENGINEERING_SELECTION",
                "missing_fields": [],
                "reason": "Life, load, or speed specified → engineering calculation required."
            }

        if application_hint is not None:
            return {
                "intent": "ENGINEERING_SELECTION",
                "missing_fields": [],
                "reason": "Application-based request → derive engineering parameters."
            }

        return {
            "intent": "DIRECT_SEARCH",
            "missing_fields": [],
            "reason": "No engineering or application requirement → direct catalogue search."
        }

    # --------------------------------------------------
    # Defaults from application
    # --------------------------------------------------
    def normalize_application_hint(self, s: str) -> str:
        return (
            s.lower()
            .strip()
            .replace("-", " ")
            .replace("_", " ")
        )

    def derive_defaults_from_application(self, application_hint: str):

        ah = self.normalize_application_hint(application_hint)

        # ---------------- APPLICATION ALIAS MAP (same logic as expert) ----------------
        alias_map = {
            # Slewing / crane
            "crane": "slewing",
            "slewing bearing": "slewing",
            "slew bearing": "slewing",
            "turntable": "turntable",
            "yaw drive": "yaw",

            # Excavator
            "excavator": "excavator",
            "swing bearing": "excavator",
            "excavator swing": "excavator",

            # Wind turbine
            "yaw bearing": "yaw",
            "wind yaw": "yaw",
        }

        for key, mapped in alias_map.items():
            if key in ah:
                ah = mapped
                break

        # ---------------- DEFAULT MAPPING TABLE ----------------
        # list of (keywords, defaults)
        mapping = [

            # -------- VERY HEAVY POSITIONING / CONSTRUCTION --------
            (["slewing", "turntable", "yaw", "excavator", "rotary table"],
             {
                 "life_hours": 25000,
                 "rpm": 40,
                 "radial_load_kN": 80.0,
                 "axial_load_kN": 30.0,
                 "duty_class": "heavy_positioning"
             }),

            # -------- HEAVY INDUSTRIAL --------
            (["conveyor", "crusher", "cement mill", "rolling mill", "paper dryer", "large pump"],
             {
                 "life_hours": 20000,
                 "rpm": 300,
                 "radial_load_kN": 15.0,
                 "axial_load_kN": 3.0,
                 "duty_class": "heavy_industrial"
             }),

            # -------- GENERAL INDUSTRIAL --------
            (["gearbox", "gearboxes", "industrial pump", "fan", "low speed motor", "compressor", "rubber mixer"],
             {
                 "life_hours": 15000,
                 "rpm": 1500,
                 "radial_load_kN": 10.0,
                 "axial_load_kN": 2.0,
                 "duty_class": "general_industrial"
             }),

            # -------- AUTOMOTIVE / MEDIUM SPEED --------
            (["automotive wheel", "wheel hub", "propeller shaft", "engine", "rocker arm", "reducer", "spindle"],
             {
                 "life_hours": 8000,
                 "rpm": 3000,
                 "radial_load_kN": 6.0,
                 "axial_load_kN": 1.5,
                 "duty_class": "automotive"
             }),

            # -------- SMALL MACHINES --------
            (["household", "household appliance", "small motor", "blower", "light rolling mill", "washing machine"],
             {
                 "life_hours": 3000,
                 "rpm": 7000,
                 "radial_load_kN": 2.0,
                 "axial_load_kN": 0.5,
                 "duty_class": "light_machinery"
             }),

            # -------- HIGH SPEED --------
            (["machine tool spindle", "turbocharger", "high speed pump", "dental drill", "small turbine"],
             {
                 "life_hours": 2000,
                 "rpm": 15000,
                 "radial_load_kN": 1.5,
                 "axial_load_kN": 0.5,
                 "duty_class": "high_speed"
             }),

            # -------- VERY HIGH SPEED / PRECISION --------
            (["gas turbine", "aerospace", "gyroscope", "ultra high speed", "laboratory"],
             {
                 "life_hours": 1000,
                 "rpm": 60000,
                 "radial_load_kN": 0.5,
                 "axial_load_kN": 0.2,
                 "duty_class": "ultra_high_speed"
             }),
        ]

        # ---------------- MATCH LOGIC ----------------
        for keywords, defaults in mapping:
            if any(keyword in ah for keyword in keywords):
                result = defaults.copy()
                result["is_generic_fallback"] = False
                result["source"] = "application_default_table"

                return result

        # ---------------- FINAL SAFE FALLBACK ----------------
        # If nothing matched, NEVER return ultra-light unsafe defaults
        return {
            "life_hours": 12000,
            "rpm": 1000,
            "radial_load_kN": 8.0,
            "axial_load_kN": 1.0,
            "duty_class": "unknown_industrial",
            "is_generic_fallback": True,
            "source": "generic_safe_defaults",
            "fallback_message": "Using conservative industrial defaults for unknown application."
        }

    # --------------------------------------------------
    # Life + application inference
    # --------------------------------------------------
    def classify_life_hours(self, life_hours: float):
        if life_hours < 300:
            return {"life_class": "very_low", "life_comment": "Very short specification life"}
        elif 300 <= life_hours <= 3000:
            return {"life_class": "light_duty", "life_comment": "Typical for household, agricultural, or medical equipment"}
        elif 3000 < life_hours <= 8000:
            return {"life_class": "intermittent_industrial", "life_comment": "Typical for intermittent industrial or construction machinery"}
        elif 8000 < life_hours <= 12000:
            return {"life_class": "high_reliability", "life_comment": "High reliability application such as lifts or cranes"}
        else:
            return {"life_class": "very_high_reliability", "life_comment": "Very high life expectation; conservative bearing selection required"}

    def infer_application_from_rpm_and_life(self, rpm: float, life_hours: float):
        if rpm < 100:
            return {"application_class": "slewing_positioning", "examples": ["slewing drives", "positioning systems"]}
        elif 100 <= rpm <= 500:
            return {"application_class": "low_speed_industrial", "examples": ["conveyors", "crushers"]}
        elif 500 < rpm <= 2000:
            if life_hours > 8000:
                return {"application_class": "high_reliability_industrial", "examples": ["gearboxes", "pumps", "continuous-duty machinery"]}
            return {"application_class": "general_industrial", "examples": ["gearboxes", "pumps"]}
        elif 2000 < rpm <= 5000:
            return {"application_class": "automotive", "examples": ["automotive systems"]}
        elif 5000 < rpm <= 10000:
            return {"application_class": "small_motors", "examples": ["electric motors", "household machines"]}
        else:
            return {"application_class": "high_speed", "examples": ["spindles", "turbomachinery"]}

    # --------------------------------------------------
    # Engineering
    # --------------------------------------------------
    def compute_engineering_requirements(
            self,
            entities: Dict[str, Any],
            category_hint: Optional[str] = None
    ) -> Dict[str, Any]:

        life_hours = entities.get("life_hours")
        rpm = entities.get("rpm")
        Fr = entities.get("radial_load_kN")
        Fa = entities.get("axial_load_kN") or 0.0

        # ---------------- HARD GUARDS ----------------
        if rpm is None or rpm <= 0:
            return {
                "error": "RPM missing or invalid",
                "P_kN": None,
                "C_required_kN": None
            }

        if life_hours is None or life_hours <= 0:
            # Industrial fallback life (never zero)
            life_hours = 12000.0
            entities["life_hours"] = life_hours

        if Fr is None or Fr <= 0:
            # Life + RPM aware fallback load
            Fr = self.generic_safe_load(rpm, life_hours)
            entities["radial_load_kN"] = Fr

        # ---------------- ISO 281 LIFE CALC ----------------
        L10 = (life_hours * 60.0 * rpm) / 1_000_000.0
        P = Fr + Fa

        # Life exponent
        p = 10.0 / 3.0
        if category_hint and "ball" in category_hint.lower():
            p = 3.0

        # Required dynamic capacity
        C_required = P * (L10 ** (1.0 / p))

        # Hard clamp (catalog sanity)
        if C_required > 1e6:
            C_required = 1e6

        return {
            "L10_million_revs": round(L10, 3),
            "P_kN": round(P, 3),
            "C_required_kN": round(C_required, 2),
            "p": p,
            "life_evaluation": self.classify_life_hours(life_hours),
            "application_evaluation": self.infer_application_from_rpm_and_life(rpm, life_hours),
        }

    # --------------------------------------------------
    # Static Safety
    # --------------------------------------------------
    def evaluate_static_safety(self, Co: float, P: float) -> Dict[str, Any]:
        """
        Industrial-grade static safety evaluation
        s0 = C0 / P
        """

        # ---------------- HARD VALIDATION ----------------
        if P is None or P <= 0:
            return {
                "static_safety_factor": None,
                "static_safety_verdict": "INVALID",
                "static_safety_class": "INVALID",
                "engineering_comment": "Equivalent load must be positive",
            }

        if Co is None or Co <= 0:
            return {
                "static_safety_factor": None,
                "static_safety_verdict": "INVALID",
                "static_safety_class": "INVALID",
                "engineering_comment": "Static load rating not available or invalid",
            }

        # ---------------- UNIT GUARD (N vs kN) ----------------
        # If Co is very large (e.g. > 2000), it's likely in Newtons. Convert to kN.
        # Most industrial bearings have static ratings from 1kN to 1000kN.
        if Co > 2000:
            Co = Co / 1000.0

        # ---------------- SAFETY FACTOR ----------------
        So = round(Co / P, 2)

        # Hard cap (avoid absurd numbers breaking ranking)
        if So > 20:
            So = 20.0

        # ---------------- INDUSTRIAL CLASSIFICATION (REAL LIMITS) ----------------

        if So < 1.0:
            verdict = "Failure risk"
            s_class = "FAIL"
            comment = "Unsafe: very high risk of permanent deformation"

        elif So < 1.5:
            verdict = "Very risky"
            s_class = "VERY_RISKY"
            comment = "Not acceptable for industrial service or shock loads"

        elif So < 2.0:
            verdict = "Risky"
            s_class = "RISKY"
            comment = "Only suitable for light, non-shock applications"

        elif So < 3.0:
            verdict = "Acceptable"
            s_class = "PASS"
            comment = "Adequate static safety for general industrial duty"

        elif So < 4.5:
            verdict = "Safe"
            s_class = "STRONG_PASS"
            comment = "Good static safety for heavy industrial and moderate shock loads"

        else:
            verdict = "Overdesigned"
            s_class = "OVER_SAFE"
            comment = "Very high static safety (bearing significantly oversized)"

        return {
            "static_safety_factor": So,
            "static_safety_verdict": verdict,
            "static_safety_class": s_class,
            "engineering_comment": comment
        }

    # --------------------------------------------------
    # DB search
    # --------------------------------------------------
    def run_direct_search(self, entities: Dict[str, Any]):
        query = supabase.table("bearing_master").select("*")

        if entities.get("bore_d_mm") is not None:
            query = query.eq("Bore_diameter", entities["bore_d_mm"])
        if entities.get("outer_D_mm") is not None:
            query = query.eq("D", entities["outer_D_mm"])
        if entities.get("width_B_mm") is not None:
            query = query.eq("B", entities["width_B_mm"])
        if entities.get("bearing_type"):
            query = query.ilike("Category", f"%{entities['bearing_type']}%")
        if entities.get("brand"):
            query = query.ilike("Brand", f"%{entities['brand']}%")
        if entities.get("designation"):
            code = entities["designation"].replace(" ", "")
            query = query.ilike("Designation", f"%{code}%")
        if entities.get("rpm"):
            query = query.gte("Limiting_speed_oil", entities["rpm"])

        return query.execute().data

    def run_engineering_selection(self, entities: Dict[str, Any], calc: Dict[str, Any]):

        C_required = calc.get("C_required_kN")
        rpm = entities.get("rpm")

        if C_required is None or C_required <= 0 or rpm is None or rpm <= 0:
            return []

        # -------- UNIT NORMALIZATION --------
        try:
            sample = get_supabase().table("bearing_master") \
                .select("Basic_dynamic_load_rating") \
                .limit(1) \
                .execute().data

            if sample:
                db_val = float(sample[0]["Basic_dynamic_load_rating"])
                if db_val > 5000:
                    C_required = C_required * 1000
        except Exception:
            pass

        # -------- ADMISSION WINDOW --------
        min_C = max(C_required * 0.20, 1.0)
        max_C = C_required * 4.0

        min_speed = rpm * 0.7

        data = get_supabase().table("bearing_master") \
            .select("*") \
            .gte("Basic_dynamic_load_rating", min_C) \
            .lte("Basic_dynamic_load_rating", max_C) \
            .or_(f"Limiting_speed_oil.gte.{min_speed},Limiting_speed_oil.is.null") \
            .execute().data or []

        # -------- STATIC SAFETY POST FILTER --------
        filtered = []
        P = calc.get("P_kN")

        for row in data:

            raw_co = row.get("Basic_static_load_rating")
            if raw_co is None:
                filtered.append(row)
                continue

            try:
                Co = float(raw_co)
            except Exception:
                filtered.append(row)
                continue

            if Co > 1000:
                Co = Co / 1000.0

            # only reject absurd failures
            if P and Co / P < 0.3:
                continue

            filtered.append(row)

        # -------- FAILSAFE --------
        if not filtered:
            fallback = get_supabase().table("bearing_master") \
                .select("*") \
                .or_(f"Limiting_speed_oil.gte.{min_speed},Limiting_speed_oil.is.null") \
                .execute().data or []
            return fallback[:50]

        return filtered

    # --------------------------------------------------
    # Public entry
    # --------------------------------------------------
    def run(self, query: str) -> Dict[str, Any]:

        # --------------------------------------------------
        # LUBRICATION QUERY DETECTION (Stage-3 RAG)
        # --------------------------------------------------
        q = query.lower()

        lubrication_keywords = [
            "iso vg", "viscosity", "lubrication", "lubricant",
            "oil", "grease", "kappa", "film", "adequate lubrication"
        ]

        if any(k in q for k in lubrication_keywords):

            import re

            iso_vg = None
            temperature_c = None
            rpm = None
            designation = None

            # ISO VG
            m = re.search(r"iso\s*vg\s*(\d+)", q)
            if m:
                iso_vg = int(m.group(1))

            # Temperature (°C)
            m = re.search(r"(\d+)\s*°?\s*c", q)
            if m:
                temperature_c = float(m.group(1))

            # RPM
            m = re.search(r"(\d+)\s*rpm", q)
            if m:
                rpm = float(m.group(1))

            # Comprehensive Bearing Identification
            # 1. Numeric: 1xxx-8xxx (e.g., 6208, 22210, 51105)
            # 2. Alphanumeric: NU, NJ, NUP, HK etc. (e.g., NU205, NJ 308)
            # We use word boundaries \b to avoid picking up 80 from "80C"
            patterns = [
                r"\b([1-8]\d{1,4})\b",               # Classic numeric
                r"\b([a-z]{1,3}\s?\d{2,5})\b",       # Alphanumeric like NU 205 or NU205
            ]
            
            for pat in patterns:
                m = re.search(pat, q)
                if m:
                    designation = m.group(1).replace(" ", "")
                    break

            # Load extraction
            radial_load_kN = None
            axial_load_kN = None

            # Radial Load (e.g., 5kN, 5 kN, 5.5kN)
            m = re.search(r"(\d+\.?\d*)\s*kn", q)
            if m:
                radial_load_kN = float(m.group(1))

            # Axial Load (specifically looking for axial/thrust)
            m = re.search(r"axial\s*(\d+\.?\d*)\s*kn", q)
            if m:
                axial_load_kN = float(m.group(1))

            return self.evaluate_lubrication(
                iso_vg=iso_vg,
                temperature_c=temperature_c,
                rpm=rpm,
                designation=designation,
                radial_load_kN=radial_load_kN,
                axial_load_kN=axial_load_kN
            )

        # -------------------------------
        # 1. Entity extraction
        # -------------------------------
        entities = self.extract_entities(query)
        intent = self.decide_intent(entities)

        # -------------------------------
        # 1B. BASIC SANITY CLEANUP
        # -------------------------------
        for k in ["life_hours", "rpm", "radial_load_kN", "axial_load_kN"]:
            if entities.get(k) is not None:
                try:
                    val = float(entities[k])
                    if val <= 0:
                        entities[k] = None
                    else:
                        entities[k] = val
                except Exception:
                    entities[k] = None

        # -------------------------------
        # 2. Direct search
        # -------------------------------
        if intent["intent"] == "DIRECT_SEARCH":
            return {
                "engine_version": "Kyvo-Mechanical-v1.1",
                "intent_type": "size-based",
                "extracted_parameters": entities,
                "results": self.run_direct_search(entities),
            }

        inference_info = None

        # -------------------------------
        # 3. Application based inference (PRIMARY)
        # -------------------------------
        if entities.get("application_hint") and (entities.get("life_hours") is None or entities.get("rpm") is None):

            expert_defaults = self.infer_from_expert_tables(entities["application_hint"])

            if expert_defaults:
                for k, v in expert_defaults.items():
                    if k in entities and entities.get(k) is None:
                        entities[k] = v

                entities["matched_application"] = expert_defaults.get("matched_application")

                inference_info = {
                    "source": expert_defaults.get("source"),
                    "matched_application": expert_defaults.get("matched_application"),
                    "duty_class": expert_defaults.get("duty_class"),
                    "rpm_range": expert_defaults.get("rpm_range"),
                    "life_range": expert_defaults.get("life_range"),
                    "load_range": expert_defaults.get("load_range"),
                }

        # 4. SMART FALLBACK (rpm + life only)
        if (
                entities.get("life_hours") is not None
                and entities.get("rpm") is not None
                and entities.get("radial_load_kN") is None
        ):

            app_guess = self.infer_application_from_rpm_and_life(
                entities["rpm"],
                entities["life_hours"]
            )

            app_class = app_guess["application_class"]
            guessed_app = None

            if app_class in ["general_industrial", "high_reliability_industrial"]:
                guessed_app = "gearbox"
            elif app_class == "low_speed_industrial":
                guessed_app = "conveyor"
            elif app_class == "small_motors":
                guessed_app = "motor"
            elif app_class == "automotive":
                guessed_app = "wheel_hub"
            elif app_class == "high_speed":
                guessed_app = "machine_tool_spindle"

            if guessed_app:
                expert_defaults = self.infer_from_expert_tables(guessed_app)

                if expert_defaults:
                    entities["radial_load_kN"] = expert_defaults["radial_load_kN"]
                    entities["axial_load_kN"] = expert_defaults["axial_load_kN"]
                    entities["matched_application"] = expert_defaults["matched_application"]

                    inference_info = {
                        "source": "rpm_life_fallback_inference",
                        "matched_application": guessed_app,
                        "duty_class": expert_defaults.get("duty_class"),
                    }

        # -------------------------------
        # 5. FINAL HARD SAFETY — NEVER ALLOW MISSING LOAD
        # -------------------------------
        if entities.get("radial_load_kN") is None:

            rpm_for_safe = entities.get("rpm") or 1000.0
            life_for_safe = entities.get("life_hours") or 12000.0

            safe_load = self.generic_safe_load(
                rpm_for_safe,
                life_for_safe
            )

            entities["radial_load_kN"] = safe_load

            if entities.get("axial_load_kN") is None:
                entities["axial_load_kN"] = round(safe_load * 0.1, 2)

            if entities.get("rpm") is None:
                entities["rpm"] = rpm_for_safe

            if entities.get("life_hours") is None:
                entities["life_hours"] = life_for_safe

            if not inference_info:
                inference_info = {
                    "source": "generic_safe_load_fallback",
                    "matched_application": "general_industrial",
                    "duty_class": "unknown"
                }

        # 6. HARD VALIDATION (AFTER SAFETY FILL)
        # Life is allowed to fallback inside engineering
        if entities.get("rpm") is None:
            return {
                "engine_version": "Kyvo-Mechanical-v1.1",
                "ready_for_inference": False,
                "missing_required_inputs": ["rpm"],
                "results": [],
            }

        # 7. ENGINEERING CALCULATIONS
        calc = self.compute_engineering_requirements(entities)

        if "error" in calc:
            return {
                "engine_version": "Kyvo-Mechanical-v1.1",
                "ready_for_inference": False,
                "error": calc["error"],
                "results": [],
            }

        # 7B. CONTAMINATION PRE-PROCESSOR
        # Infer environment from query if not explicitly provided
        env_desc = entities.get("environment_description") or query
        inferred_env = self.infer_cleanliness(env_desc)
        
        # Inject into calc for downstream modules
        calc["environment"] = inferred_env
        calc["filtration_grade"] = entities.get("filtration_grade")
        calc["oil_cleanliness_code"] = entities.get("oil_cleanliness_code")

        if calc["C_required_kN"] > 1e6:
            calc["C_required_kN"] = 1e6

        # 8. Catalogue search
        results = self.run_engineering_selection(entities, calc)
        relaxed_used = False

        # 8B. RELAX SEARCH IF EMPTY
        if not results:

            relaxed_C = max(calc["C_required_kN"] * 0.4, 10.0)
            relaxed_used = True

            query = get_supabase().table("bearing_master") \
                .select("*") \
                .gte("Basic_dynamic_load_rating", relaxed_C) \
                .gte("Limiting_speed_oil", entities["rpm"])

            if entities.get("bore_d_mm") is not None:
                query = query.eq("Bore_diameter", entities["bore_d_mm"])
            if entities.get("outer_D_mm") is not None:
                query = query.eq("D", entities["outer_D_mm"])

            results = query.execute().data or []
            if entities.get("width_B_mm") is not None:
                query = query.eq("B", entities["width_B_mm"])

            results = query.execute().data
        # 9. STATIC SAFETY EVALUATION (NO HARD REJECTION)
        final_results = []
        P_effective = calc["P_kN"]

        for row in results:

            raw_co = row.get("Basic_static_load_rating")

            if raw_co is None:
                row["static_safety_factor"] = None
                row["static_safety_verdict"] = "UNKNOWN"
                row["static_safety_class"] = "UNKNOWN"
                row["static_safety_comment"] = "Static load rating not available"
                row["unsafe_static"] = True  # penalize later
                final_results.append(row)
                continue

            try:
                raw_co = float(raw_co)
            except Exception:
                # Corrupt row → still keep but mark unsafe
                row["static_safety_factor"] = None
                row["static_safety_verdict"] = "UNKNOWN"
                row["static_safety_class"] = "UNKNOWN"
                row["static_safety_comment"] = "Invalid static rating"
                row["unsafe_static"] = True
                final_results.append(row)
                continue

            # Pass the raw rating; evaluate_static_safety handles N vs kN normalization.
            static = self.evaluate_static_safety(raw_co, P_effective)

            row["static_safety_factor"] = static.get("static_safety_factor")
            row["static_safety_verdict"] = static.get("static_safety_verdict")
            row["static_safety_class"] = static.get("static_safety_class")
            row["static_safety_comment"] = static.get("engineering_comment")

            # NEVER hard-reject — only flag
            row["unsafe_static"] = static.get("static_safety_verdict") in [
                "Failure risk", "Very risky"
            ]

            final_results.append(row)

        results = final_results

        # 9B. THERMAL + FRICTION MODULE
        stage_thermal = None

        if results and calc.get("P_kN") is not None:

            bearing_row = results[0]  # best candidate

            stage_thermal = self.evaluate_thermal_friction(
                entities=entities,
                calc=calc,
                bearing_row=bearing_row
            )

        else:
            stage_thermal = {
                "stage": "Thermal",
                "decision": "No valid bearing candidates for thermal evaluation"
            }

        # 9C. CONTAMINATION ANALYSIS (STANDALONE)
        stage_contamination = None
        if results:
            eta_c = self.compute_contamination_factor(
                environment=calc.get("environment"),
                sealing_type=entities.get("sealing_type"),
                filtration_grade=calc.get("filtration_grade"),
                oil_cleanliness_code=calc.get("oil_cleanliness_code")
            )
            stage_contamination = {
                "stage": "Contamination",
                "inferred_cleanliness": calc.get("environment"),
                "contamination_factor": eta_c,
                "impact": "Friction increased, life reduced" if eta_c and eta_c < 0.7 else "Negligible impact"
            }

        # 10. STAGE-4: PRELOAD
        stage4_preload = None

        if results and calc.get("P_kN") is not None:

            bearing_row = results[0]  # best candidate
            s0 = bearing_row.get("static_safety_factor")

            # Static capacity already stored in the row, used by previous modules.
            # No redundant normalization here; handled centrally in safety/life modules.

            if s0 is not None and s0 >= 1.0:

                stage4_preload = self.evaluate_preload_stage4(
                    entities=entities,
                    calc=calc,
                    bearing_row=bearing_row,
                    C_oper_um=bearing_row.get("C_oper_um"),
                    high_stiffness=entities.get("high_stiffness_required", False)
                )

            else:
                stage4_preload = {
                    "stage": "Stage-4",
                    "preload_required": False,
                    "comment": "Static safety too low for preload evaluation"
                }

        else:
            stage4_preload = {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "No valid bearing candidates for preload evaluation"
            }

        # 10B. FINAL RANKING & PENALTY (TOP RESULT ONLY)
        ranking_details = None
        if results:
            # Assume a base score of 100 for the top candidate
            ranking_details = self.apply_ranking_penalty(
                base_score=100.0,
                preload_stage4=stage4_preload,
                thermal_stage=stage_thermal,
                contamination_stage=stage_contamination,
                calc=calc
            )
            # Update the top result's score
            results[0]["kyvo_score"] = ranking_details.get("final_score")
            results[0]["ranking_penalty_reasons"] = ranking_details.get("ranking_penalty_reasons")

        # 11. Explainability
        explain = {
            "source": inference_info.get("source") if inference_info else "user_specified",
            "matched_application": entities.get("matched_application"),
            "duty_class": inference_info.get("duty_class") if inference_info else None,
            "rpm_used": entities["rpm"],
            "life_used_hours": entities["life_hours"],
            "radial_load_used_kN": entities["radial_load_kN"],
            "axial_load_used_kN": entities.get("axial_load_kN", 0.0),
            "equivalent_load_P_kN": round(calc["P_kN"], 3),
            "required_dynamic_capacity_kN": round(calc["C_required_kN"], 2),
            "relaxed_search_used": relaxed_used,
            "fallback_used": True if inference_info else False,
        }
        # 12. FINAL OUTPUT
        return {
            "engine_version": "Kyvo-Mechanical-v1.1",
            "intent_type": "application-based" if entities.get("application_hint") else "life-based",
            "extracted_parameters": entities,
            "ready_for_inference": True,
            "note": "Closest feasible bearings shown." if not results else None,
            "inference": explain,
            "engineering": calc,
            "stage_contamination": stage_contamination,
            "stage_thermal": stage_thermal,
            "stage4_preload": stage4_preload,
            "ranking_details": ranking_details,
            "results": results if results else [],
        }

    # Added generic safety load
    def generic_safe_load(self, rpm: float, life: float) -> float:
        """
        Conservative generic radial load estimator when nothing is known.
        Prevents zero-load / crash / unrealistic capacity.
        Life-aware + RPM-aware.
        """

        # ---------------- HARD SAFETY GUARDS ----------------
        if rpm is None or rpm <= 0:
            rpm = 1000.0

        if life is None or life <= 0:
            life = 12000.0

        # ---------------- RPM BASED LOAD ----------------
        if rpm <= 500:
            base_load = 20.0
        elif rpm <= 2000:
            base_load = 12.0
        elif rpm <= 5000:
            base_load = 7.0
        elif rpm <= 10000:
            base_load = 3.5
        else:
            base_load = 1.5

        # ---------------- LIFE MODIFIER ----------------
        if life > 30000:
            base_load *= 0.6  # high reliability → derate
        elif life > 15000:
            base_load *= 0.75
        elif life < 3000:
            base_load *= 1.2  # short life → allow higher load

        # Clamp to industrial realism
        base_load = max(1.0, min(base_load, 50.0))

        return round(base_load, 2)

    # Application Inference Engine (Table above the class)
    def infer_from_expert_tables(self, application_hint: str):

        ah = self.normalize_application_hint(application_hint)

        # ---------------- APPLICATION ALIAS MAP ----------------
        alias_map = {
            # Slewing / crane
            "crane": "slewing_ring",
            "slewing bearing": "slewing_ring",
            "slew bearing": "slewing_ring",
            "turntable": "turntable_heavy",

            # Excavator
            "excavator": "excavator_swing",
            "swing bearing": "excavator_swing",
            "excavator swing": "excavator_swing",

            # Wind turbine
            "yaw bearing": "wind_turbine_yaw",
            "yaw drive": "wind_turbine_yaw",
            "wind yaw": "wind_turbine_yaw",
        }

        # Normalize via alias first
        for key, mapped_app in alias_map.items():
            if key in ah:
                ah = mapped_app
                break

        # Prefer longer / more specific keys first
        sorted_apps = sorted(APPLICATION_RPM_TABLE.keys(), key=lambda x: -len(x))

        for app in sorted_apps:
            if app.replace("_", " ") in ah or app in ah:

                rpm_range = APPLICATION_RPM_TABLE.get(app)
                life_range = APPLICATION_LIFE_TABLE.get(app)
                load_range = APPLICATION_LOAD_TABLE.get(app)

                # ---------------- CLASSIFY DUTY LEVEL ----------------
                heavy_duty = False

                # Very low speed machines are heavy
                if rpm_range and rpm_range[1] <= 300:
                    heavy_duty = True

                # Very high load class are heavy
                if load_range and load_range[1] >= 100:
                    heavy_duty = True

                # Explicit heavy positioning systems
                if app in ["slewing_ring", "excavator_swing", "wind_turbine_yaw"]:
                    heavy_duty = True

                # ---------------- RPM INFERENCE ----------------
                if rpm_range is None:
                    rpm = 1000  # generic industrial default
                else:
                    if heavy_duty:
                        # heavier → more conservative RPM
                        rpm = int((rpm_range[0] * 0.7) + (rpm_range[1] * 0.3))
                    else:
                        rpm = int((rpm_range[0] * 0.6) + (rpm_range[1] * 0.4))

                # Hard safety cap
                rpm = max(10, min(rpm, 150000))

                # ---------------- LIFE INFERENCE ----------------
                if life_range is None:
                    life = 15000  # safe industrial default
                else:
                    if heavy_duty:
                        # heavy machines → higher reliability
                        life = int((life_range[0] * 0.3) + (life_range[1] * 0.7))
                    else:
                        life = int((life_range[0] * 0.4) + (life_range[1] * 0.6))

                # Hard floor & ceiling
                life = max(500, min(life, 150000))

                # ---------------- LOAD INFERENCE ----------------
                if load_range is None:
                    design_load = 10.0  # safe medium industrial load
                else:
                    # mid design load (never max)
                    design_load = (load_range[0] + load_range[1]) / 2

                # Apply safety margin (shock + misalignment)
                radial_kN = round(design_load * 1.3, 2)  # 30% margin

                # ---------------- AXIAL LOAD INFERENCE ----------------
                # Positioning / overturning systems → axial dominant
                if app in ["slewing_ring", "excavator_swing", "wind_turbine_yaw"]:
                    axial_kN = round(radial_kN * 0.4, 2)  # very realistic
                elif heavy_duty:
                    axial_kN = round(radial_kN * 0.2, 2)
                else:
                    axial_kN = round(radial_kN * 0.1, 2)

                # ---------------- FINAL RETURN ----------------
                return {
                    "life_hours": life,
                    "rpm": rpm,
                    "radial_load_kN": radial_kN,
                    "axial_load_kN": axial_kN,
                    "source": "expert_application_table",
                    "matched_application": app,
                    "rpm_range": rpm_range,
                    "life_range": life_range,
                    "load_range": load_range,
                    "duty_class": "heavy" if heavy_duty else "normal",
                }

        return None

    # --------------------------------------------------
    # Stage-3 Lubrication Evaluation
    # --------------------------------------------------

    ISO_VG_TABLE = {
        32: [(40, 32), (100, 5.4)],
        46: [(40, 46), (100, 6.8)],
        68: [(40, 68), (100, 8.6)],
        100: [(40, 100), (100, 11)],
        150: [(40, 150), (100, 14)],
        220: [(40, 220), (100, 19)],
        320: [(40, 320), (100, 24)],
        460: [(40, 460), (100, 30)],
    }

    def _viscosity_at_temperature(self, iso_vg: int, temperature_c: float) -> float:
        points = self.ISO_VG_TABLE.get(iso_vg)
        if iso_vg not in self.ISO_VG_TABLE:
            # Surgical fallback: Pick the closest available grade
            iso_vg = min(self.ISO_VG_TABLE.keys(), key=lambda x: abs(x - iso_vg))
        if not points:
            return None

        (t1, v1), (t2, v2) = points

        import math
        ln_v = math.log(v1) + (math.log(v2 / v1) / (t2 - t1)) * (temperature_c - t1)
        return round(math.exp(ln_v), 2)

    def _mean_diameter(self, d: Optional[float], D: Optional[float]) -> Optional[float]:
        """
        Mean bearing diameter dm = (d + D) / 2
        Safe fallback:
        • If both missing → return None
        • If only one present → approximate dm from that
        """

        try:
            if d is not None and D is not None:
                return round((float(d) + float(D)) / 2, 2)

            if d is not None:
                return round(float(d) * 2.0, 2)  # crude fallback

            if D is not None:
                return round(float(D) * 0.5, 2)  # crude fallback

        except Exception:
            pass

        return None

    def _required_viscosity_v1(self, d_m: float, rpm: float) -> float:
        n_dm = rpm * d_m

        if n_dm < 50_000:
            return 80
        elif n_dm < 200_000:
            return 60
        elif n_dm < 500_000:
            return 40
        elif n_dm < 1_000_000:
            return 28
        elif n_dm < 2_000_000:
            return 20
        else:
            return 15

    def _viscosity_ratio(self, nu: float, nu1: float) -> float:
        if nu is None or nu1 is None or nu1 == 0:
            return None
        return round(nu / nu1, 2)

    def _lubrication_verdict(self, kappa: float) -> Dict[str, str]:
        """
        SKF-aligned lubrication adequacy verdict based on viscosity ratio (kappa).
        
        κ < 0.4  → Critical - High wear risk, EP additives mandatory
        κ 0.4-1  → Marginal - Additives recommended
        κ 1-4    → Adequate - Normal operation
        κ > 4    → Excellent - May cause churning at high speeds
        """

        if kappa is None:
            return {
                "class": "UNKNOWN",
                "verdict": "Insufficient data",
                "comment": "Missing viscosity or geometry input"
            }

        if kappa < 0.4:
            return {
                "class": "CRITICAL",
                "verdict": "Inadequate lubrication - High wear risk",
                "comment": f"κ = {kappa} is critically low. Use EP/AW additives or switch to higher ISO VG grade.",
                "recommendation": "Increase ISO VG grade or use synthetic oil with EP additives"
            }
        elif kappa < 1.0:
            return {
                "class": "MARGINAL",
                "verdict": "Marginal lubrication - Additives recommended",
                "comment": f"κ = {kappa} is below optimal. Consider EP additives for extended life.",
                "recommendation": "Add EP/AW additives or consider higher viscosity grade"
            }
        elif kappa <= 4.0:
            return {
                "class": "ADEQUATE",
                "verdict": "Adequate lubrication - Normal operation",
                "comment": f"κ = {kappa} is within optimal range for full EHL film formation.",
                "recommendation": "Current oil selection is appropriate"
            }
        else:
            return {
                "class": "EXCELLENT",
                "verdict": "Excellent lubrication - Monitor for churning",
                "comment": f"κ = {kappa} is high. Watch for increased friction/heat at high speeds.",
                "recommendation": "Oil may be too viscous at high speeds, monitor temperature"
            }

    def evaluate_lubrication(
        self,
        iso_vg: Optional[int],
        temperature_c: Optional[float],
        rpm: Optional[float],
        designation: Optional[str],
        radial_load_kN: Optional[float] = None,
        axial_load_kN: Optional[float] = None
    ) -> Dict[str, Any]:

        # ---------------- Fetch bearing geometry ----------------
        d = None
        D = None
        bearing_results = []

        if designation:
            rows = (
                supabase.table("bearing_master")
                .select("*")
                .ilike("Designation", f"%{designation}%")
                .execute()
                .data
            )

            if rows:
                bearing_results = rows
                d = rows[0].get("Bore_diameter")
                D = rows[0].get("D")

        # ---------------- Compute lubrication ----------------
        d_m = self._mean_diameter(d, D) if d and D else None
        nu = self._viscosity_at_temperature(iso_vg, temperature_c) if iso_vg and temperature_c else None
        nu1 = self._required_viscosity_v1(d_m, rpm) if d_m and rpm else None
        kappa = self._viscosity_ratio(nu, nu1)

        verdict = self._lubrication_verdict(kappa)

        # ---------------- Static Safety Evaluation ----------------
        # Fallback to generic load if none provided
        p_effective = radial_load_kN
        if p_effective is None:
            safe_rpm = rpm or 1000.0
            p_effective = self.generic_safe_load(safe_rpm, 12000.0)
            safety_source = "generic_fallback"
        else:
            safety_source = "user_provided"

        # Combine with axial if present (crude P estimation)
        if axial_load_kN:
            p_effective = math.sqrt(p_effective**2 + axial_load_kN**2)

        for row in bearing_results:
            raw_co = row.get("Basic_static_load_rating")
            if raw_co:
                try:
                    Co_normalized = float(raw_co)
                    static = self.evaluate_static_safety(Co_normalized, p_effective)
                    
                    row["static_safety_factor"] = static.get("static_safety_factor")
                    row["static_safety_verdict"] = static.get("static_safety_verdict")
                    row["static_safety_class"] = static.get("static_safety_class")
                    row["static_safety_comment"] = static.get("engineering_comment")
                except Exception:
                    row["static_safety_verdict"] = "CALC_ERROR"

        return {
            "engine_version": "Kyvo-Lubrication-v1.1",
            "ready": True,
            "intent_type": "lubrication-analysis",
            "designation": designation,
            "inputs": {
                "iso_vg": iso_vg,
                "temperature_C": temperature_c,
                "rpm": rpm,
                "radial_load_kN": radial_load_kN,
                "axial_load_kN": axial_load_kN,
                "bore_d_mm": d,
                "outer_D_mm": D
            },
            "computed": {
                "mean_diameter_d_m_mm": d_m,
                "actual_viscosity_nu_cSt": nu,
                "required_viscosity_nu1_cSt":  nu1,
                "viscosity_ratio_kappa": kappa,
                "p_effective_kN": round(p_effective, 3),
                "safety_source": safety_source
            },
            "lubrication_verdict": verdict,
            "results": bearing_results
        }

    # --------------------------------------------------
    # Stage-4: Preload & Clearance Intelligence
    # --------------------------------------------------

    def check_preload_required(
            self,
            P_kN: float,
            C_kN: float,
            bearing_type: str,
            high_stiffness: bool = False
    ) -> Dict[str, Any]:

        if P_kN is None or C_kN is None or C_kN <= 0 or P_kN <= 0:
            return {
                "preload_required": False,
                "comment": "Invalid load inputs",
                "P_min_kN": None,
                "shortfall_ratio": None,
                "preload_recommendation": None,
                "bearing_class": None,
                "reasons": ["Invalid load inputs"]
            }

        # Bearing type classification
        bt = (bearing_type or "").lower()

        if "ball" in bt:
            k_min = 0.01
            bearing_class = "ball"
        elif "roller" in bt or "taper" in bt or "cylindrical" in bt or "needle" in bt:
            k_min = 0.04
            bearing_class = "roller"
        else:
            # safe default
            k_min = 0.01
            bearing_class = "ball"

        # SKF minimum load
        P_min = k_min * C_kN

        if P_kN >= P_min:
            # Minimum load satisfied — no preload required
            return {
                "preload_required": False,
                "bearing_class": bearing_class,
                "P_min_kN": round(P_min, 3),
                "shortfall_ratio": 0.0,
                "preload_recommendation": None,
                "reasons": ["Minimum load satisfied — preload not required"]
            }

        # Load shortfall ratio
        shortfall_ratio = (P_min - P_kN) / P_min

        # Preload level classification (SKF-aligned fallback)
        if shortfall_ratio < 0.25:
            preload_recommendation = "LIGHT"
        elif shortfall_ratio < 0.75:
            preload_recommendation = "MEDIUM"
        else:
            preload_recommendation = "HEAVY"

        reasons = ["Minimum load not satisfied (skidding risk)"]

        if high_stiffness:
            if preload_recommendation == "LIGHT":
                preload_recommendation = "MEDIUM"
            reasons.append("High stiffness / accuracy requirement")

        return {
            "preload_required": True,
            "bearing_class": bearing_class,
            "P_min_kN": round(P_min, 3),
            "shortfall_ratio": round(shortfall_ratio, 3),
            "preload_recommendation": preload_recommendation,
            "reasons": reasons
        }

    def compute_delta_pre(self, C_oper_um: float, preload_level: str) -> Dict[str, Any]:
        """
        Preload displacement sized as a fraction of operating clearance.
        δ_pre = α × C_oper
        """

        if C_oper_um is None or C_oper_um <= 0:
            return {"delta_pre_um": None, "comment": "Invalid operating clearance"}

        alpha_map = {
            "light": 0.15,
            "medium": 0.30,
            "heavy": 0.50
        }

        alpha = alpha_map.get((preload_level or "").lower())

        if alpha is None:
            alpha = 0.15  # safe default: LIGHT preload

        delta_pre = alpha * C_oper_um

        # Sanity clamp
        if delta_pre <= 0 or delta_pre > C_oper_um:
            return {"delta_pre_um": None, "comment": "Computed preload displacement invalid"}

        return {
            "delta_pre_um": round(delta_pre, 2),
            "alpha_fraction": alpha
        }

    def compute_stiffness(self, C0_N: float, dm_mm: float, bearing_type: str) -> Optional[float]:
        """
        SKF-aligned axial stiffness fallback:
        k ≈ K_type × (C0 / dm)   [N/µm]
        """

        if C0_N is None or dm_mm is None or dm_mm <= 0:
            return None

        bt = (bearing_type or "").lower()

        K_map = {
            "deep_groove_ball": 0.20,
            "angular_contact": 0.40,
            "cylindrical_roller": 0.45,
            "tapered_roller": 0.50,
            "needle": 0.40,
            "ball": 0.20,
            "roller": 0.45
        }

        K = None

        for key, val in K_map.items():
            if key in bt:
                K = val
                break

        if K is None:
            # Safe default (ball bearing)
            K = 0.20

        k = K * (C0_N / dm_mm)

        # Crash clamps
        if k <= 0 or k > 1e7:
            return None

        return round(k, 2)

    def compute_preload_force(self, k_N_per_um: float, delta_pre_um: float) -> float:
        """
        Core preload sizing equation:
        F_pre = k · delta_pre
        """
        if k_N_per_um is None or delta_pre_um is None:
            return None

        F_pre = k_N_per_um * delta_pre_um
        return round(F_pre, 2)

    def preload_safety_check(
            self,
            F_pre_N: float,
            C0_N: float,
            preload_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Light   : 1–2% of C0
        Medium  : 2–4% of C0
        Heavy   : 4–6% of C0   (SKF reference band only)

        Hard Kyvo clamp:
        > 5% of C0  → FAIL (absolute limit, overrides SKF heavy band)
        """

        if F_pre_N is None or C0_N is None or C0_N <= 0:
            return {
                "status": "UNKNOWN",
                "comment": "Missing preload or static rating"
            }

        ratio = F_pre_N / C0_N
        if ratio > 0.05:
            return {
                "status": "FAIL",
                "ratio": round(ratio, 3),
                "comment": "Over-preload risk (exceeds 5% of C0 — Kyvo hard clamp)"
            }

        # SKF level-specific warnings
        if preload_level == "light" and ratio > 0.02:
            return {
                "status": "WARNING",
                "ratio": round(ratio, 3),
                "comment": "Light preload exceeds 2% of C0"
            }

        if preload_level == "medium" and ratio > 0.04:
            return {
                "status": "WARNING",
                "ratio": round(ratio, 3),
                "comment": "Medium preload exceeds 4% of C0"
            }

        # NOTE:
        # Heavy preload > 5% is already FAILed above.
        # Heavy preload 4–5% is allowed but should be flagged informationally.

        if preload_level == "heavy" and ratio > 0.04:
            return {
                "status": "WARNING",
                "ratio": round(ratio, 3),
                "comment": "Heavy preload in upper SKF band (4–5% of C0)"
            }

        return {
            "status": "PASS",
            "ratio": round(ratio, 3),
            "comment": "Preload within safe SKF limits"
        }

    def evaluate_thermal_friction(
            self,
            entities: Dict[str, Any],
            calc: Dict[str, Any],
            bearing_row: Dict[str, Any]
    ) -> Dict[str, Any]:

        # Inputs
        P_kN = calc.get("P_kN")
        C_kN = bearing_row.get("Basic_dynamic_load_rating")
        n_rpm = calc.get("rpm")
        kappa = calc.get("kappa")
        nu_mm2_s = calc.get("nu_mm2_s")
        n_ref = calc.get("n_ref") or 3000
        T_oper = calc.get("T_oper_C")

        bore_mm = entities.get("bore_d_mm")
        OD_mm = entities.get("outer_D_mm")

        material_inner = (entities.get("inner_ring_material") or "steel").lower()
        material_outer = (entities.get("outer_ring_material") or "steel").lower()

        # Unit normalization
        if C_kN and C_kN > 1000:
            C_kN = C_kN / 1000.0

        if P_kN and P_kN > 1000:
            P_kN = P_kN / 1000.0

        # Guards
        if (
                P_kN is None or P_kN <= 0 or
                C_kN is None or C_kN <= 0 or
                n_rpm is None or n_rpm <= 0 or
                kappa is None or
                nu_mm2_s is None or
                bore_mm is None or
                OD_mm is None or
                T_oper is None
        ):
            return {
                "stage": "Thermal",
                "friction_factor_f": None,
                "friction_torque_Nmm": None,
                "power_loss_W": None,
                "delta_bore_mm": None,
                "delta_OD_mm": None,
                "delta_clearance_mm": None,
                "overheat_risk": "UNKNOWN",
                "decision": "Thermal/friction inputs missing"
            }

        # Geometry
        dm_mm = self._mean_diameter(bore_mm, OD_mm)

        if dm_mm is None or dm_mm <= 0:
            return {
                "stage": "Thermal",
                "friction_factor_f": None,
                "friction_torque_Nmm": None,
                "power_loss_W": None,
                "delta_bore_mm": None,
                "delta_OD_mm": None,
                "delta_clearance_mm": None,
                "overheat_risk": "UNKNOWN",
                "decision": "Mean diameter missing"
            }

        # Ratios
        load_ratio = P_kN / C_kN
        speed_ratio = n_rpm / n_ref if n_ref > 0 else None

        # Friction factor
        f = self.select_f(kappa, load_ratio, speed_ratio)

        if f is None:
            return {
                "stage": "Thermal",
                "friction_factor_f": None,
                "friction_torque_Nmm": None,
                "power_loss_W": None,
                "delta_bore_mm": None,
                "delta_OD_mm": None,
                "delta_clearance_mm": None,
                "overheat_risk": "UNKNOWN",
                "decision": "Friction factor selection failed"
            }

        # Equivalent load (no preload here)
        P_N = P_kN * 1000

        # Modular torque
        M1 = self.compute_M1(f, P_N, dm_mm)
        M0 = self.compute_M0(nu_mm2_s, n_rpm, dm_mm)

        if M0 is None or M1 is None:
            return {
                "stage": "Thermal",
                "friction_factor_f": None,
                "friction_torque_Nmm": None,
                "power_loss_W": None,
                "delta_bore_mm": None,
                "delta_OD_mm": None,
                "delta_clearance_mm": None,
                "overheat_risk": "UNKNOWN",
                "decision": "Friction torque computation failed"
            }

        M_total_Nmm = M0 + M1

        # Modular power loss
        P_loss_W = self.compute_power_loss(n_rpm, M_total_Nmm)

        if P_loss_W is None:
            return {
                "stage": "Thermal",
                "friction_factor_f": round(f, 5),
                "friction_torque_Nmm": round(M_total_Nmm, 2),
                "power_loss_W": None,
                "delta_bore_mm": None,
                "delta_OD_mm": None,
                "delta_clearance_mm": None,
                "overheat_risk": "UNKNOWN",
                "decision": "Power loss computation failed"
            }

        # Thermal expansion
        delta_T = T_oper - 20.0

        alpha_inner = 12e-6 if "steel" in material_inner else 23e-6
        alpha_outer = 12e-6 if "steel" in material_outer else 23e-6

        delta_d = bore_mm * alpha_inner * delta_T
        delta_D = OD_mm * alpha_outer * delta_T

        delta_clearance = delta_d - delta_D

        # Industrial overheat risk
        overheat = self.compute_overheat_risk(
            P_loss_W=P_loss_W,
            kappa=kappa,
            delta_clearance_mm=delta_clearance,
            n_rpm=n_rpm,
            n_ref=n_ref
        )

        return {
            "stage": "Thermal",
            "friction_factor_f": round(f, 5),
            "friction_torque_Nmm": round(M_total_Nmm, 2),
            "power_loss_W": round(P_loss_W, 2),
            "delta_bore_mm": round(delta_d, 6),
            "delta_OD_mm": round(delta_D, 6),
            "delta_clearance_mm": round(delta_clearance, 6),
            "overheat_risk": overheat.get("status"),
            "decision": ", ".join(overheat.get("reasons", [])) if overheat.get("status") != "OK" else "OK"
        }


    def compute_equivalent_load_with_preload(
            self,
            P_N: float,
            F_pre_N: float,
            contact_angle_deg: float
    ) -> Optional[float]:
        """
        SKF-aligned equivalent load under preload:
        P_eq = P + F_pre · sin(α)
        """

        if (
                P_N is None or P_N <= 0 or
                F_pre_N is None or F_pre_N <= 0 or
                contact_angle_deg is None or contact_angle_deg <= 0
        ):
            return None

        alpha_rad = math.radians(contact_angle_deg)

        sin_alpha = math.sin(alpha_rad)

        if sin_alpha <= 0:
            return None

        P_eq = P_N + F_pre_N * sin_alpha

        # Sanity clamp
        if P_eq <= P_N or P_eq > 10 * P_N:
            return None

        return round(P_eq, 2)

    def compute_M1(self, f: float, P_eq_N: float, dm_mm: float) -> Optional[float]:
        """
        Load-dependent friction torque:
        M1 = f · P_eq · dm
        Returns: N·mm
        """

        if (
                f is None or f <= 0 or
                P_eq_N is None or P_eq_N <= 0 or
                dm_mm is None or dm_mm <= 0
        ):
            return None

        M1 = f * P_eq_N * dm_mm

        # Crash clamp
        if M1 < 0 or M1 > 1e9:
            return None

        return round(M1, 3)

    # ==================================================
    # THERMAL MODULE
    # ==================================================

    def compute_M0(self, nu: float, n: float, dm: float) -> float:
        """Base friction torque: M0 = 10^-7 * (nu * n)^(2/3) * dm^3"""
        if nu is None or n is None or dm is None:
            return 0.0
        return (10**-7) * (nu * n)**(2.0/3.0) * (dm**3)

    def compute_power_loss(self, n: float, M: float) -> float:
        """Power loss in Watts: P_loss = (2 * pi * n * M) / 60 / 1000"""
        if n is None or M is None:
            return 0.0
        return (2 * 3.14159 * n * (M/1000.0)) / 60.0

    def compute_overheat_risk(self, P_loss_W: float, kappa: float, delta_clearance_mm: float, n_rpm: float, n_ref: float) -> Dict[str, Any]:
        """Determines overheat risk based on power loss, lubrication, clearance and speed."""
        overheat_risk = False
        reasons = []

        if P_loss_W > 100:
            overheat_risk = True
            reasons.append("High power loss")
        if kappa < 0.4:
            overheat_risk = True
            reasons.append("Poor lubrication")
        if delta_clearance_mm < -0.005:
            overheat_risk = True
            reasons.append("Clearance collapse risk")
        if n_ref > 0 and (n_rpm / n_ref) > 1.2:
            overheat_risk = True
            reasons.append("Overspeed")

        return {
            "status": True if overheat_risk else False,
            "reasons": reasons
        }

    # --------------------------------------------------
    # THERMAL EXPANSION
    # --------------------------------------------------

    ALPHA_STEEL = 12e-6  # Thermal expansion coefficient for steel (1/°C)
    ALPHA_ALUMINUM = 23e-6  # Thermal expansion coefficient for aluminum (1/°C)

    def compute_delta_d(self, d_mm: float, delta_T: float, material: str = "steel") -> float:
        """
        Inner ring thermal expansion.
        Δd = d × α × ΔT
        
        Args:
            d_mm: Bore diameter (mm)
            delta_T: Temperature rise from 20°C (°C)
            material: 'steel' or 'aluminum'
        
        Returns:
            Expansion in mm
        """
        if d_mm is None or delta_T is None:
            return 0.0
        alpha = self.ALPHA_ALUMINUM if material == "aluminum" else self.ALPHA_STEEL
        return round(d_mm * alpha * delta_T, 6)

    def compute_delta_D(self, D_mm: float, delta_T: float, material: str = "steel") -> float:
        """
        Outer ring thermal expansion.
        ΔD = D × α × ΔT
        
        Args:
            D_mm: Outer diameter (mm)
            delta_T: Temperature rise from 20°C (°C)
            material: 'steel' or 'aluminum'
        
        Returns:
            Expansion in mm
        """
        if D_mm is None or delta_T is None:
            return 0.0
        alpha = self.ALPHA_ALUMINUM if material == "aluminum" else self.ALPHA_STEEL
        return round(D_mm * alpha * delta_T, 6)

    def compute_clearance_change(self, delta_d_mm: float, delta_D_mm: float) -> float:
        """
        Net clearance change due to thermal expansion.
        ΔC_temp = Δd - ΔD
        
        Negative value means clearance REDUCTION (risk of seizure).
        
        Args:
            delta_d_mm: Inner ring expansion (mm)
            delta_D_mm: Outer ring expansion (mm)
        
        Returns:
            Clearance change in mm (negative = reduced)
        """
        if delta_d_mm is None or delta_D_mm is None:
            return 0.0
        return round(delta_d_mm - delta_D_mm, 6)

    def evaluate_thermal_expansion(
        self, 
        d_mm: float, 
        D_mm: float, 
        T_operating: float, 
        original_clearance_um: float = None
    ) -> Dict[str, Any]:
        """
        Complete thermal expansion analysis.
        
        Args:
            d_mm: Bore diameter (mm)
            D_mm: Outer diameter (mm)
            T_operating: Operating temperature (°C)
            original_clearance_um: Original clearance in micrometers (optional)
        
        Returns:
            Thermal expansion analysis with verdict
        """
        if d_mm is None or D_mm is None or T_operating is None:
            return {"error": "Missing input parameters"}
        
        delta_T = T_operating - 20.0  # Reference temperature is 20°C
        
        delta_d = self.compute_delta_d(d_mm, delta_T)
        delta_D = self.compute_delta_D(D_mm, delta_T)
        delta_clearance = self.compute_clearance_change(delta_d, delta_D)
        
        # Convert to micrometers for readability
        delta_d_um = round(delta_d * 1000, 2)
        delta_D_um = round(delta_D * 1000, 2)
        delta_clearance_um = round(delta_clearance * 1000, 2)
        
        # Determine verdict
        verdict = "OK"
        if delta_clearance_um < -10:
            verdict = "DANGER - Seizure risk"
        elif delta_clearance_um < -5:
            verdict = "WARNING - Significant clearance reduction"
        elif delta_clearance_um < 0:
            verdict = "CAUTION - Minor clearance reduction"
        
        result = {
            "delta_T_C": delta_T,
            "inner_ring_expansion_um": delta_d_um,
            "outer_ring_expansion_um": delta_D_um,
            "clearance_change_um": delta_clearance_um,
            "verdict": verdict
        }
        
        # If original clearance provided, calculate final clearance
        if original_clearance_um is not None:
            final_clearance = original_clearance_um + delta_clearance_um
            result["original_clearance_um"] = original_clearance_um
            result["final_clearance_um"] = round(final_clearance, 2)
            if final_clearance < 0:
                result["verdict"] = "CRITICAL - Negative clearance, bearing will seize!"
        
        return result

    def select_f(self, kappa: float, load_ratio: float, speed_ratio: float) -> float:
        """Dynamic friction factor selection based on lubrication and load conditions."""
        if kappa is None:
            return 0.002  # safe default

        if kappa < 0.4:
            return 0.004
        elif kappa < 1.0:
            return 0.003 if (load_ratio and load_ratio > 0.05) else 0.0025
        elif kappa <= 4.0:
            if load_ratio and load_ratio > 0.05:
                return 0.002 if (speed_ratio and speed_ratio < 0.7) else 0.0025
            else:
                return 0.0015 if (speed_ratio and speed_ratio < 0.7) else 0.0025
        else:
            return 0.001

    # ==================================================
    # CONTAMINATION MODULE
    # ==================================================

    def correct_friction(self, f: float, eta_c: float) -> float:
        """Corrected friction factor: f_contaminated = f / η_c"""
        if eta_c is None or eta_c <= 0:
            return f
        return round(f / eta_c, 5)

    def correct_preload(self, F_pre: float, eta_c: float) -> float:
        """Maximum allowable preload: F_pre_max_cont = η_c × F_pre"""
        if eta_c is None:
            return F_pre
        return round(eta_c * F_pre, 2)

    def correct_life(self, L: float, eta_c: float) -> float:
        """Contaminated bearing life: L_contaminated = η_c × L"""
        if eta_c is None:
            return L
        return round(eta_c * L, 2)

    def compute_a_cont(self, kappa: float, eta_c: float) -> Optional[float]:
        """a_cont ≈ κ^0.6 × η_c"""
        if kappa is None or eta_c is None:
            return None
        return round((kappa ** 0.6) * eta_c, 3)

    def infer_cleanliness(self, env_desc: str) -> str:
        """Maps user environment description to ISO cleanliness level."""
        env = (env_desc or "").lower()
        if any(k in env for k in ["lab", "clean room", "semiconductor"]):
            return "very_clean"
        if any(k in env for k in ["sealed", "filtered", "indoor"]):
            return "clean"
        if any(k in env for k in ["factory", "industrial", "workshop"]):
            return "moderate"
        if any(k in env for k in ["dusty", "outdoor", "construction", "mining"]):
            return "contaminated"
        if any(k in env for k in ["severe", "extreme", "steel mill", "foundry"]):
            return "heavily_contaminated"
        return "moderate"

    # ==================================================
    # BEARING FREQUENCY MODULE
    # ==================================================

    def compute_shaft_frequency(self, n_rpm: float) -> float:
        """
        Shaft rotational frequency.
        fr = n / 60
        
        Args:
            n_rpm: Shaft speed (rpm)
        
        Returns:
            Frequency in Hz
        """
        if n_rpm is None or n_rpm <= 0:
            return 0.0
        return round(n_rpm / 60.0, 3)

    def compute_BPFO(self, Z: int, fr: float, d: float, D: float, alpha_deg: float = 0) -> float:
        """
        Ball Pass Frequency - Outer race.
        BPFO = (Z/2) × fr × (1 - d/D × cos α)
        
        Args:
            Z: Number of rolling elements
            fr: Shaft frequency (Hz)
            d: Rolling element diameter (mm)
            D: Pitch diameter (mm)
            alpha_deg: Contact angle (degrees)
        
        Returns:
            BPFO in Hz
        """
        if Z is None or fr is None or d is None or D is None or D == 0:
            return 0.0
        alpha_rad = math.radians(alpha_deg or 0)
        return round((Z / 2.0) * fr * (1 - (d / D) * math.cos(alpha_rad)), 2)

    def compute_BPFI(self, Z: int, fr: float, d: float, D: float, alpha_deg: float = 0) -> float:
        """
        Ball Pass Frequency - Inner race.
        BPFI = (Z/2) × fr × (1 + d/D × cos α)
        
        Args:
            Z: Number of rolling elements
            fr: Shaft frequency (Hz)
            d: Rolling element diameter (mm)
            D: Pitch diameter (mm)
            alpha_deg: Contact angle (degrees)
        
        Returns:
            BPFI in Hz
        """
        if Z is None or fr is None or d is None or D is None or D == 0:
            return 0.0
        alpha_rad = math.radians(alpha_deg or 0)
        return round((Z / 2.0) * fr * (1 + (d / D) * math.cos(alpha_rad)), 2)

    def compute_BSF(self, fr: float, d: float, D: float, alpha_deg: float = 0) -> float:
        """
        Ball Spin Frequency.
        BSF = (D / 2d) × fr × (1 - (d/D × cos α)²)
        
        Args:
            fr: Shaft frequency (Hz)
            d: Rolling element diameter (mm)
            D: Pitch diameter (mm)
            alpha_deg: Contact angle (degrees)
        
        Returns:
            BSF in Hz
        """
        if fr is None or d is None or D is None or d == 0 or D == 0:
            return 0.0
        alpha_rad = math.radians(alpha_deg or 0)
        ratio = (d / D) * math.cos(alpha_rad)
        return round((D / (2.0 * d)) * fr * (1 - ratio ** 2), 2)

    def compute_FTF(self, fr: float, d: float, D: float, alpha_deg: float = 0) -> float:
        """
        Fundamental Train Frequency (Cage frequency).
        FTF = (1/2) × fr × (1 - d/D × cos α)
        
        Args:
            fr: Shaft frequency (Hz)
            d: Rolling element diameter (mm)
            D: Pitch diameter (mm)
            alpha_deg: Contact angle (degrees)
        
        Returns:
            FTF in Hz
        """
        if fr is None or d is None or D is None or D == 0:
            return 0.0
        alpha_rad = math.radians(alpha_deg or 0)
        return round(0.5 * fr * (1 - (d / D) * math.cos(alpha_rad)), 2)

    def compute_bearing_frequencies(
        self,
        n_rpm: float,
        Z: int,
        d_ball: float,
        D_pitch: float,
        alpha_deg: float = 0
    ) -> Dict[str, float]:
        """
        Calculate all bearing characteristic frequencies.
        
        Args:
            n_rpm: Shaft speed (rpm)
            Z: Number of rolling elements
            d_ball: Rolling element diameter (mm)
            D_pitch: Pitch diameter (mm)
            alpha_deg: Contact angle (degrees)
        
        Returns:
            Dictionary with all frequencies in Hz
        """
        fr = self.compute_shaft_frequency(n_rpm)
        
        return {
            "shaft_freq_Hz": fr,
            "BPFO_Hz": self.compute_BPFO(Z, fr, d_ball, D_pitch, alpha_deg),
            "BPFI_Hz": self.compute_BPFI(Z, fr, d_ball, D_pitch, alpha_deg),
            "BSF_Hz": self.compute_BSF(fr, d_ball, D_pitch, alpha_deg),
            "FTF_Hz": self.compute_FTF(fr, d_ball, D_pitch, alpha_deg),
            "input_rpm": n_rpm
        }

    # ==================================================
    # GEOMETRY INFERENCE MODULE (Group 1)
    # ==================================================

    # Typical geometry data for common bearing series
    BEARING_SERIES_DATA = {
        # Series: (typical_Z, typical_d_ball_mm, d_over_D_ratio)
        "60": (7, 6.35, 0.16),    # 600x series (miniature)
        "62": (8, 9.525, 0.18),   # 620x series (light)
        "63": (8, 12.7, 0.20),    # 630x series (medium)
        "64": (8, 15.875, 0.21),  # 640x series (heavy)
        "72": (12, 8.0, 0.17),    # Angular contact 72xx
        "73": (13, 11.0, 0.19),   # Angular contact 73xx
        "NU": (12, None, 0.15),   # Cylindrical roller
        "NJ": (12, None, 0.15),   # Cylindrical roller
        "32": (17, None, 0.18),   # Tapered roller
        "30": (15, None, 0.17),   # Tapered roller
    }

    def infer_geometry_from_catalog(self, designation: str) -> Dict[str, Any]:
        """
        Infer bearing geometry (Z, d, D_pitch) from designation.
        
        Args:
            designation: Bearing designation (e.g., "6208", "7206")
        
        Returns:
            Dictionary with inferred geometry parameters
        """
        if not designation:
            return {"error": "No designation provided"}
        
        # Clean designation
        des = designation.upper().strip()
        
        # Extract series prefix
        series = None
        for prefix in ["NU", "NJ", "32", "30", "72", "73", "64", "63", "62", "60"]:
            if des.startswith(prefix):
                series = prefix
                break
        
        if not series:
            # Try to extract 2-digit series from standard ball bearings
            import re
            match = re.match(r"(\d{2})\d+", des)
            if match:
                series = match.group(1)
        
        if series and series in self.BEARING_SERIES_DATA:
            Z, d_ball, d_over_D = self.BEARING_SERIES_DATA[series]
            return {
                "designation": designation,
                "series": series,
                "inferred_Z": Z,
                "inferred_d_ball_mm": d_ball,
                "inferred_d_over_D_ratio": d_over_D,
                "source": "series_lookup"
            }
        
        # Default fallback
        return {
            "designation": designation,
            "series": "unknown",
            "inferred_Z": 9,
            "inferred_d_ball_mm": 10.0,
            "inferred_d_over_D_ratio": 0.18,
            "source": "default_fallback"
        }

    def infer_pitch_diameter_from_dimensions(self, d_bore_mm: float, D_outer_mm: float) -> float:
        """
        Calculate pitch diameter from bore and outer diameter.
        D_pitch ≈ (d + D) / 2
        
        Args:
            d_bore_mm: Bore diameter (mm)
            D_outer_mm: Outer diameter (mm)
        
        Returns:
            Pitch diameter in mm
        """
        if d_bore_mm is None or D_outer_mm is None:
            return None
        return round((d_bore_mm + D_outer_mm) / 2.0, 2)

    def infer_ball_diameter_from_series(self, series: str, d_bore_mm: float = None) -> float:
        """
        Estimate ball/roller diameter from bearing series.
        
        Args:
            series: Bearing series (e.g., "62", "63")
            d_bore_mm: Bore diameter for refined estimate
        
        Returns:
            Estimated ball diameter in mm
        """
        if series and series in self.BEARING_SERIES_DATA:
            _, d_ball, _ = self.BEARING_SERIES_DATA[series]
            if d_ball:
                return d_ball
        
        # Fallback: estimate from bore diameter
        if d_bore_mm:
            # Typical ball diameter ≈ 0.2 to 0.3 × bore
            return round(d_bore_mm * 0.25, 2)
        
        return 10.0  # Default

    def infer_roller_count_from_series(self, series: str, d_bore_mm: float = None) -> int:
        """
        Estimate number of rolling elements from series.
        
        Args:
            series: Bearing series
            d_bore_mm: Bore diameter for refined estimate
        
        Returns:
            Estimated roller/ball count
        """
        if series and series in self.BEARING_SERIES_DATA:
            Z, _, _ = self.BEARING_SERIES_DATA[series]
            return Z
        
        # Fallback: estimate from bore
        if d_bore_mm:
            if d_bore_mm < 20:
                return 7
            elif d_bore_mm < 50:
                return 9
            elif d_bore_mm < 100:
                return 11
            else:
                return 13
        
        return 9  # Default

    # ==================================================
    # DEFAULT VALUES MODULE
    # ==================================================

    def get_default_contact_angle(self, bearing_type: str) -> float:
        """
        Get default contact angle in degrees.
        
        Args:
            bearing_type: Type of bearing
        
        Returns:
            Contact angle in degrees
        """
        angles = {
            "ball": 0,
            "dgbb": 0,           # Deep groove ball bearing
            "angular_15": 15,
            "angular_25": 25,
            "angular_40": 40,
            "angular": 15,       # Default angular
            "tapered": 15,
            "roller": 0,
            "thrust": 90
        }
        return angles.get(bearing_type.lower(), 0)

    def get_default_d_over_D_ratio(self, series: str = None) -> float:
        """
        Get default d/D ratio (ball diameter / pitch diameter).
        
        Args:
            series: Bearing series if known
        
        Returns:
            Default d/D ratio
        """
        if series and series in self.BEARING_SERIES_DATA:
            _, _, ratio = self.BEARING_SERIES_DATA[series]
            return ratio
        return 0.18  # Typical for most bearings

    # ==================================================
    # HARMONICS & SEVERITY MODULE
    # ==================================================

    def refine_diagnosis_with_harmonics(
        self,
        observed_freqs: list,
        base_frequency: float,
        tolerance_percent: float = 5.0
    ) -> Dict[str, Any]:
        """
        Check for harmonic peaks (2x, 3x, 4x) to confirm and refine diagnosis.
        Multiple harmonics indicate more severe damage.
        
        Args:
            observed_freqs: List of observed peak frequencies (Hz)
            base_frequency: The suspected defect frequency (Hz)
            tolerance_percent: Matching tolerance
        
        Returns:
            Harmonic analysis with severity indication
        """
        if not observed_freqs or not base_frequency:
            return {"error": "Missing input data"}
        
        harmonics_found = []
        tolerance = tolerance_percent / 100.0
        
        for harmonic in [1, 2, 3, 4, 5]:
            expected = base_frequency * harmonic
            for obs in observed_freqs:
                if abs(obs - expected) / expected <= tolerance:
                    harmonics_found.append({
                        "harmonic": f"{harmonic}x",
                        "expected_Hz": round(expected, 2),
                        "observed_Hz": obs
                    })
                    break
        
        harmonic_count = len(harmonics_found)
        
        if harmonic_count >= 4:
            severity = "CRITICAL"
        elif harmonic_count >= 3:
            severity = "HIGH"
        elif harmonic_count >= 2:
            severity = "MODERATE"
        elif harmonic_count >= 1:
            severity = "LOW"
        else:
            severity = "NONE"
        
        return {
            "base_frequency_Hz": base_frequency,
            "harmonics_found": harmonics_found,
            "harmonic_count": harmonic_count,
            "severity": severity,
            "recommendation": "Immediate replacement" if severity == "CRITICAL" else
                            "Plan replacement" if severity == "HIGH" else
                            "Monitor closely" if severity == "MODERATE" else
                            "Continue monitoring"
        }

    def classify_severity_from_amplitude(
        self,
        amplitude_g: float,
        baseline_g: float = 0.1
    ) -> Dict[str, str]:
        """
        Classify defect severity based on vibration amplitude.
        
        Args:
            amplitude_g: Measured amplitude (g or mm/s)
            baseline_g: Normal baseline amplitude
        
        Returns:
            Severity classification
        """
        if amplitude_g is None or baseline_g is None or baseline_g <= 0:
            return {"error": "Invalid input"}
        
        ratio = amplitude_g / baseline_g
        
        if ratio < 2:
            return {"severity": "NORMAL", "ratio": round(ratio, 2), "action": "No action"}
        elif ratio < 4:
            return {"severity": "LOW", "ratio": round(ratio, 2), "action": "Monitor"}
        elif ratio < 8:
            return {"severity": "MODERATE", "ratio": round(ratio, 2), "action": "Plan maintenance"}
        elif ratio < 16:
            return {"severity": "HIGH", "ratio": round(ratio, 2), "action": "Schedule replacement"}
        else:
            return {"severity": "CRITICAL", "ratio": round(ratio, 2), "action": "Immediate shutdown"}

    # ==================================================
    # FFT & SAMPLING MODULE
    # ==================================================

    def get_recommended_fft_window(self, signal_type: str = "vibration") -> Dict[str, str]:
        """
        Recommend FFT window function.
        
        Args:
            signal_type: 'vibration', 'impact', 'continuous'
        
        Returns:
            Recommended window and reason
        """
        recommendations = {
            "vibration": {
                "window": "Hanning",
                "reason": "Good frequency resolution for periodic signals"
            },
            "impact": {
                "window": "Flat-top",
                "reason": "Better amplitude accuracy for transient events"
            },
            "continuous": {
                "window": "Hamming",
                "reason": "Good general-purpose window for continuous signals"
            },
            "transient": {
                "window": "Rectangular",
                "reason": "Preserves transient shape"
            }
        }
        return recommendations.get(signal_type, recommendations["vibration"])

    def get_sampling_rate(self, max_frequency_Hz: float, safety_factor: float = 2.56) -> Dict[str, float]:
        """
        Calculate minimum sampling rate using Nyquist theorem.
        
        Args:
            max_frequency_Hz: Maximum frequency of interest
            safety_factor: Multiplier (default 2.56 for anti-aliasing)
        
        Returns:
            Recommended sampling parameters
        """
        if max_frequency_Hz is None or max_frequency_Hz <= 0:
            return {"error": "Invalid frequency"}
        
        min_sample_rate = max_frequency_Hz * safety_factor
        
        # Round up to common rates
        common_rates = [1024, 2048, 4096, 8192, 16384, 32768, 65536]
        recommended_rate = min_sample_rate
        for rate in common_rates:
            if rate >= min_sample_rate:
                recommended_rate = rate
                break
        
        return {
            "max_frequency_Hz": max_frequency_Hz,
            "nyquist_min_Hz": round(max_frequency_Hz * 2, 2),
            "recommended_sample_rate_Hz": recommended_rate,
            "samples_per_second": recommended_rate
        }

    def recommend_sensor_type(self, rpm: float, frequency_range: str = "low") -> Dict[str, str]:
        """
        Recommend vibration sensor type based on application.
        
        Args:
            rpm: Operating speed
            frequency_range: 'low', 'medium', 'high'
        
        Returns:
            Sensor recommendation
        """
        if rpm is None:
            return {"error": "RPM required"}
        
        # Calculate shaft frequency
        shaft_freq = rpm / 60.0
        
        if shaft_freq < 10 or frequency_range == "low":
            return {
                "sensor": "Velocity sensor",
                "type": "Piezoelectric velocity",
                "frequency_range": "1-1000 Hz",
                "reason": "Better sensitivity at low frequencies"
            }
        elif shaft_freq > 100 or frequency_range == "high":
            return {
                "sensor": "Accelerometer",
                "type": "IEPE/ICP accelerometer",
                "frequency_range": "10-10000 Hz",
                "reason": "Required for high-frequency bearing defects"
            }
        else:
            return {
                "sensor": "Accelerometer",
                "type": "General purpose IEPE",
                "frequency_range": "5-5000 Hz",
                "reason": "Good balance for medium-speed applications"
            }

    # ==================================================
    # SCALING VALIDATION MODULE
    # ==================================================

    def validate_linear_scaling(
        self,
        original_rpm: float,
        new_rpm: float,
        max_ratio: float = 3.0
    ) -> Dict[str, Any]:
        """
        Validate if linear frequency scaling is appropriate.
        Large RPM changes may introduce non-linear effects.
        
        Args:
            original_rpm: Original RPM used for calculation
            new_rpm: New RPM to scale to
            max_ratio: Maximum acceptable scaling ratio
        
        Returns:
            Validation result
        """
        if original_rpm is None or new_rpm is None or original_rpm <= 0:
            return {"valid": False, "error": "Invalid RPM values"}
        
        ratio = new_rpm / original_rpm
        
        if ratio > max_ratio or ratio < (1 / max_ratio):
            return {
                "valid": False,
                "scale_ratio": round(ratio, 3),
                "warning": f"Scale ratio {ratio:.2f} exceeds recommended range. Non-linear effects may occur.",
                "recommendation": "Recalculate frequencies at new RPM"
            }
        
        return {
            "valid": True,
            "scale_ratio": round(ratio, 3),
            "message": "Linear scaling appropriate"
        }

    def apply_slip_correction(
        self,
        calculated_freq: float,
        rpm: float,
        load_ratio: float = 0.5
    ) -> Dict[str, float]:
        """
        Apply slip correction for high-speed or low-load conditions.
        Rolling elements may slip instead of pure rolling.
        
        Args:
            calculated_freq: Calculated defect frequency (Hz)
            rpm: Operating speed
            load_ratio: P/C ratio (lower = more slip)
        
        Returns:
            Corrected frequency with slip factor
        """
        if calculated_freq is None or rpm is None:
            return {"error": "Invalid input"}
        
        # Slip is more pronounced at high speed and low load
        base_slip = 0.0
        
        # High speed penalty
        if rpm > 3000:
            base_slip += 0.02
        if rpm > 6000:
            base_slip += 0.03
        
        # Low load penalty
        if load_ratio < 0.02:
            base_slip += 0.05
        elif load_ratio < 0.05:
            base_slip += 0.02
        
        slip_factor = min(base_slip, 0.10)  # Cap at 10%
        corrected_freq = calculated_freq * (1 - slip_factor)
        
        return {
            "original_freq_Hz": calculated_freq,
            "slip_factor": round(slip_factor, 4),
            "corrected_freq_Hz": round(corrected_freq, 2),
            "slip_percent": round(slip_factor * 100, 2)
        }

    def compute_contamination_factor(
            self,
            environment: Optional[str],
            sealing_type: Optional[str],
            filtration_grade: Optional[str],
            oil_cleanliness_code: Optional[str],
            bearing_size_class: Optional[str] = None
    ) -> Optional[float]:

        if environment is None and sealing_type is None and filtration_grade is None and oil_cleanliness_code is None:
            return None

        ENV_MAP = {
            "very_clean": 1.00,
            "clean": 0.85,
            "moderate": 0.65,
            "contaminated": 0.45,
            "heavily_contaminated": 0.25
        }

        env_key = (environment or "moderate").strip().lower()

        if env_key not in ENV_MAP:
            env_key = "moderate"  # conservative fallback

        eta_c = ENV_MAP[env_key]

        SEAL_MAP = {
            "open": 0.70,
            "zz": 0.85,
            "2z": 0.85,
            "rs": 0.95,
            "2rs": 0.95,
            "contact": 1.00
        }

        seal_key = (sealing_type or "").strip().lower()
        if seal_key in SEAL_MAP:
            eta_c *= SEAL_MAP[seal_key]

        FILTRATION_MAP = {
            "none": 0.70,
            "coarse": 0.85,
            "medium": 0.95,
            "fine": 1.00
        }

        filt_key = (filtration_grade or "").strip().lower()
        if filt_key in FILTRATION_MAP:
            eta_c *= FILTRATION_MAP[filt_key]

        # ISO 4406 parsing — CORRECT
        if oil_cleanliness_code:
            try:
                parts = oil_cleanliness_code.strip().split("/")

                if len(parts) >= 2:
                    iso_major = int(parts[0])

                    if iso_major <= 14:
                        eta_c *= 1.00
                    elif 15 <= iso_major <= 17:
                        eta_c *= 0.85
                    elif 18 <= iso_major <= 20:
                        eta_c *= 0.65
                    else:
                        eta_c *= 0.45

            except Exception:
                return None

        SIZE_MAP = {
            "small": 1.00,
            "medium": 0.90,
            "large": 0.80
        }

        size_key = (bearing_size_class or "").strip().lower()
        if size_key in SIZE_MAP:
            eta_c *= SIZE_MAP[size_key]

        # SKF realism clamps
        if eta_c < 0.30:
            return None

        if eta_c > 1.00:
            eta_c = 1.00

        return round(eta_c, 3)

    def compute_ranking_penalty(
            self,
            overheat_risk: bool,
            kappa: float,
            clearance_collapse_ratio: float,
            eta_c: float,
            preload_level: Optional[str],
            life_ratio: float
    ) -> Optional[float]:
        """
        Industrial-grade ranking penalty multiplier.

        Returns:
            multiplier ∈ (0.05 … 1.00)
            Lower = worse candidate
        """

        # -------------------------------
        # Crash guards
        # -------------------------------
        if (
                overheat_risk is None or
                kappa is None or kappa <= 0 or
                clearance_collapse_ratio is None or clearance_collapse_ratio < 0 or
                eta_c is None or eta_c <= 0 or
                life_ratio is None or life_ratio <= 0
        ):
            return None

        multiplier = 1.0
        reasons = []

        # -------------------------------
        # Thermal risk penalty
        # -------------------------------
        if overheat_risk:
            multiplier *= 0.70  # −30%
            reasons.append("Overheat risk")

        # -------------------------------
        # Lubrication penalty
        # -------------------------------
        if kappa < 0.4:
            multiplier *= 0.80  # −20%
            reasons.append("Poor lubrication (κ < 0.4)")

        # -------------------------------
        # Clearance collapse penalty
        # -------------------------------
        if clearance_collapse_ratio > 0.40:
            multiplier *= 0.75  # −25%
            reasons.append("Severe clearance collapse")

        # -------------------------------
        # Contamination penalty
        # -------------------------------
        if eta_c < 0.60:
            multiplier *= 0.70  # −30%
            reasons.append("High contamination (ηc < 0.6)")

        # -------------------------------
        # Preload severity penalty
        # -------------------------------
        pl = (preload_level or "").lower()

        if pl == "heavy":
            multiplier *= 0.85  # −15%
            reasons.append("Heavy preload")

        # -------------------------------
        # Life reduction penalty
        # -------------------------------
        # life_ratio = (P / P_eq)^p
        # If life_ratio < 0.6 → more than 40% life loss
        if life_ratio < 0.60:
            multiplier *= 0.75  # −25%
            reasons.append("Severe life reduction")

        if eta_c < 0.60:
            multiplier *= 0.70
            reasons.append("High contamination (ηc < 0.6)")

        # ADD THIS
        if eta_c < 0.40:
            multiplier *= 0.70
            reasons.append("Severe contamination")

        # ADD THIS
        if life_ratio < 0.50:
            multiplier *= 0.70
            reasons.append("Catastrophic life reduction")

        # -------------------------------
        # Final clamps
        # -------------------------------
        if multiplier < 0.05:
            multiplier = 0.05

        if multiplier > 1.00:
            multiplier = 1.00

        return round(multiplier, 3)

    def apply_ranking_penalty(
            self,
            base_score: float,
            preload_stage4: Optional[Dict[str, Any]],
            thermal_stage: Optional[Dict[str, Any]],
            contamination_stage: Optional[Dict[str, Any]],
            calc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Injects industrial safety penalties into Kyvo ranking score.
        """

        # -------------------------------
        # Crash guards
        # -------------------------------
        if base_score is None or base_score <= 0:
            return {
                "final_score": None,
                "ranking_penalty_multiplier": None,
                "ranking_penalty_reasons": ["Invalid base score"]
            }

        # -------------------------------
        # Extract inputs
        # -------------------------------
        overheat_risk = (
            thermal_stage.get("overheat_risk")
            if thermal_stage else None
        )

        kappa = calc.get("kappa")

        clearance_collapse_ratio = (
            preload_stage4.get("clearance_collapse_ratio")
            if preload_stage4 else None
        )

        eta_c = (
            contamination_stage.get("contamination_factor")
            if contamination_stage else None
        )

        preload_level = (
            preload_stage4.get("preload_level")
            if preload_stage4 else None
        )

        life_ratio = (
            preload_stage4.get("life_reduction_ratio")
            if preload_stage4 else None
        )

        # -------------------------------
        # Compute penalty multiplier
        # -------------------------------
        multiplier = self.compute_ranking_penalty(
            overheat_risk=overheat_risk,
            kappa=kappa,
            clearance_collapse_ratio=clearance_collapse_ratio,
            eta_c=eta_c,
            preload_level=preload_level,
            life_ratio=life_ratio
        )

        if multiplier is None:
            return {
                "final_score": base_score * 0.50,  # hard conservative fallback
                "ranking_penalty_multiplier": None,
                "ranking_penalty_reasons": ["Ranking penalty inputs missing — conservative fallback"]
            }

        final_score = base_score * multiplier

        # -------------------------------
        # Collect explainability reasons
        # -------------------------------
        reasons = []

        if overheat_risk:
            reasons.append("Overheat risk")

        if kappa is not None and kappa < 0.4:
            reasons.append("Poor lubrication")

        if clearance_collapse_ratio is not None and clearance_collapse_ratio > 0.40:
            reasons.append("Severe clearance collapse")

        if eta_c is not None and eta_c < 0.60:
            reasons.append("High contamination")

        if preload_level == "heavy":
            reasons.append("Heavy preload")

        if life_ratio is not None and life_ratio < 0.60:
            reasons.append("Severe life reduction")

        return {
            "final_score": round(final_score, 4),
            "ranking_penalty_multiplier": multiplier,
            "ranking_penalty_reasons": reasons
        }

    def evaluate_preload_stage4(
            self,
            entities: Dict[str, Any],
            calc: Dict[str, Any],
            bearing_row: Dict[str, Any],
            C_oper_um: Optional[float] = None,
            high_stiffness: bool = False
    ) -> Dict[str, Any]:

        static_sf = calc.get("static_safety_factor")

        if static_sf is not None and static_sf < 1.0:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Static safety < 1.0 — preload skipped",
                "static_safety_factor": static_sf
            }

        P_kN = calc.get("P_kN")
        rpm = calc.get("rpm") or 0

        C_kN = bearing_row.get("Basic_dynamic_load_rating")
        C0_raw = bearing_row.get("Basic_static_load_rating")

        bearing_type = entities.get("bearing_type") or ""

        contact_angle_deg = (
                entities.get("contact_angle_deg") or
                bearing_row.get("Contact_angle_deg")
        )

        # Contamination inputs
        environment = calc.get("environment")
        filtration_grade = calc.get("filtration_grade")
        oil_cleanliness_code = calc.get("oil_cleanliness_code")
        sealing_type = entities.get("sealing_type")

        # Unit normalization
        if C_kN and C_kN > 1000:
            C_kN = C_kN / 1000.0

        if C0_raw and C0_raw > 1000:
            C0_kN = C0_raw / 1000.0
        else:
            C0_kN = C0_raw

        C0_N = C0_kN * 1000 if C0_kN else None

        # Geometry
        d = entities.get("bore_d_mm")
        D = entities.get("outer_D_mm")

        dm_mm = self._mean_diameter(d, D)

        if dm_mm is None or dm_mm <= 0:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Bearing geometry missing"
            }

        # Hard sanity checks
        if (
                P_kN is None or P_kN <= 0 or
                C_kN is None or C_kN <= 0 or
                C0_N is None or C0_N <= 0
        ):
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Invalid preload inputs"
            }

        # Decision
        decision = self.check_preload_required(
            P_kN=P_kN,
            C_kN=C_kN,
            bearing_type=bearing_type,
            high_stiffness=high_stiffness
        )

        if not decision["preload_required"]:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Preload not required",
                "decision": decision
            }

        preload_level = (decision.get("preload_recommendation") or "light").lower()

        if preload_level == "heavy" and not high_stiffness:
            preload_level = "medium"

        if C_oper_um is None or C_oper_um <= 0:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Operating clearance missing",
                "decision": decision
            }

        delta = self.compute_delta_pre(C_oper_um, preload_level)
        delta_pre_um = delta.get("delta_pre_um")

        if delta_pre_um is None:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Preload displacement failed",
                "decision": decision
            }

        k = self.compute_stiffness(C0_N, dm_mm, bearing_type)

        if k is None:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Bearing stiffness failed",
                "decision": decision
            }

        F_pre = self.compute_preload_force(k, delta_pre_um)

        if F_pre is None or F_pre <= 0:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Preload force failed",
                "decision": decision
            }

        # ---- Preload → clearance collapse ----
        delta_C_preload_um = F_pre / k
        clearance_collapse_ratio = delta_C_preload_um / C_oper_um

        final_clearance_um = C_oper_um - delta_C_preload_um

        if final_clearance_um <= 0:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Negative clearance after preload",
                "decision": decision
            }

        if clearance_collapse_ratio > 0.70:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Excessive clearance collapse due to preload",
                "decision": decision
            }

        if contact_angle_deg is None or contact_angle_deg <= 0:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Contact angle missing",
                "decision": decision
            }

        P_N = P_kN * 1000

        P_eq_N = self.compute_equivalent_load_with_preload(
            P_N=P_N,
            F_pre_N=F_pre,
            contact_angle_deg=contact_angle_deg
        )

        if P_eq_N is None:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Equivalent load failed",
                "decision": decision
            }

        bearing_class = decision.get("bearing_class")
        p_exp = 3.0 if bearing_class == "ball" else 10.0 / 3.0

        # Clean life
        life_ratio = round((P_N / P_eq_N) ** p_exp, 3)
        L_pre = round((C_kN * 1000 / P_eq_N) ** p_exp, 3)

        # ---- ISO contamination factor ηc ----
        eta_c = self.compute_contamination_factor(
            environment=environment,
            sealing_type=sealing_type,
            filtration_grade=filtration_grade,
            oil_cleanliness_code=oil_cleanliness_code,
            bearing_size_class=None
        )

        if eta_c is None or eta_c <= 0.330:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Contamination factor invalid or unsafe",
                "decision": decision
            }

        # Contaminated life
        L_final = round(eta_c * L_pre, 3)

        life_collapse_ratio = L_final / L_pre

        if life_collapse_ratio < 0.50:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Catastrophic life collapse due to contamination",
                "decision": decision
            }

        # Catastrophic life collapse guard
        if L_final < 0.20 * L_pre:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Excessive life loss due to contamination",
                "decision": decision
            }

        # ---- Thermal guard ----
        kappa = calc.get("kappa")
        n_ref = calc.get("n_ref") or 3000

        load_ratio = P_kN / C_kN
        speed_ratio = rpm / n_ref if n_ref > 0 else None

        f = self.select_f(kappa, load_ratio, speed_ratio)

        if f is None:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Friction factor failed",
                "decision": decision
            }

        M1_pre = self.compute_M1(f, P_eq_N, dm_mm)
        M1_base = self.compute_M1(f, P_N, dm_mm)

        if M1_pre is None or M1_base is None:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Friction torque failed",
                "decision": decision
            }

        delta_M1 = M1_pre - M1_base

        P_loss_W = self.compute_power_loss(rpm, delta_M1)

        if P_loss_W is None:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Preload power loss failed",
                "decision": decision
            }

        # Thermal runaway clamp
        if P_loss_W > 150:
            return {
                "stage": "Stage-4",
                "preload_required": False,
                "comment": "Thermal runaway risk due to preload",
                "decision": decision
            }

        safety = self.preload_safety_check(F_pre, C0_N, preload_level)

        return {
            "stage": "Stage-4",
            "preload_required": True,
            "preload_level": preload_level,
            "delta_pre_um": delta_pre_um,
            "alpha_fraction": delta.get("alpha_fraction"),
            "stiffness_k_N_per_um": k,
            "preload_force_N": round(F_pre, 0),
            "equivalent_load_kN": round(P_eq_N / 1000, 3),
            "life_reduction_ratio": life_ratio,
            "preloaded_life_index": L_pre,
            "contamination_factor": eta_c,
            "final_life_index": L_final,
            "clearance_collapse_um": round(delta_C_preload_um, 2),
            "clearance_collapse_ratio": round(clearance_collapse_ratio, 3),
            "final_clearance_um": round(final_clearance_um, 2),
            "additional_power_loss_W": round(P_loss_W, 2),
            "safety": safety,
            "decision": decision
        }

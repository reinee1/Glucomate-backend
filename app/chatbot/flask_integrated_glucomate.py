# app/chatbot/flask_integrated_glucomate.py
"""
Flask-Integrated GlucoMate (no migrations)
- Persists state via StateStore (Redis/file/in-mem)
- Throttles weekly prompts
- Safe medication reminder behavior (no infinite loops by default)
- LLM-safe: graceful fallbacks if Bedrock creds/region are wrong
- Queues unsent weekly assessments and retries on next request
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
import sys
import re

# Ensure app package importable
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.extensions import db
from app.models import (
    User, MedicalProfile, MedicalHistory, UserMedication, Monitoring, Lifestyle,
    MedicalReminder, WeeklyAssessment
)
from app.utils.state_store import StateStore
from app.chatbot.clean_bedrock_web_crawler import BedrockWebCrawlerGlucoMate

logger = logging.getLogger(__name__)

# ---------------------------- Env flags ----------------------------
GLUCOMATE_ENABLE_MONITOR = os.getenv("GLUCOMATE_ENABLE_MONITOR", "0") == "1"
GLUCOMATE_AUTO_MONITOR_ON_REQUEST = os.getenv("GLUCOMATE_AUTO_MONITOR_ON_REQUEST", "0") == "1"
GLUCOMATE_ENABLE_WEEKLY_CHECKIN = os.getenv("GLUCOMATE_ENABLE_WEEKLY_CHECKIN", "1") == "1"
GLUCOMATE_PERSONALIZE_RESPONSES = os.getenv("GLUCOMATE_PERSONALIZE_RESPONSES", "1") == "1"

try:
    REMINDER_GRACE_MINUTES = int(os.getenv("GLUCOMATE_REMINDER_GRACE_MINUTES", "2"))
except ValueError:
    REMINDER_GRACE_MINUTES = 2

try:
    MAX_MONITOR_SECS = int(os.getenv("GLUCOMATE_MAX_MONITOR_SECS", "300"))
except ValueError:
    MAX_MONITOR_SECS = 300

WEEKLY_PROMPT_THROTTLE_HOURS = int(os.getenv("WEEKLY_PROMPT_THROTTLE_HOURS", "24"))

# State store (Redis → file → in-mem)
_STATE = StateStore(namespace="glucomate", default_ttl_secs=14 * 24 * 3600)
_GLUCO_INSTANCES = {}  # optional per-user reuse


# ---------------------------- DB adapter ----------------------------
class FlaskPostgreSQLDatabase:
    def get_patient_profile(self, user_id):
        try:
            user = User.query.get(user_id)
            if not user:
                return None

            profile = {
                "user_id": user.id,
                "name": f"{user.first_name} {user.last_name}".strip(),
                "email": user.email,
            }

            medical = MedicalProfile.query.filter_by(user_id=user_id).first()
            if medical:
                profile.update({
                    "date_of_birth": medical.date_of_birth,
                    "gender": medical.gender,
                    "weight": medical.weight,
                    "height": medical.height,
                    "diabetes_type": medical.diabetes_type,
                    "diagnosis_year": medical.diagnosis_year,
                    "age": self._age(medical.date_of_birth) if medical.date_of_birth else None,
                })

            monitoring = Monitoring.query.filter_by(user_id=user_id).first()
            if monitoring:
                profile.update({
                    "glucose_frequency": monitoring.glucose_frequency,
                    "hba1c": float(monitoring.latest_hba1c_percent) if monitoring.latest_hba1c_percent else None,
                    "uses_cgm": monitoring.uses_cgm,
                    "frequent_hypoglycemia": monitoring.frequent_hypoglycemia,
                })

            lifestyle = Lifestyle.query.filter_by(user_id=user_id).first()
            if lifestyle:
                profile.update({
                    "smoking_status": lifestyle.smoking_status,
                    "alcohol_consumption": lifestyle.alcohol_consumption,
                    "activity_level": lifestyle.exercise_frequency,
                })

            meds = UserMedication.query.filter_by(user_id=user_id).all()
            profile["medications"] = [(m.medication_name, m.dosage, m.frequency) for m in meds]

            reminders = MedicalReminder.query.filter_by(user_id=user_id, active=True).all()
            profile["medication_reminders"] = [
                (r.medication_name, r.dosage, r.frequency, r.time_of_day) for r in reminders
            ]

            return profile
        except Exception as e:
            logger.exception("get_patient_profile error: %s", e)
            return None

    def _age(self, dob):
        today = datetime.now().date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    
    def save_weekly_assessment(self, user_id, assessment_data):
        """Save weekly assessment using Flask WeeklyAssessment model"""
        try:
            # Always use Monday as the week key
            today = datetime.utcnow().date()
            week_start = today - timedelta(days=today.weekday())

            existing = WeeklyAssessment.query.filter_by(
                user_id=user_id,
                week_date=week_start
            ).first()

            # ---- Normalize all types ----
            gf = self._freq_to_int(assessment_data.get('glucose_frequency'))   # int (1..5)
            rc = float(assessment_data.get('range_compliance', 50))           # float percent
            en = int(assessment_data.get('energy_level', 5))                  # int 1..10
            sl = int(assessment_data.get('sleep_quality', 5))                 # int 1..10

            # adherence as INTEGER (0–100). Already a % int.
            adh = int(assessment_data.get('medication_adherence', 85))        # int %
            concerns = (assessment_data.get('concerns') or "").strip()
            overall = str(assessment_data.get('overall_feeling', 7))

            if existing:
                existing.glucose_frequency = gf
                existing.range_compliance = rc
                existing.energy_level = en
                existing.sleep_quality = sl
                existing.medication_adherence = adh
                existing.concerns = concerns
                existing.overall_feeling = overall
            else:
                assessment = WeeklyAssessment(
                    user_id=user_id,
                    week_date=week_start,
                    glucose_frequency=gf,
                    range_compliance=rc,
                    energy_level=en,
                    sleep_quality=sl,
                    medication_adherence=adh,
                    concerns=concerns,
                    overall_feeling=overall
                )
                db.session.add(assessment)

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"[WeeklyAssessment SAVE ERROR] user={user_id}: {e}")
            return False

    def _freq_to_int(self, text):
        if not text:
            return 0
        return {
            "1-2 times total": 1,
            "3-4 times total": 2,
            "Once daily": 3,
            "2-3 times daily": 4,
            "4+ times daily": 5,
        }.get(text, 0)

    def get_recent_assessments(self, user_id, limit=4):
        try:
            items = (
                WeeklyAssessment.query.filter_by(user_id=user_id)
                .order_by(WeeklyAssessment.week_date.desc())
                .limit(limit)
                .all()
            )
            return [
                (a.week_date, a.glucose_frequency, a.range_compliance, a.energy_level,
                 a.sleep_quality, int(a.medication_adherence), a.concerns)
                for a in items
            ]
        except Exception as e:
            logger.exception("get_recent_assessments error: %s", e)
            return []

    def check_weekly_checkin_due(self, user_id):
        try:
            latest = (
                WeeklyAssessment.query.filter_by(user_id=user_id)
                .order_by(WeeklyAssessment.week_date.desc())
                .first()
            )
            if not latest:
                return True
            return (datetime.now().date() - latest.week_date).days >= 7
        except Exception as e:
            logger.exception("check_weekly_checkin_due error: %s", e)
            return True


# ---------------------------- Main chatbot ----------------------------
class FlaskIntegratedGlucoMate(BedrockWebCrawlerGlucoMate):
    def __init__(self, user_id=None, start_monitor=None):
        super().__init__()
        self.user_id = user_id
        self.patient_profile = None

        # background reminder loop
        self.stop_event = threading.Event()
        self.medication_thread = None
        self._monitor_started_at = None

        # state (persisted in StateStore)
        self.in_weekly_checkin = False
        self.current_checkin_index = 0
        self.checkin_data = {}
        self._last_weekly_prompt_at = None

        self.patient_db = FlaskPostgreSQLDatabase()

        if user_id:
            self.load_patient_data()
            if GLUCOMATE_ENABLE_MONITOR and (GLUCOMATE_AUTO_MONITOR_ON_REQUEST if start_monitor is None else bool(start_monitor)):
                self.start_medication_monitoring()

    # ---------------- state persistence ----------------
    def _load_state(self):
        if not self.user_id:
            self.in_weekly_checkin = False
            self.current_checkin_index = 0
            self.checkin_data = {}
            self._last_weekly_prompt_at = None
            return
        data = _STATE.get_json(self.user_id) or {}
        self.in_weekly_checkin = bool(data.get("in_weekly_checkin", False))
        self.current_checkin_index = int(data.get("current_checkin_index", 0))
        self.checkin_data = dict(data.get("checkin_data", {}))
        self._last_weekly_prompt_at = data.get("last_weekly_prompt_at")

    def _save_state(self):
        if not self.user_id:
            return
        _STATE.set_json(self.user_id, {
            "in_weekly_checkin": bool(self.in_weekly_checkin),
            "current_checkin_index": int(self.current_checkin_index or 0),
            "checkin_data": dict(self.checkin_data or {}),
            "last_weekly_prompt_at": self._last_weekly_prompt_at,
        })

    def _update_last_weekly_prompt(self):
        self._last_weekly_prompt_at = datetime.utcnow().isoformat()
        self._save_state()

    def _should_prompt_weekly(self) -> bool:
        if not (self.user_id and GLUCOMATE_ENABLE_WEEKLY_CHECKIN):
            return False
        if self.in_weekly_checkin:
            return False
        if not self.patient_db.check_weekly_checkin_due(self.user_id):
            return False
        if self._last_weekly_prompt_at:
            try:
                last = datetime.fromisoformat(self._last_weekly_prompt_at)
                if datetime.utcnow() - last < timedelta(hours=WEEKLY_PROMPT_THROTTLE_HOURS):
                    return False
            except Exception:
                pass
        return True

    # ---------------- unsent assessment queue ----------------
    def _queue_unsent_assessment(self, payload):
        if not self.user_id:
            return
        key = "unsent_assessments"
        lst = _STATE.get_json(self.user_id, suffix=key) or []
        payload = dict(payload or {})
        payload["_queued_at"] = datetime.utcnow().isoformat()
        lst.append(payload)
        _STATE.set_json(self.user_id, lst, suffix=key)

    def _flush_unsent_assessments(self):
        """Try to save any queued assessments (best-effort; quiet on failure)"""
        if not self.user_id:
            return
        key = "unsent_assessments"
        lst = _STATE.get_json(self.user_id, suffix=key) or []
        if not lst:
            return
        kept = []
        for item in lst:
            ok = self.patient_db.save_weekly_assessment(self.user_id, item)
            if not ok:
                kept.append(item)
        _STATE.set_json(self.user_id, kept, suffix=key)

    # ---------------- profile ----------------
    def load_patient_data(self):
        self.patient_profile = self.patient_db.get_patient_profile(self.user_id)
        if self.patient_profile:
            dtype = self.patient_profile.get("diabetes_type") or "diabetes"
            logger.info("Loaded profile for user_id=%s (type=%s)", self.user_id, dtype)

    # ---------------- medication reminders (safe) ----------------
    def start_medication_monitoring(self):
        if not (self.patient_profile and self.patient_profile.get("medication_reminders")):
            return
        if self.medication_thread and self.medication_thread.is_alive():
            return
        self.stop_event.clear()
        self._monitor_started_at = time.time()
        self.medication_thread = threading.Thread(
            target=self._medication_monitor, name=f"glucomate-monitor-u{self.user_id}", daemon=True
        )
        self.medication_thread.start()

    def _medication_monitor(self):
        while not self.stop_event.wait(60):
            if time.time() - (self._monitor_started_at or time.time()) > MAX_MONITOR_SECS:
                break
            try:
                reminder = self.check_medication_time()
                if reminder:
                    logger.info("Medication reminder (user_id=%s): %s", self.user_id, reminder)
            except Exception as e:
                logger.exception("Medication monitor error: %s", e)
                break

    def check_medication_time(self):
        if not (self.patient_profile and self.patient_profile.get("medication_reminders")):
            return None
        now = datetime.now().time()
        now_min = now.hour * 60 + now.minute
        gm = max(0, REMINDER_GRACE_MINUTES)
        for (med_name, _dosage, _freq, time_of_day) in self.patient_profile["medication_reminders"]:
            if not time_of_day:
                continue
            rem_min = time_of_day.hour * 60 + time_of_day.minute
            if abs(now_min - rem_min) <= gm:
                return f"Time for your {med_name}! 💊"
        return None

    def cleanup(self):
        self.stop_event.set()
        if self.medication_thread and self.medication_thread.is_alive():
            self.medication_thread.join(timeout=2)

    # ---------------- weekly check-in flow ----------------
    def start_weekly_checkin(self):
        self.in_weekly_checkin = True
        self.current_checkin_index = 0
        self.checkin_data = {}
        self._save_state()

        name = self.patient_profile.get("name", "there") if self.patient_profile else "there"
        intro = (
            f"🌟 Hi {name}! Time for your weekly diabetes check-in. "
            "I'll ask you 6 quick questions. You can say 'skip' for any question, or 'stop' to do this later."
        )
        return intro + "\n\n" + self.get_current_checkin_question()

    def get_current_checkin_question(self):
        questions = self._questions()
        if self.current_checkin_index >= len(questions):
            return None
        qd = questions[self.current_checkin_index]
        text = f"**Question {self.current_checkin_index + 1}/{len(questions)}**: {qd['question']}"
        if qd.get("options") and qd["type"] != "text":
            text += "\n\nOptions:"
            for i, opt in enumerate(qd["options"], 1):
                text += f"\n{i}. {opt}"
            text += "\n\nJust tell me the number or describe your answer!"
        return text

    def process_checkin_answer(self, user_input):
        user_input_clean = (user_input or "").strip().lower()
        if user_input_clean in {"stop", "quit", "later", "not now"}:
            self.in_weekly_checkin = False
            self._save_state()
            return "No worries! Say 'weekly check-in' anytime to resume. 😊"

        questions = self._questions()
        qd = questions[self.current_checkin_index]

        if user_input_clean == "skip":
            self.checkin_data[qd["field"]] = None
        else:
            self.checkin_data[qd["field"]] = self._process_answer_by_type(user_input, qd)

        self.current_checkin_index += 1
        self._save_state()

        if self.current_checkin_index >= len(questions):
            reply = self.complete_weekly_checkin()
            # reset state
            self.in_weekly_checkin = False
            self.current_checkin_index = 0
            self.checkin_data = {}
            self._save_state()
            return reply

        return f"Great! ({self.current_checkin_index}/{len(questions)} completed)\n\n{self.get_current_checkin_question()}"


    def complete_weekly_checkin(self):
        data = {
            "glucose_frequency": self.checkin_data.get("glucose_frequency"),
            "range_compliance": self._num(self.checkin_data.get("range_compliance"), 50),
            "energy_level": self._num(self.checkin_data.get("energy_level"), 5),
            "sleep_quality": self._num(self.checkin_data.get("sleep_quality"), 5),
          "medication_adherence": self._map_medication_adherence(self.checkin_data.get("medication_adherence")),
            "concerns": self.checkin_data.get("concerns", ""),
            "overall_feeling": 7,
        }
        ok = self.patient_db.save_weekly_assessment(self.user_id, data)
        if not ok:
            # queue and continue—don’t lose the data
            self._queue_unsent_assessment(data)
            return (
                "⚠️ I couldn't reach the database to save your check-in right now, "
                "but I saved your answers temporarily and will retry shortly. "
                "You can continue using the chat normally."
            )

        # saved → maybe flush any older unsent ones
        self._flush_unsent_assessments()

        insights = self.analyze_weekly_progress()
        name = self.patient_profile.get("name", "friend") if self.patient_profile else "friend"
        return f"🎉 Weekly check-in complete, {name}!\n\n{insights}\n\n📈 Keep up the great work!"

    def analyze_weekly_progress(self):
        items = self.patient_db.get_recent_assessments(self.user_id, 4)
        if len(items) < 2:
            return "📊 This is your first check-in—I’ll show trends starting next week."
        cur, prev = items[0], items[1]
        insights = []
        if cur[3] and prev[3]:
            if cur[3] > prev[3]:
                insights.append(f"✨ Energy improved from {prev[3]}/10 to {cur[3]}/10.")
            elif cur[3] < prev[3]:
                insights.append(f"📉 Energy dipped from {prev[3]}/10 to {cur[3]}/10.")
            else:
                insights.append(f"📊 Energy steady at {cur[3]}/10.")
        if cur[2] and prev[2]:
            if cur[2] > prev[2]:
                insights.append(f"🎯 Time-in-range improved from {prev[2]}% to {cur[2]}%.")
            elif cur[2] < prev[2]:
                insights.append(f"🔎 Time-in-range decreased from {prev[2]}% to {cur[2]}%.")
        return "\n".join(insights) or "📊 You’re maintaining steady progress."

    # ---------------- general chat ----------------
    def flask_integrated_chat(self, user_input, target_language_code="en"):
        self._load_state()
        # Best-effort: flush queued assessments
        self._flush_unsent_assessments()

        text = (user_input or "").strip()
        low = text.lower()

        # If mid check-in, route answer
        if self.in_weekly_checkin:
            return self.process_checkin_answer(text)

        # Explicit commands
        if low in {"weekly check-in", "weekly check in", "check in"}:
            return self.start_weekly_checkin()
        if low in {"yes", "y"} and GLUCOMATE_ENABLE_WEEKLY_CHECKIN:
            return self.start_weekly_checkin()
        if "progress report" in low or "how am i doing" in low:
            return self.generate_progress_report()
        if "meal plan" in low or "diet plan" in low:
            return self.generate_personalized_meal_plan(target_language_code)

        # Throttled weekly prompt
        if self._should_prompt_weekly():
            name = self.patient_profile.get("name", "there") if self.patient_profile else "there"
            self._update_last_weekly_prompt()
            return (
                f"🌟 Hi {name}! It's been a week since our last check-in.\n\n"
                "Would you like to do a quick weekly check-in? Say 'yes' to start, or ask me anything else! 😊"
            )

        # Inline medication reminder (single check; no loops)
        if GLUCOMATE_ENABLE_MONITOR:
            reminder = self.check_medication_time()
            if reminder:
                who = self.patient_profile.get("name", "there") if self.patient_profile else "there"
                return f"🔔 Hi {who}! {reminder} Now, what were you asking about?"

        # Default: medical chat (LLM) with safe fallback
        return self._safe_enhanced_medical_chat(text, target_language_code)

    # ---------------- LLM safety & fallbacks ----------------
    def _safe_enhanced_medical_chat(self, text, lang):
        """Call base LLM chat; on any exception, return a helpful offline answer."""
        try:
            return self.enhanced_medical_chat(text, lang)
        except Exception as e:
            logger.exception("enhanced_medical_chat failed: %s", e)
            return self._offline_medical_fallback(text)

    def generate_personalized_meal_plan(self, target_language_code="en"):
        if not self.patient_profile:
            return "I can personalize a plan once your health profile is set."
        p = self.patient_profile
        name = p.get("name", "friend")
        prompt = f"""
Create a highly personalized 3-day diabetes meal plan for {name}:

Patient Profile:
- Diabetes Type: {p.get('diabetes_type', 'Not specified')}
- Age: {p.get('age', 'Not specified')}
- Weight: {p.get('weight', 'Not specified')} kg
- Height: {p.get('height', 'Not specified')} cm
- Activity Level: {p.get('activity_level', 'Moderate')}
- HbA1c: {p.get('hba1c', 'Not available')}%
- Medications: {len(p.get('medications', []))} diabetes medications

Requirements:
1) Tailor to diabetes type and control
2) Match activity level/anthropometrics
3) Consider meds
4) Practical, age-appropriate
5) Include tips addressed to {name}
Format: 3 days with breakfast, lunch, dinner, 2 snacks; include carb counts and portions.
"""
        try:
            response = self.call_bedrock_model(prompt, conversation_type="medical")
            if target_language_code != "en":
                response = self.enhance_medical_translation(response, target_language_code)
            return response
        except Exception as e:
            logger.exception("meal plan LLM failed: %s", e)
            # Offline quick-start if LLM not available
            return self._offline_diet_basics()

    def _offline_medical_fallback(self, text):
        t = (text or "").lower()

        # emergency-ish keyword: low blood sugar
        if any(k in t for k in ["low blood sugar", "hypogly", "i'm dizzy", "feeling dizzy", "shaky", "sweaty"]) or re.search(r"\blow\b.*\bsugar\b", t):
            return (
                "🚑 **Possible hypoglycemia (low blood sugar). Quick steps:**\n"
                "1) If you can test, check your glucose now.\n"
                "2) If below ~70 mg/dL *or you have symptoms*: take **15g fast carbs** (e.g., 120–150 ml juice, 3–4 glucose tabs, 1 tbsp honey).\n"
                "3) Wait 15 minutes, **re-check**. If still low, repeat Step 2.\n"
                "4) Once normal and next meal is >1 hour away, eat a **small snack** with carbs + protein (e.g., crackers + cheese).\n"
                "5) If symptoms are severe, you can’t keep food down, or you’re alone and getting worse → seek medical help immediately.\n"
            )

        # definition / basics
        if "what is diabetes" in t or "whats diabetes" in t or "what's diabetes" in t or t.strip() == "diabetes":
            return (
                "**Diabetes** is a condition where the body has trouble regulating blood glucose. "
                "Either the pancreas makes little/no insulin (Type 1), or the body doesn’t use insulin well (Type 2). "
                "Gestational diabetes happens during pregnancy. Management focuses on healthy eating, activity, "
                "monitoring glucose, and—if prescribed—medications or insulin."
            )

        # diet advice
        if "diet" in t or "meal" in t or "nutrition" in t or "eat" in t:
            return self._offline_diet_basics()

        # default fallback
        return (
            "I’m having trouble reaching the medical model right now, but I can still help:\n"
            "• Tell me your question (symptoms, reading, meal idea) and I’ll give general guidance.\n"
            "• For urgent symptoms (confusion, severe dizziness, fainting), seek medical care immediately."
        )

    def _offline_diet_basics(self):
        return (
            "🍽️ **Diabetes-friendly diet quick tips**\n"
            "• Build plates with **½ non-starchy veg**, **¼ lean protein**, **¼ high-fiber carbs** (whole grains/legumes).\n"
            "• Aim ~**45–60g carbs per meal** (individualize) and **15–20g per snack**; spread carbs evenly.\n"
            "• Prefer water/unsweetened drinks; limit juices/sugary drinks.\n"
            "• Choose **whole grains**, beans, lentils; limit refined carbs and ultra-processed snacks.\n"
            "• Include healthy fats (olive oil, nuts) and proteins to slow glucose spikes.\n"
            "• Pre-meal walk (10–15 min) can improve post-meal glucose.\n"
        )

    # ---------------- utilities ----------------
    def _questions(self):
        return [
            {
                "field": "glucose_frequency",
                "question": "How often did you check your glucose this week?",
                "options": ["1-2 times total", "3-4 times total", "Once daily", "2-3 times daily", "4+ times daily"],
                "type": "choice",
            },
            {
                "field": "range_compliance",
                "question": "What percentage of your readings were in target range this week?",
                "options": ["Less than 25%", "25-50%", "50-75%", "75-90%", "90%+", "Not sure"],
                "type": "choice",
            },
            {
                "field": "energy_level",
                "question": "On a scale of 1-10, how has your energy been this week?",
                "options": ["1-2 (Much worse)", "3-4 (Worse)", "5-6 (About the same)", "7-8 (Better)", "9-10 (Much better)"],
                "type": "scale",
            },
            {
                "field": "sleep_quality",
                "question": "How has your sleep quality been this week (1-10)?",
                "options": ["1-2 (Very poor)", "3-4 (Poor)", "5-6 (Fair)", "7-8 (Good)", "9-10 (Excellent)"],
                "type": "scale",
            },
            {
                "field": "medication_adherence",
                "question": "How consistently did you take your diabetes medications this week?",
                "options": ["Less than 50%", "50-70%", "70-85%", "85-95%", "95-100%", "I don't take medications"],
                "type": "choice",
            },
            {"field": "concerns", "question": "Any concerns or symptoms you've noticed this week?", "type": "text"},
        ]

    def _process_answer_by_type(self, user_input, qd):
        text = (user_input or "").strip()
        if qd["type"] == "text":
            return text
        if qd["type"] in {"choice", "scale"}:
            try:
                n = int(text)
                if 1 <= n <= len(qd["options"]):
                    return qd["options"][n - 1]
            except Exception:
                pass
            norm = text.lower().replace("time", "times").replace("  ", " ").strip()
            for opt in qd["options"]:
                o = opt.lower().strip()
                if norm in o or o in norm:
                    return opt
            return text
        return text

    def _num(self, val, default):
        if val is None:
            return default
        try:
            nums = re.findall(r"\d+", str(val))
            return int(nums[0]) if nums else default
        except Exception:
            return default


# ---------------------------- Factory ----------------------------
def create_flask_glucomate_for_user(user_id, start_monitor=False):
    inst = _GLUCO_INSTANCES.get(user_id)
    if inst is None:
        inst = FlaskIntegratedGlucoMate(user_id=user_id, start_monitor=start_monitor)
        _GLUCO_INSTANCES[user_id] = inst
    return inst

def process_flask_chat_message(user_id, message, language="en"):
    try:
        start_monitor = GLUCOMATE_AUTO_MONITOR_ON_REQUEST
        g = create_flask_glucomate_for_user(user_id, start_monitor=start_monitor)
        return {"success": True, "response": g.flask_integrated_chat(message, language), "user_id": user_id}
    except Exception as e:
        logger.exception("process_flask_chat_message error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "response": "I'm having trouble processing your request right now. Please try again.",
        }

def cleanup_flask_glucomate(glucomate_instance):
    if glucomate_instance:
        glucomate_instance.cleanup()

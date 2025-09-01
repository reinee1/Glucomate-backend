# app/chatbot/flask_integrated_glucomate.py
"""
Flask-Integrated GlucoMate: Personalized Health Tracking
Adapts the integrated GlucoMate to work seamlessly with Flask backend
Uses existing PostgreSQL schema and JWT authentication
"""

import threading
import time
import sys
import os
from datetime import datetime, timedelta

# Add Flask app context
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.extensions import db
from app.models import User, MedicalProfile, MedicalHistory, UserMedication, Monitoring, Lifestyle, MedicalReminder, WeeklyAssessment

# Import base chatbot functionality
from clean_bedrock_web_crawler import BedrockWebCrawlerGlucoMate

class FlaskPostgreSQLDatabase:
    """Flask SQLAlchemy database adapter for GlucoMate"""
    
    def get_patient_profile(self, user_id):
        """Get complete patient profile using Flask models"""
        try:
            user = User.query.get(user_id)
            if not user:
                return None
            
            profile_data = {
                'user_id': user.id,
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email
            }
            
            # Get medical profile
            medical = MedicalProfile.query.filter_by(user_id=user_id).first()
            if medical:
                profile_data.update({
                    'date_of_birth': medical.date_of_birth,
                    'gender': medical.gender,
                    'weight': medical.weight,
                    'height': medical.height,
                    'diabetes_type': medical.diabetes_type,
                    'diagnosis_year': medical.diagnosis_year,
                    'age': self._calculate_age(medical.date_of_birth) if medical.date_of_birth else None
                })
            
            # Get monitoring info
            monitoring = Monitoring.query.filter_by(user_id=user_id).first()
            if monitoring:
                profile_data.update({
                    'glucose_frequency': monitoring.glucose_frequency,
                    'hba1c': float(monitoring.latest_hba1c_percent) if monitoring.latest_hba1c_percent else None,
                    'uses_cgm': monitoring.uses_cgm,
                    'frequent_hypoglycemia': monitoring.frequent_hypoglycemia
                })
            
            # Get lifestyle info
            lifestyle = Lifestyle.query.filter_by(user_id=user_id).first()
            if lifestyle:
                profile_data.update({
                    'smoking_status': lifestyle.smoking_status,
                    'alcohol_consumption': lifestyle.alcohol_consumption,
                    'activity_level': lifestyle.exercise_frequency
                })
            
            # Get medications
            medications = UserMedication.query.filter_by(user_id=user_id).all()
            profile_data['medications'] = [(med.medication_name, med.dosage, med.frequency) for med in medications]
            
            # Get medical reminders for medication monitoring
            reminders = MedicalReminder.query.filter_by(user_id=user_id, active=True).all()
            profile_data['medication_reminders'] = [
                (r.medication_name, r.dosage, r.frequency, r.time_of_day) for r in reminders
            ]
            
            return profile_data
            
        except Exception as e:
            print(f"Error getting patient profile: {e}")
            return None
    
    def _calculate_age(self, birth_date):
        """Calculate age from birth date"""
        if not birth_date:
            return None
        today = datetime.now().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    def save_weekly_assessment(self, user_id, assessment_data):
        """Save weekly assessment using Flask WeeklyAssessment model"""
        try:
            week_date = datetime.now().date()
            
            # Check if assessment exists for this week
            existing = WeeklyAssessment.query.filter_by(
                user_id=user_id, 
                week_date=week_date
            ).first()
            
            if existing:
                # Update existing assessment
                existing.glucose_frequency = self._convert_frequency_to_int(assessment_data.get('glucose_frequency'))
                existing.range_compliance = float(assessment_data.get('range_compliance', 50))
                existing.energy_level = int(assessment_data.get('energy_level', 5))
                existing.sleep_quality = int(assessment_data.get('sleep_quality', 5))
                existing.medication_adherence = assessment_data.get('medication_adherence', 85) >= 80
                existing.concerns = assessment_data.get('concerns', '')
                existing.overall_feeling = str(assessment_data.get('overall_feeling', 7))
            else:
                # Create new assessment
                assessment = WeeklyAssessment(
                    user_id=user_id,
                    week_date=week_date,
                    glucose_frequency=self._convert_frequency_to_int(assessment_data.get('glucose_frequency')),
                    range_compliance=float(assessment_data.get('range_compliance', 50)),
                    energy_level=int(assessment_data.get('energy_level', 5)),
                    sleep_quality=int(assessment_data.get('sleep_quality', 5)),
                    medication_adherence=assessment_data.get('medication_adherence', 85) >= 80,
                    concerns=assessment_data.get('concerns', ''),
                    overall_feeling=str(assessment_data.get('overall_feeling', 7))
                )
                db.session.add(assessment)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving weekly assessment: {e}")
            return False
    
    def _convert_frequency_to_int(self, frequency_text):
        """Convert frequency text to integer for database"""
        if not frequency_text:
            return 0
        
        frequency_map = {
            "1-2 times total": 1,
            "3-4 times total": 2, 
            "Once daily": 3,
            "2-3 times daily": 4,
            "4+ times daily": 5
        }
        
        return frequency_map.get(frequency_text, 0)
    
    def get_recent_assessments(self, user_id, limit=4):
        """Get recent weekly assessments for progress tracking"""
        try:
            assessments = WeeklyAssessment.query.filter_by(user_id=user_id)\
                .order_by(WeeklyAssessment.week_date.desc())\
                .limit(limit)\
                .all()
            
            return [(a.week_date, a.glucose_frequency, a.range_compliance, 
                    a.energy_level, a.sleep_quality, int(a.medication_adherence), a.concerns) 
                   for a in assessments]
            
        except Exception as e:
            print(f"Error getting recent assessments: {e}")
            return []
    
    def check_weekly_checkin_due(self, user_id):
        """Check if weekly check-in is due"""
        try:
            latest = WeeklyAssessment.query.filter_by(user_id=user_id)\
                .order_by(WeeklyAssessment.week_date.desc())\
                .first()
            
            if not latest:
                return True  # First time
            
            days_since = (datetime.now().date() - latest.week_date).days
            return days_since >= 7  # Weekly check-in
            
        except Exception as e:
            print(f"Error checking weekly check-in: {e}")
            return True

class FlaskIntegratedGlucoMate(BedrockWebCrawlerGlucoMate):
    """
    Flask-integrated personalized GlucoMate
    Uses Flask's existing database models and authentication
    """
    
    def __init__(self, user_id=None):
        super().__init__()  # Get all web crawler functionality
        
        # Flask-specific setup
        self.user_id = user_id
        self.patient_profile = None
        self.medication_timer = None
        self.conversation_active = False
        
        # Use Flask database adapter
        self.patient_db = FlaskPostgreSQLDatabase()
        
        # Weekly check-in configuration (same as before)
        self.in_weekly_checkin = False
        self.checkin_data = {}
        self.checkin_questions = [
            {
                "field": "glucose_frequency",
                "question": "How often did you check your glucose this week?",
                "options": ["1-2 times total", "3-4 times total", "Once daily", "2-3 times daily", "4+ times daily"],
                "type": "choice"
            },
            {
                "field": "range_compliance", 
                "question": "What percentage of your readings were in your target range this week?",
                "options": ["Less than 25%", "25-50%", "50-75%", "75-90%", "90%+", "Not sure"],
                "type": "choice"
            },
            {
                "field": "energy_level",
                "question": "On a scale of 1-10, how has your energy been this week?",
                "options": ["1-2 (Much worse)", "3-4 (Worse)", "5-6 (About the same)", "7-8 (Better)", "9-10 (Much better)"],
                "type": "scale"
            },
            {
                "field": "sleep_quality",
                "question": "How has your sleep quality been this week (1-10)?",
                "options": ["1-2 (Very poor)", "3-4 (Poor)", "5-6 (Fair)", "7-8 (Good)", "9-10 (Excellent)"],
                "type": "scale"
            },
            {
                "field": "medication_adherence",
                "question": "How consistently did you take your diabetes medications this week?",
                "options": ["Less than 50%", "50-70%", "70-85%", "85-95%", "95-100%", "I don't take medications"],
                "type": "choice"
            },
            {
                "field": "concerns",
                "question": "Any concerns or symptoms you've noticed this week?",
                "type": "text"
            }
        ]
        self.current_checkin_index = 0
        
        if user_id:
            self.load_patient_data()
            self.start_medication_monitoring()
    
    def load_patient_data(self):
        """Load patient data using Flask models"""
        if self.user_id:
            self.patient_profile = self.patient_db.get_patient_profile(self.user_id)
            if self.patient_profile:
                name = self.patient_profile.get('name', 'there')
                diabetes_type = self.patient_profile.get('diabetes_type', 'diabetes')
                print(f"👋 Welcome back, {name}! Ready to help with your {diabetes_type} management.")
    
    def start_medication_monitoring(self):
        """Start background medication reminder monitoring"""
        if self.patient_profile and self.patient_profile.get('medication_reminders'):
            self.conversation_active = True
            self.medication_timer = threading.Thread(target=self._medication_monitor, daemon=True)
            self.medication_timer.start()
    
    def _medication_monitor(self):
        """Background medication reminder checker"""
        while self.conversation_active:
            try:
                reminder = self.check_medication_time()
                if reminder:
                    print(f"\n🔔 MEDICATION REMINDER: {reminder}")
                time.sleep(60)  # Check every minute
            except Exception:
                break
    
    def check_medication_time(self):
        """Check if it's time for any medication"""
        if not self.patient_profile or not self.patient_profile.get('medication_reminders'):
            return None
        
        current_time = datetime.now().time()
        
        for reminder in self.patient_profile['medication_reminders']:
            med_name = reminder[0]
            time_of_day = reminder[3]
            
            if time_of_day:
                reminder_minutes = time_of_day.hour * 60 + time_of_day.minute
                current_minutes = current_time.hour * 60 + current_time.minute
                
                if abs(current_minutes - reminder_minutes) <= 2:
                    return f"Time for your {med_name}! 💊"
        
        return None
    
    # Weekly check-in methods (adapted from original)
    def start_weekly_checkin(self):
        """Start weekly check-in process"""
        self.in_weekly_checkin = True
        self.current_checkin_index = 0
        self.checkin_data = {}
        
        patient_name = self.patient_profile.get('name', 'there') if self.patient_profile else 'there'
        
        intro_message = f"""
        🌟 Hi {patient_name}! Time for your weekly diabetes check-in. This helps me track your progress and provide better personalized care!
        
        I'll ask you 6 quick questions about this week. You can say 'skip' for any question, or 'stop' to do this later.
        
        Let's see how you've been doing! 📊
        """
        
        first_question = self.get_current_checkin_question()
        return intro_message + "\n\n" + first_question
    
    def get_current_checkin_question(self):
        """Get current check-in question"""
        if self.current_checkin_index >= len(self.checkin_questions):
            return None
        
        question_data = self.checkin_questions[self.current_checkin_index]
        question_text = f"**Question {self.current_checkin_index + 1}/{len(self.checkin_questions)}**: {question_data['question']}"
        
        if question_data.get('options') and question_data['type'] != 'text':
            question_text += "\n\nOptions:"
            for i, option in enumerate(question_data['options'], 1):
                question_text += f"\n{i}. {option}"
            question_text += "\n\nJust tell me the number or describe your answer!"
        
        return question_text
    
    def process_checkin_answer(self, user_input):
        """Process check-in answer"""
        user_input_clean = user_input.strip().lower()
        
        # Handle stop/skip commands
        if user_input_clean in ['stop', 'quit', 'later', 'not now']:
            self.in_weekly_checkin = False
            return "No worries! I'll remind you about the weekly check-in later. You can say 'weekly check-in' anytime to start it. 😊"
        
        if user_input_clean == 'skip':
            self.checkin_data[self.checkin_questions[self.current_checkin_index]['field']] = None
        else:
            # Process the answer
            question_data = self.checkin_questions[self.current_checkin_index]
            processed_answer = self.process_answer_by_type(user_input, question_data)
            self.checkin_data[question_data['field']] = processed_answer
        
        # Move to next question
        self.current_checkin_index += 1
        
        if self.current_checkin_index >= len(self.checkin_questions):
            return self.complete_weekly_checkin()
        else:
            next_question = self.get_current_checkin_question()
            progress = f"Great! ({self.current_checkin_index}/{len(self.checkin_questions)} completed)\n\n"
            return progress + next_question
    
    def process_answer_by_type(self, user_input, question_data):
        """Process answer based on question type"""
        if question_data['type'] == 'text':
            return user_input.strip()
        
        elif question_data['type'] in ['choice', 'scale']:
            # Try to match number
            try:
                choice_num = int(user_input.strip())
                if 1 <= choice_num <= len(question_data['options']):
                    return question_data['options'][choice_num - 1]
            except:
                pass
            
            # Try to match text
            user_lower = user_input.lower()
            for option in question_data['options']:
                if user_lower in option.lower() or option.lower() in user_lower:
                    return option
            
            return user_input.strip()
    
    def complete_weekly_checkin(self):
        """Complete weekly check-in and save to Flask database"""
        self.in_weekly_checkin = False
        
        # Convert responses to database format
        processed_data = {
            'glucose_frequency': self.checkin_data.get('glucose_frequency'),
            'range_compliance': self.extract_numeric_value(self.checkin_data.get('range_compliance', ''), 50),
            'energy_level': self.extract_numeric_value(self.checkin_data.get('energy_level', ''), 5),
            'sleep_quality': self.extract_numeric_value(self.checkin_data.get('sleep_quality', ''), 5),
            'medication_adherence': self.extract_numeric_value(self.checkin_data.get('medication_adherence', ''), 85),
            'concerns': self.checkin_data.get('concerns', ''),
            'overall_feeling': 7
        }
        
        # Save using Flask database adapter
        success = self.patient_db.save_weekly_assessment(self.user_id, processed_data)
        
        if success:
            insights = self.analyze_weekly_progress()
            patient_name = self.patient_profile.get('name', 'friend') if self.patient_profile else 'friend'
            
            response = f"🎉 Weekly check-in complete, {patient_name}! Here's what I noticed:\n\n"
            response += insights
            response += "\n\n📈 Keep up the great work! I'll check in with you again next week."
            
            return response
        else:
            return "❌ Sorry, there was an issue saving your check-in data. Please try again later."
    
    def extract_numeric_value(self, text_response, default):
        """Extract numeric value from text response"""
        if not text_response:
            return default
        
        import re
        numbers = re.findall(r'\d+', str(text_response))
        if numbers:
            return int(numbers[0])
        return default
    
    def analyze_weekly_progress(self):
        """Analyze weekly progress using Flask database"""
        if not self.user_id:
            return "📊 Check-in completed! Great job staying on top of your health."
        
        assessments = self.patient_db.get_recent_assessments(self.user_id, 4)
        
        if len(assessments) < 2:
            return "📊 This is your first check-in! I'll be able to show you trends starting next week."
        
        # Compare current vs previous
        current = assessments[0]
        previous = assessments[1]
        
        insights = []
        
        # Energy level comparison (index 3)
        if current[3] and previous[3]:
            if current[3] > previous[3]:
                insights.append(f"✨ Your energy levels improved from {previous[3]}/10 to {current[3]}/10!")
            elif current[3] < previous[3]:
                insights.append(f"📉 Your energy dropped from {previous[3]}/10 to {current[3]}/10. Let's explore what might help.")
            else:
                insights.append(f"📊 Your energy levels stayed consistent at {current[3]}/10.")
        
        # Range compliance comparison (index 2)
        if current[2] and previous[2]:
            if current[2] > previous[2]:
                insights.append(f"🎯 Great progress! Your readings in target range improved from {previous[2]}% to {current[2]}%!")
            elif current[2] < previous[2]:
                insights.append(f"📈 Your target range percentage decreased from {previous[2]}% to {current[2]}%. We can work on strategies to improve this.")
        
        return '\n'.join(insights) if insights else "📊 You're maintaining steady progress! Consistency is key in diabetes management."
    
    def generate_personalized_meal_plan(self, target_language_code='en'):
        """Generate meal plan based on Flask patient profile"""
        if not self.patient_profile:
            return "I'd love to create a personalized meal plan! Let me get to know you better through our health profile system."
        
        profile = self.patient_profile
        name = profile.get('name', 'friend')
        
        meal_plan_prompt = f"""
        Create a highly personalized 3-day diabetes meal plan for {name}:
        
        Patient Profile:
        - Name: {profile.get('name', 'Patient')}
        - Diabetes Type: {profile.get('diabetes_type', 'Not specified')}
        - Age: {profile.get('age', 'Not specified')}
        - Weight: {profile.get('weight', 'Not specified')} kg
        - Height: {profile.get('height', 'Not specified')} cm
        - Activity Level: {profile.get('activity_level', 'Moderate')}
        - HbA1c: {profile.get('hba1c', 'Not available')}%
        - Medications: {len(profile.get('medications', []))} diabetes medications
        
        Create a meal plan that:
        1. Is specifically tailored to their diabetes type and current control
        2. Matches their activity level and physical profile
        3. Considers their current medication regimen
        4. Is age-appropriate and practical
        5. Includes practical tips for {name} specifically
        6. Has encouraging, personal language throughout
        
        Format: 3 days with breakfast, lunch, dinner, and 2 snacks each day.
        Include carb counts, portion sizes, and personalized tips for {name}.
        """
        
        response = self.call_bedrock_model(meal_plan_prompt, conversation_type="medical")
        
        if target_language_code != 'en':
            response = self.enhance_medical_translation(response, target_language_code)
        
        return response
    
    def flask_integrated_chat(self, user_input, target_language_code='en'):
        """
        Main chat method integrated with Flask backend
        Uses all inherited functionality plus Flask database integration
        """
        self.conversation_active = True
        
        # Handle weekly check-in process
        if self.in_weekly_checkin:
            return self.process_checkin_answer(user_input)
        
        # Check for medication reminders
        if self.patient_profile:
            med_reminder = self.check_medication_time()
            if med_reminder:
                return f"🔔 Hi {self.patient_profile.get('name', 'there')}! {med_reminder} Now, what were you asking about?"
        
        # Handle specific commands
        if "weekly check" in user_input.lower() or "check in" in user_input.lower():
            return self.start_weekly_checkin()
        
        if "progress report" in user_input.lower() or "how am i doing" in user_input.lower():
            return self.generate_progress_report()
        
        if 'meal plan' in user_input.lower() or 'diet plan' in user_input.lower():
            return self.generate_personalized_meal_plan(target_language_code)
        
        # Auto-suggest weekly check-in if due
        if self.user_id and self.patient_db.check_weekly_checkin_due(self.user_id):
            patient_name = self.patient_profile.get('name', 'there') if self.patient_profile else 'there'
            reminder = f"""
            🌟 Hi {patient_name}! It's been a week since our last check-in. 
            
            Would you like to do a quick weekly check-in? It helps me track your progress and provide better personalized care!
            
            Say 'yes' to start the check-in, or ask me anything else! 😊
            """
            return reminder
        
        # Use enhanced medical chat with personalization (inherited from parent)
        response = self.enhanced_medical_chat(user_input, target_language_code)
        
        # Add personalization if we have patient data
        if self.patient_profile and not any(word in response for word in ['emergency', 'call 911', 'hospital']):
            name = self.patient_profile.get('name')
            if name and len(response) > 100:
                personal_prompt = f"""
                Take this response and make it more personal for {name} who has {self.patient_profile.get('diabetes_type', 'diabetes')}:
                
                {response}
                
                Add personal touches like:
                - Use their name naturally (don't overuse it)
                - Reference their diabetes type when relevant
                - Make it feel like advice from a friend who knows them
                
                Keep all the medical accuracy and disclaimers. Just make it more personal and warm.
                """
                
                try:
                    personalized_response = self.call_bedrock_model(
                        personal_prompt, 
                        conversation_type="medical",
                        temperature=0.4
                    )
                    return personalized_response
                except:
                    pass
        
        return response
    
    def generate_progress_report(self):
        """Generate comprehensive progress report from Flask database"""
        if not self.user_id:
            return "Set up your health profile first to see progress insights!"
        
        assessments = self.patient_db.get_recent_assessments(self.user_id)
        assessment_count = len(assessments)
        
        if assessment_count == 0:
            return "Complete your first weekly check-in to start tracking your progress!"
        
        patient_name = self.patient_profile.get('name', 'friend') if self.patient_profile else 'friend'
        
        report = f"""
        📊 **Progress Report for {patient_name}**
        
        **Health Tracking Summary:**
        • {assessment_count} weekly check-ins completed
        • Consistent engagement with diabetes management
        • Using personalized care recommendations
        
        """
        
        if len(assessments) >= 2:
            recent = assessments[0]
            previous = assessments[1]
            
            # Energy trend
            if recent[3] and previous[3]:
                if recent[3] > previous[3]:
                    report += "📈 **Energy levels are improving - excellent progress!**\n"
                else:
                    report += "📊 **Energy levels are stable - good consistency!**\n"
            
            # Range compliance trend
            if recent[2] and previous[2]:
                if recent[2] > previous[2]:
                    report += "🎯 **Blood sugar control is improving!**\n"
        
        report += """
        **Keep up the excellent work!** 🌟
        Your commitment to tracking and managing your diabetes is making a real difference.
        """
        
        return report
    
    def cleanup(self):
        """Cleanup method for ending conversation"""
        self.conversation_active = False

# Flask Integration Functions
def create_flask_glucomate_for_user(user_id):
    """Factory function to create Flask-integrated GlucoMate instance"""
    return FlaskIntegratedGlucoMate(user_id=user_id)

def process_flask_chat_message(user_id, message, language='en'):
    """Process a single chat message for Flask API integration"""
    try:
        glucomate = create_flask_glucomate_for_user(user_id)
        response = glucomate.flask_integrated_chat(message, language)
        return {
            'success': True,
            'response': response,
            'user_id': user_id
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'response': "I'm having trouble processing your request right now. Please try again."
        }

def cleanup_flask_glucomate(glucomate_instance):
    """Cleanup function for Flask integration"""
    if glucomate_instance:
        glucomate_instance.cleanup()
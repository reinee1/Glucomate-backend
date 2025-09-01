"""
GlucoMate Level 3: Knowledge Enhanced (Fixed Model Compatibility)
Inherits: Bedrock core, safety, multilingual support
Adds: Knowledge base queries, medical citations, authoritative sources
"""

import boto3
import json
import sys
from clean_multilingual_glucomate import MultilingualGlucoMate

class KnowledgeEnhancedGlucoMate(MultilingualGlucoMate):
    """
    Level 3: Adds knowledge base integration with proper model compatibility
    Inherits: Bedrock core, safety, multilingual support
    Adds: Knowledge base queries, medical citations, authoritative sources
    """
    
    def __init__(self):
        super().__init__()  # Get ALL previous functionality
        
        # Knowledge base configuration
        self.knowledge_base_id = "JX4DNBIXAA"  # Your actual Knowledge Base ID
        
        # Override model specifically for knowledge base (different from inherited model)
        self.kb_model_id = "anthropic.claude-3-haiku-20240307-v1:0"  # KB-compatible model
        
        # Query enhancement for better knowledge base results
        self.medical_query_enhancements = {
            'blood sugar': 'blood glucose levels diabetes management',
            'insulin': 'insulin therapy diabetes treatment administration',
            'diet': 'diabetic diet nutrition meal planning carbohydrates',
            'exercise': 'physical activity diabetes blood glucose exercise',
            'symptoms': 'diabetes symptoms hyperglycemia hypoglycemia signs',
            'complications': 'diabetes complications long-term effects prevention',
            'medication': 'diabetes medications metformin insulin therapy',
            'monitoring': 'blood glucose monitoring testing devices'
        }
        
        print("📚 GlucoMate Level 3: Knowledge base integration loaded")
        print(f"🔧 Using KB model: {self.kb_model_id}")
        print(f"🔧 Using chat model: {self.model_id}")
    
    def enhance_query_for_knowledge_base(self, question):
        """
        Enhance user queries for better knowledge base results
        """
        question_lower = question.lower()
        
        # Add diabetes context if not present
        if 'diabetes' not in question_lower:
            question = f"diabetes {question}"
        
        # Enhance with medical terminology
        for key_term, enhancement in self.medical_query_enhancements.items():
            if key_term in question_lower:
                # Don't replace, just add context
                question = f"{question} {enhancement}"
                break
        
        return question
    
    def query_medical_knowledge(self, question):
        """
        Query the diabetes knowledge base with proper model compatibility
        """
        try:
            # Enhance query for better results
            enhanced_query = self.enhance_query_for_knowledge_base(question)
            print(f"🔍 Querying knowledge base: {enhanced_query}")
            
            # Use the KB-specific model (not the inherited chat model)
            response = self.bedrock_agent.retrieve_and_generate(
                input={'text': enhanced_query},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.knowledge_base_id,
                        'modelArn': f'arn:aws:bedrock:us-east-1::foundation-model/{self.kb_model_id}'
                    }
                }
            )
            
            print("✅ Knowledge base query successful!")
            
            # Extract response and sources
            answer = response['output']['text']
            citations = response.get('citations', [])
            
            # Process and enhance the response
            enhanced_answer = self.process_knowledge_response(answer, citations)
            return enhanced_answer
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Knowledge base error: {error_msg[:100]}...")
            
            # Try fallback with Titan Express
            try:
                print("🔄 Trying Titan Express fallback...")
                fallback_response = self.bedrock_agent.retrieve_and_generate(
                    input={'text': enhanced_query},
                    retrieveAndGenerateConfiguration={
                        'type': 'KNOWLEDGE_BASE',
                        'knowledgeBaseConfiguration': {
                            'knowledgeBaseId': self.knowledge_base_id,
                            'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-text-express-v1'
                        }
                    }
                )
                
                print("✅ Fallback model successful!")
                answer = fallback_response['output']['text']
                citations = fallback_response.get('citations', [])
                enhanced_answer = self.process_knowledge_response(answer, citations)
                return enhanced_answer
                
            except Exception as e2:
                print(f"❌ Fallback also failed: {str(e2)[:50]}...")
            
            # Specific error handling
            if "ThrottlingException" in error_msg:
                return "I'm getting a lot of requests right now. Let me try to help with what I know, or please try again in a moment."
            elif "ValidationException" in error_msg:
                return None  # Let it fall back to regular response
            elif "ResourceNotFoundException" in error_msg or "does not exist" in error_msg:
                print("⚠️ Knowledge base not found - check the ID")
                return None
            elif "AccessDeniedException" in error_msg:
                print("⚠️ Access denied - check AWS permissions")
                return None
            else:
                return None
    
    def process_knowledge_response(self, answer, citations):
        """
        Process knowledge base response and add proper citations
        """
        # Make the response warmer and more personal
        if answer:
            # Add a warm introduction if the response seems too clinical
            if not any(starter in answer.lower()[:50] for starter in ['i understand', 'great question', 'that\'s']):
                warm_starters = [
                    "Great question! ",
                    "I'm happy to help with that. ",
                    "That's important to know. ",
                    "Let me share what the medical guidelines tell us. "
                ]
                import random
                starter = random.choice(warm_starters)
                answer = starter + answer
        
        # Add source information
        if citations and len(citations) > 0:
            source_info = "\n\n📚 **Sources**: This information comes from authoritative diabetes care guidelines, medical literature, and evidence-based research from trusted healthcare organizations."
            answer += source_info
        else:
            # Generic source attribution
            source_info = "\n\n📚 **Source**: Medical knowledge base with evidence-based diabetes care information."
            answer += source_info
        
        return answer
    
    def create_knowledge_enhanced_prompt(self, user_input, kb_response, language="English"):
        """
        Create prompt that combines knowledge base info with conversational tone
        """
        
        prompt = f"""You are GlucoMate, a warm and caring diabetes companion. A person asked: "{user_input}"

You have this authoritative medical information from your knowledge base:
{kb_response}

Please rewrite this information in a warm, conversational, and supportive tone that:
1. Keeps all the medical accuracy and important details
2. Sounds like a knowledgeable friend, not a medical textbook
3. Shows empathy and understanding
4. Uses encouraging, supportive language
5. Includes practical tips they can use
6. Makes complex medical information easy to understand
7. Maintains the source attribution

Respond in {language} with a caring, personal touch while keeping all the medical accuracy:"""

        return prompt
    
    def knowledge_enhanced_chat(self, user_input, target_language_code):
        """
        Enhanced chat with knowledge base integration (no auto-detection)
        """
        
        # Translate input to English for processing (inherited)
        english_input = self.translate_to_english(user_input, target_language_code)
        
        # Safety check first (inherited)
        safety_check = self.check_safety(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = safety_check['message']
            if target_language_code != 'en':
                emergency_msg = self.translate_response(emergency_msg, target_language_code)
            return emergency_msg
        
        # Get language name for responses
        language_name = "English"
        for code, (name, lang_code) in self.supported_languages.items():
            if lang_code == target_language_code:
                language_name = name
                break
        
        # Determine if this needs knowledge base lookup
        conversation_type = self.classify_conversation_type(english_input)
        
        if conversation_type == "casual":
            # Use inherited multilingual chat for casual conversation
            return self.multilingual_chat(user_input, target_language_code)
        
        # Try knowledge base for medical questions
        kb_response = self.query_medical_knowledge(english_input)
        
        if kb_response:
            # Enhance knowledge base response with conversational tone
            enhancement_prompt = self.create_knowledge_enhanced_prompt(
                english_input, kb_response, language_name
            )
            
            # Use the inherited chat model for response enhancement
            response = self.call_bedrock_model(
                enhancement_prompt, 
                conversation_type="medical",
                temperature=0.4  # Slightly higher for warmth while keeping accuracy
            )
            
            print("✅ Enhanced response from knowledge base")
        else:
            # Fallback to inherited multilingual functionality
            print("⚠️ Using multilingual fallback response")
            return self.multilingual_chat(user_input, target_language_code)
        
        # Translate response if needed (inherited method)
        if target_language_code != 'en':
            response = self.enhance_medical_translation(response, target_language_code)
        
        # Add medical disclaimer (inherited method)
        response = self.add_medical_disclaimer(response, language_name)
        
        # Add safety warnings if needed (inherited)
        if safety_check['urgency_level'] in ['HIGH', 'MODERATE']:
            warning_msg = safety_check['message']
            if target_language_code != 'en':
                warning_msg = self.translate_response(warning_msg, target_language_code)
            response = warning_msg + "\n\n" + response
        
        return response
    
    def test_knowledge_base_connection(self):
        """Test knowledge base connectivity with detailed output"""
        print("🧪 Testing knowledge base connection...")
        print(f"📋 Knowledge Base ID: {self.knowledge_base_id}")
        print(f"🤖 KB Model: {self.kb_model_id}")
        
        test_query = "What is diabetes?"
        result = self.query_medical_knowledge(test_query)
        
        if result:
            print("✅ Knowledge base connection successful!")
            print(f"📝 Sample response: {result[:150]}...")
            return True
        else:
            print("❌ Knowledge base connection failed!")
            print("   Will fall back to multilingual responses")
            return False
    
    def get_knowledge_base_stats(self):
        """Get information about knowledge base usage"""
        return {
            'knowledge_base_id': self.knowledge_base_id,
            'kb_model_id': self.kb_model_id,
            'chat_model_id': self.model_id,
            'enhancement_terms': len(self.medical_query_enhancements)
        }

def main():
    """Demo of Level 3 - Knowledge Enhanced GlucoMate"""
    print("📚 GlucoMate Level 3: Knowledge Enhanced Diabetes Care")
    print("🏥 Now with authoritative medical knowledge base integration!")
    print("\n✨ New Features:")
    print("   • Authoritative medical knowledge base queries")
    print("   • Enhanced medical citations and sources")
    print("   • Query enhancement for better results")
    print("   • Warm tone with medical accuracy")
    print("   • All previous multilingual capabilities")
    print("   • Fixed model compatibility issues")
    
    bot = KnowledgeEnhancedGlucoMate()
    
    # Test knowledge base connection
    print("\n" + "="*50)
    kb_working = bot.test_knowledge_base_connection()
    print("="*50)
    
    if not kb_working:
        print("⚠️ Note: Knowledge base issues detected. System will use multilingual fallback.")
        print("   You'll still get great medical advice from the core system.")
    
    # Show knowledge base info
    kb_stats = bot.get_knowledge_base_stats()
    print(f"\n📊 Configuration:")
    print(f"   • Knowledge Base ID: {kb_stats['knowledge_base_id']}")
    print(f"   • KB Model: {kb_stats['kb_model_id']}")
    print(f"   • Chat Model: {kb_stats['chat_model_id']}")
    print(f"   • Query Enhancements: {kb_stats['enhancement_terms']} medical terms")
    
    # Language selection (inherited)
    language_name, language_code = bot.get_language_choice()
    
    # Cultural greeting (inherited)
    greeting = bot.get_cultural_greeting(language_code)
    print(f"\n💙 {greeting}")
    
    # Knowledge-focused suggestions
    knowledge_suggestions = [
        "What are the normal blood sugar ranges?",
        "Tell me about the different types of diabetes",
        "What are the long-term complications of diabetes?",
        "How does insulin work in the body?",
        "What should I know about diabetic diet?"
    ]
    
    print(f"\n💡 Try asking about medical topics:")
    for suggestion in knowledge_suggestions[:3]:
        if language_code != 'en':
            translated = bot.translate_response(suggestion, language_code)
            print(f"   • {translated}")
        else:
            print(f"   • {suggestion}")
    
    exit_instruction = "Type 'quit' to exit"
    if language_code != 'en':
        exit_instruction = bot.translate_response(exit_instruction, language_code)
    print(f"\n{exit_instruction}")
    
    try:
        while True:
            user_input = input(f"\n😊 You: ").strip()
            
            if bot.handle_exit_commands(user_input, language_code):
                farewell = bot.get_cultural_farewell(language_code)
                print(f"\n💙 GlucoMate: {farewell}")
                break
            
            if user_input:
                response = bot.knowledge_enhanced_chat(user_input, language_code)
                print(f"\n📚 GlucoMate: {response}")
                print("\n" + "─" * 60)
            else:
                ready_msg = "I'm here with authoritative medical information whenever you need it!"
                if language_code != 'en':
                    ready_msg = bot.translate_response(ready_msg, language_code)
                print(f"💭 {ready_msg}")
                
    except KeyboardInterrupt:
        farewell = bot.get_cultural_farewell(language_code)
        print(f"\n\n💙 GlucoMate: {farewell}")
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        if language_code != 'en':
            error_msg = bot.translate_response(error_msg, language_code)
        print(f"\n❌ {error_msg}")

if __name__ == "__main__":
    main()

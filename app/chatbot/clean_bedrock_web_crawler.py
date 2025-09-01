"""
GlucoMate Level 4: Bedrock Web Crawler Integration (Clean Version)
Inherits: Bedrock core, safety, multilingual, knowledge base
Adds: Enhanced knowledge base with web-crawled content
"""

import boto3
import json
import sys
from app.chatbot.fixed_knowledge_enhanced_glucomate import KnowledgeEnhancedGlucoMate

class BedrockWebCrawlerGlucoMate(KnowledgeEnhancedGlucoMate):
    """
    Level 4: Uses enhanced knowledge base with web-crawled content
    Inherits: All previous functionality
    Adds: Enhanced responses using web-crawled medical content
    """
    
    def __init__(self):
        super().__init__()  # Get ALL previous functionality
        print("🕷️ GlucoMate Level 4: Enhanced knowledge base with web-crawled content loaded")
    
    def enhanced_medical_chat(self, user_input, target_language_code):
        """
        Enhanced chat using knowledge base with web-crawled content
        """
        
        # Translate input to English for processing
        english_input = self.translate_to_english(user_input, target_language_code)
        
        # Safety check first
        safety_check = self.check_safety(english_input)
        
        if safety_check['is_emergency']:
            emergency_msg = safety_check['message']
            if target_language_code != 'en':
                emergency_msg = self.translate_response(emergency_msg, target_language_code)
            return emergency_msg
        
        # Get language name
        language_name = "English"
        for code, (name, lang_code) in self.supported_languages.items():
            if lang_code == target_language_code:
                language_name = name
                break
        
        # Classify conversation type
        conversation_type = self.classify_conversation_type(english_input)
        
        # Handle casual conversation
        if conversation_type == "casual":
            return self.multilingual_chat(user_input, target_language_code)
        
        # For medical questions, use the enhanced knowledge base
        kb_response = self.query_medical_knowledge(english_input)
        
        if kb_response:
            # Enhance KB response with conversational tone
            enhancement_prompt = self.create_knowledge_enhanced_prompt(
                english_input, kb_response, language_name
            )
            
            response = self.call_bedrock_model(
                enhancement_prompt, 
                conversation_type="medical"
            )
        else:
            # Fallback to multilingual chat
            return self.multilingual_chat(user_input, target_language_code)
        
        # Add encouragement if needed
        if any(word in english_input.lower() for word in ['scared', 'worried', 'difficult', 'hard', 'confused']):
            encouragement = "\n\n" + self.encouragement[hash(english_input) % len(self.encouragement)]
            response = response + encouragement
        
        # Translate response if needed
        if target_language_code != 'en':
            response = self.enhance_medical_translation(response, target_language_code)
        
        # Add medical disclaimer
        response = self.add_medical_disclaimer(response, language_name)
        
        # Add safety warnings if needed
        if safety_check['urgency_level'] in ['HIGH', 'MODERATE']:
            warning_msg = safety_check['message']
            if target_language_code != 'en':
                warning_msg = self.translate_response(warning_msg, target_language_code)
            response = warning_msg + "\n\n" + response
        
        # Add source attribution
        response += "\n\n🕷️ **Enhanced Sources**: This response uses my knowledge base which includes web-crawled content from authoritative medical sources for maximum accuracy."
        
        return response

def main():
    """Demo of Level 4 - Enhanced Web Crawler GlucoMate"""
    print("🕷️ GlucoMate Level 4: Enhanced Knowledge Base with Web-Crawled Content")
    print("🌐 Now with diabetes.org content for comprehensive medical information!")
    print("\n✨ Features:")
    print("   • Enhanced knowledge base with web-crawled medical content")
    print("   • Authoritative diabetes information from trusted sources")
    print("   • All previous capabilities (multilingual, safety, citations)")
    print("   • Improved medical accuracy and currency")
    
    bot = BedrockWebCrawlerGlucoMate()
    
    # Test knowledge base connection
    print("\n📚 Testing enhanced knowledge base...")
    if not bot.test_knowledge_base_connection():
        print("⚠️ Knowledge base issues detected")
    
    # Language selection
    language_name, language_code = bot.get_language_choice()
    
    # Greeting
    greeting = bot.get_cultural_greeting(language_code)
    print(f"\n💙 {greeting}")
    
    # Enhanced suggestions
    suggestions = [
        "What are the latest diabetes treatment options?",
        "Tell me about blood sugar management",
        "How can I prevent diabetes complications?",
        "What foods are good for diabetics?"
    ]
    
    print(f"\n💡 Try asking about diabetes topics:")
    for suggestion in suggestions[:3]:
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
                response = bot.enhanced_medical_chat(user_input, language_code)
                print(f"\n🕷️ GlucoMate: {response}")
                print("\n" + "─" * 60)
            else:
                ready_msg = "I'm here with enhanced medical information!"
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

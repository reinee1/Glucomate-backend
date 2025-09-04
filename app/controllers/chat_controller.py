# app/controllers/chat_controller.py
"""
Chat controller for GlucoMate integration with existing chat system
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.chatbot import flask_integrated_glucomate
from app.extensions import db
from app.models import ChatSession, ChatMessage, User
from datetime import datetime
import sys
import os

# Add chatbot directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

try:
    from flask_integrated_glucomate import FlaskIntegratedGlucoMate
    GLUCOMATE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: GlucoMate chatbot not available: {e}")
    GLUCOMATE_AVAILABLE = False

# ------------------------------------------------------------------------------
# NEW: keep a single GlucoMate instance per user so state (e.g., in_weekly_checkin)
# persists across messages.
# ------------------------------------------------------------------------------
_GLUCOMATE_SESSIONS = {}  # {user_id: FlaskIntegratedGlucoMate}

def _get_glucomate(user_id: int) -> "FlaskIntegratedGlucoMate":
    bot = _GLUCOMATE_SESSIONS.get(user_id)
    if bot is None:
        bot = FlaskIntegratedGlucoMate(user_id=user_id)
        _GLUCOMATE_SESSIONS[user_id] = bot
    return bot

def _dispose_glucomate(user_id: int):
    bot = _GLUCOMATE_SESSIONS.pop(user_id, None)
    if bot and hasattr(bot, "cleanup"):
        try:
            bot.cleanup()
        except Exception:
            pass

@jwt_required()
def send_message_to_glucomate():
    """
    Send message to GlucoMate and save conversation using existing ChatSession/ChatMessage models
    """
    try:
        # Get user ID from JWT
        identity = get_jwt_identity()
        user_id = int(identity)

        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "JSON data required"
            }), 400

        message = data.get('message', '').strip()
        language = data.get('language', 'en')
        session_id = data.get('session_id')  # Optional: continue existing session

        # Validate message
        if not message:
            return jsonify({
                "success": False,
                "message": "Message cannot be empty"
            }), 400

        if len(message) > 2000:
            return jsonify({
                "success": False,
                "message": "Message too long (max 2000 characters)"
            }), 400

        # Check if GlucoMate is available
        if not GLUCOMATE_AVAILABLE:
            return jsonify({
                "success": False,
                "message": "GlucoMate chatbot temporarily unavailable"
            }), 503

        # Get or create chat session
        if session_id:
            chat_session = ChatSession.query.filter_by(
                id=session_id,
                user_id=user_id
            ).first()
        else:
            chat_session = None

        if not chat_session:
            # Create new chat session
            chat_session = ChatSession(
                user_id=user_id,
                started_at=datetime.utcnow()
            )
            db.session.add(chat_session)
            try:
                db.session.flush()  # Get the ID
            except Exception as e:
                db.session.rollback()
                print(f"Database flush error: {e}")
                return jsonify({
                    "success": False,
                    "message": "Error creating chat session",
                    "error": str(e)
                }), 500

        # Save user message
        user_message = ChatMessage(
            chat_session_id=chat_session.id,
            sender="user",
            text=message,
            timestamp=datetime.utcnow()
        )
        db.session.add(user_message)

        # Get GlucoMate response (reuse the same bot instance for this user)
        try:
            glucomate = _get_glucomate(user_id)
            bot_response = glucomate.flask_integrated_chat(message, language)
        except Exception as e:
            print(f"GlucoMate error: {e}")
            bot_response = "I'm having trouble processing your request right now. Please try again in a moment."

        # Save bot response
        bot_message = ChatMessage(
            chat_session_id=chat_session.id,
            sender="glucomate",
            text=bot_response,
            timestamp=datetime.utcnow()
        )
        db.session.add(bot_message)

        # Commit all changes
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Database commit error: {e}")
            return jsonify({
                "success": False,
                "message": "Error saving conversation",
                "error": str(e)
            }), 500

        return jsonify({
            "success": True,
            "session_id": chat_session.id,
            "user_message": {
                "id": user_message.id,
                "text": message,
                "timestamp": user_message.timestamp.isoformat(),
                "sender": "user"
            },
            "bot_response": {
                "id": bot_message.id,
                "text": bot_response,
                "timestamp": bot_message.timestamp.isoformat(),
                "sender": "glucomate"
            }
        }), 200

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid user token"
        }), 401
    except Exception as e:
        db.session.rollback()
        print(f"Chat error: {e}")
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "error": str(e)
        }), 500

@jwt_required()
def get_chat_history(session_id=None):
    """
    Get chat history for a user
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)

        if session_id:
            # Get specific session messages
            chat_session = ChatSession.query.filter_by(
                id=session_id,
                user_id=user_id
            ).first()

            if not chat_session:
                return jsonify({
                    "success": False,
                    "message": "Chat session not found"
                }), 404

            messages = ChatMessage.query.filter_by(
                chat_session_id=session_id
            ).order_by(ChatMessage.timestamp.asc()).all()

            return jsonify({
                "success": True,
                "session": {
                    "id": chat_session.id,
                    "started_at": chat_session.started_at.isoformat(),
                    "ended_at": chat_session.ended_at.isoformat() if chat_session.ended_at else None,
                    "message_count": len(messages)
                },
                "messages": [{
                    "id": msg.id,
                    "sender": msg.sender,
                    "text": msg.text,
                    "timestamp": msg.timestamp.isoformat()
                } for msg in messages]
            }), 200

        else:
            # Get recent sessions for user
            sessions = ChatSession.query.filter_by(
                user_id=user_id
            ).order_by(ChatSession.started_at.desc()).limit(10).all()

            session_data = []
            for session in sessions:
                message_count = ChatMessage.query.filter_by(
                    chat_session_id=session.id
                ).count()

                # Get last message for preview
                last_message = ChatMessage.query.filter_by(
                    chat_session_id=session.id
                ).order_by(ChatMessage.timestamp.desc()).first()

                session_data.append({
                    "id": session.id,
                    "started_at": session.started_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "message_count": message_count,
                    "last_message": {
                        "text": last_message.text[:100] + "..." if last_message and len(last_message.text) > 100 else (last_message.text if last_message else ""),
                        "sender": last_message.sender if last_message else None,
                        "timestamp": last_message.timestamp.isoformat() if last_message else None
                    }
                })

            return jsonify({
                "success": True,
                "sessions": session_data
            }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error retrieving chat history",
            "error": str(e)
        }), 500

@jwt_required()
def end_chat_session(session_id):
    """
    End a chat session (set ended_at timestamp)
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)

        chat_session = ChatSession.query.filter_by(
            id=session_id,
            user_id=user_id
        ).first()

        if not chat_session:
            return jsonify({
                "success": False,
                "message": "Chat session not found"
            }), 404

        if chat_session.ended_at:
            return jsonify({
                "success": True,
                "message": "Session already ended"
            }), 200

        chat_session.ended_at = datetime.utcnow()
        db.session.commit()

        # Optional: dispose bot instance when user ends the session
        _dispose_glucomate(user_id)

        return jsonify({
            "success": True,
            "message": "Chat session ended",
            "session": {
                "id": chat_session.id,
                "ended_at": chat_session.ended_at.isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error ending session",
            "error": str(e)
        }), 500

@jwt_required()
def get_chat_status():
    """
    Get chat service status and user info
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)

        # Get user info
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        # Check if user has medical profile
        from app.models import MedicalProfile
        has_profile = MedicalProfile.query.filter_by(user_id=user_id).first() is not None

        return jsonify({
            "success": True,
            "message": "Chat service available",
            "user": {
                "id": user_id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "has_medical_profile": has_profile
            },
            "glucomate_available": GLUCOMATE_AVAILABLE
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Status check failed",
            "error": str(e)
        }), 500
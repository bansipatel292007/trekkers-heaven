import os
import json
from dotenv import load_dotenv
import treks_data

# Load environment variables from .env file
load_dotenv()

# Initialize Google GenAI client if API key is provided
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

genai_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        from google.genai import types
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ Google Gemini API Client successfully initialized.")
    except Exception as e:
        print(f"⚠️ Failed to initialize Google GenAI Client: {e}")
        genai_client = None

# Build System Prompt with full repository trek knowledge
def get_system_prompt():
    treks_summary = []
    for t in treks_data.TREKS_DATA:
        treks_summary.append(
            f"- {t.get('name')}: Region={t.get('region')}, Country={t.get('country')}, "
            f"Max Altitude={t.get('max_altitude_text')}, Duration={t.get('duration_text')}, "
            f"Distance={t.get('distance_text')}, Difficulty={t.get('difficulty')} ({t.get('fitness_level')}), "
            f"Best Season={t.get('best_season')}, Price={t.get('price')}, "
            f"Highlights={', '.join(t.get('highlights', [])[:3])}"
        )
    treks_context = "\n".join(treks_summary)

    return f"""You are 'Sherpa AI', the official AI Mountain Guide and Expedition Strategist on 'Trekkers Heaven' (a premium Himalayan & Global trekking platform).

Your Persona & Mission:
- Friendly, adventurous, highly knowledgeable, and safety-focused.
- You provide clear, concise, and structured advice for trekking expeditions across the Himalayas (Uttarakhand, Himachal Pradesh, Jammu & Kashmir, Ladakh, Nepal) and International ranges (European Alps).
- You recommend ideal trails based on the user's fitness, experience level, preferred month/season, budget, and altitude comfort.
- You actively provide altitude sickness (AMS) safety precautions and smart packing checklist guidance.

Website Trek Catalog Knowledge:
{treks_context}

Guidelines:
1. Always use clean GitHub-flavored Markdown (bolding, bullet points, emoji headings).
2. For trek recommendations or comparisons, highlight: Max Altitude, Duration, Difficulty, Best Months, and Key Highlights.
3. Keep responses engaging, structured, and easy to read on mobile and desktop screens.
4. If asked about safety or AMS, emphasize the golden rule: Never ascend with symptoms, hydrate with 4-5L water daily, and ascend gradually.
5. If the user asks in Hindi or Hinglish, reply warmly in natural Hinglish/Hindi or English as appropriate.
"""

def generate_chat_response(user_message: str, history: list = None) -> dict:
    """
    Generates a response using Google Gemini API (gemini-2.5-flash) with multi-turn conversation memory.
    Falls back to the local Trek Knowledge Engine if Gemini API key is missing or an error occurs.
    """
    global genai_client
    if not genai_client and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        try:
            from google import genai
            api_k = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            genai_client = genai.Client(api_key=api_k)
        except Exception as err:
            print(f"Error re-initializing GenAI client: {err}")
            genai_client = None

    if genai_client:
        try:
            from google.genai import types
            
            # Format multi-turn conversation history for Gemini API
            contents = []
            if history and isinstance(history, list):
                for turn in history[-8:]:  # keep last 8 messages for context
                    role = "user"
                    text = ""
                    if isinstance(turn, dict):
                        if turn.get("role") in ["user", "model"]:
                            role = turn.get("role")
                            text = turn.get("text") or turn.get("content") or ""
                        elif turn.get("sender") == "user":
                            role = "user"
                            text = turn.get("text", "")
                        elif turn.get("sender") in ["bot", "assistant"]:
                            role = "model"
                            text = turn.get("text", "")
                    
                    if text.strip():
                        contents.append(types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=text.strip())]
                        ))
            
            # Add current user message
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message.strip())]
            ))

            # Configure model request with system prompt
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            config = types.GenerateContentConfig(
                system_instruction=get_system_prompt(),
                temperature=0.7,
                max_output_tokens=1024,
            )

            response = genai_client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )

            reply_text = response.text or "I am ready to help you explore the summits! What trail would you like to discover?"
            
            # Generate contextual quick suggestion pills
            suggestions = generate_smart_suggestions(user_message, reply_text)

            return {
                "success": True,
                "source": "gemini-api",
                "model": model_name,
                "reply": reply_text,
                "suggestions": suggestions
            }

        except Exception as e:
            print(f"⚠️ Gemini API execution error: {e}. Falling back to local intelligence engine.")
            # Fall back to local rules engine below

    # Fallback to local trek intelligence engine
    return local_trek_engine_fallback(user_message)

def generate_smart_suggestions(query: str, reply: str) -> list:
    """Generate dynamic follow-up suggestion chips."""
    q_lower = query.lower()
    if "compare" in q_lower:
        return ["Show day-wise itinerary", "What gear to pack?", "Best season to visit"]
    elif "beginner" in q_lower or "easy" in q_lower:
        return ["Kedarkantha Trek details", "Brahmatal Trek details", "Packing essentials checklist"]
    elif "ams" in q_lower or "altitude" in q_lower:
        return ["AMS Prevention rules", "High-altitude medical kit", "Beginner friendly treks"]
    elif "winter" in q_lower or "snow" in q_lower:
        return ["Top winter snow treks", "Winter clothing guide", "Treks under ₹10,000"]
    else:
        return ["Compare Kedarkantha vs Brahmatal", "Best beginner treks under ₹10k", "AMS Safety tips", "View Trek Essentials Checklist"]

def local_trek_engine_fallback(msg: str) -> dict:
    """Local rule-based fallback when Gemini API key is not present or network fails."""
    msg_lower = msg.lower().strip()

    # Search for specific treks
    matched_treks = []
    for t in treks_data.TREKS_DATA:
        clean_name = t['name'].lower().replace(' trek', '').replace(' pass', '').strip()
        if clean_name in msg_lower or t['id'] in msg_lower or t['name'].lower() in msg_lower:
            matched_treks.append(t)

    if len(matched_treks) == 1:
        t = matched_treks[0]
        highlights = "\n • " + "\n • ".join(t.get('highlights', [])[:4])
        reply = (
            f"🏔️ **{t['name']}** ({t.get('region')}, {t.get('country')})\n\n"
            f"✨ *{t.get('tagline')}*\n\n"
            f"• **Max Altitude:** {t.get('max_altitude_text')}\n"
            f"• **Duration:** {t.get('duration_text')} ({t.get('distance_text')})\n"
            f"• **Difficulty:** {t.get('difficulty')} ({t.get('fitness_level')})\n"
            f"• **Best Season:** {t.get('best_season')}\n"
            f"• **Price:** {t.get('price')} (Rating: ⭐ {t.get('rating')})\n\n"
            f"📌 **Key Highlights:**{highlights}\n\n"
            f"💡 *{t.get('description')}*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "trek_id": t['id'],
            "trek_name": t['name'],
            "suggestions": [f"Compare {t['name']} vs Brahmatal", "Packing checklist for this trek", "AMS Safety tips"]
        }

    if "ams" in msg_lower or "altitude" in msg_lower or "sickness" in msg_lower:
        reply = (
            "⚠️ **Acute Mountain Sickness (AMS) Prevention Rules:**\n\n"
            "1. 💧 **Hydration:** Drink 4 to 5 liters of water daily with electrolytes.\n"
            "2. 🧗 **Gradual Ascent:** Never increase sleeping altitude by more than 1,000–1,500 ft/day above 9,000 ft.\n"
            "3. 🏔️ **Climb High, Sleep Low:** Do evening acclimatization walks.\n"
            "4. 🚫 **Avoid Alcohol & Smoking:** Both hinder oxygen absorption.\n"
            "5. 🛑 **Golden Rule:** If experiencing persistent headache or nausea, inform your trek leader and never ascend."
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Essential gear list", "Beginner friendly treks", "Treks under ₹10,000"]
        }

    if any(w in msg_lower for w in ['hello', 'hi', 'hey', 'namaste']):
        return {
            "success": True,
            "source": "local-fallback",
            "reply": "Namaste! 🏔️ Welcome to **Trekkers Heaven**. I'm **Sherpa AI**, powered by Google Gemini. I can help you choose summits, check gear essentials, plan budgets, or prepare for high-altitude conditions. What expedition are you planning?",
            "suggestions": ["Best beginner treks under ₹10k", "Top winter snow treks", "How to prevent AMS?", "Compare Kedarkantha vs Brahmatal"]
        }

    return {
        "success": True,
        "source": "local-fallback",
        "reply": (
            "I'm **Sherpa AI**, your personal Himalayan Trekking Assistant. I can guide you through our **30+ iconic summits**, compare trails, prepare your packing list, or answer safety questions. How can I assist your expedition today?"
        ),
        "suggestions": ["Compare Kedarkantha vs Brahmatal", "Top beginner treks", "AMS safety guide", "Treks under ₹10,000"]
    }

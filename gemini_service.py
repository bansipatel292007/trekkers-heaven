import os
import re
import json
from dotenv import load_dotenv
import treks_data

# Load environment variables (.env)
load_dotenv()

# Initialize Google GenAI client if API key is provided
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

genai_client = None

def get_genai_client():
    global genai_client
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    if genai_client is None:
        try:
            from google import genai
            genai_client = genai.Client(api_key=api_key)
            print("✅ Google Gemini API Client successfully initialized.")
        except Exception as e:
            print(f"⚠️ Failed to initialize Google GenAI Client: {e}")
            genai_client = None
    return genai_client

# Build System Prompt with full repository trek knowledge
def get_system_prompt():
    treks_summary = []
    for t in treks_data.TREKS_DATA:
        treks_summary.append(
            f"- {t.get('name')} (ID: {t.get('id')}): Region={t.get('region')}, Country={t.get('country')}, "
            f"Max Altitude={t.get('max_altitude_text')}, Duration={t.get('duration_text')}, "
            f"Distance={t.get('distance_text')}, Difficulty={t.get('difficulty')} ({t.get('fitness_level')}), "
            f"Best Season={t.get('best_season')}, Price={t.get('price')}, Rating={t.get('rating')}, "
            f"Highlights={', '.join(t.get('highlights', [])[:3])}"
        )
    treks_context = "\n".join(treks_summary)

    return f"""You are 'Sherpa AI', the elite AI High-Altitude Mountain Guide and Expedition Strategist on 'Trekkers Heaven' (a premier Himalayan & Global trekking platform).

Your Persona & Mission:
- Friendly, adventurous, safety-focused, and deeply knowledgeable about mountain trails.
- You provide concise, actionable, and structured guidance for expeditions in the Himalayas (Uttarakhand, Himachal Pradesh, Jammu & Kashmir, Ladakh, Sikkim, Nepal) and International ranges (European Alps: Switzerland, France, Italy).
- You recommend ideal trails based on the user's fitness, experience level, preferred month/season, budget, and altitude comfort.
- You actively provide altitude sickness (AMS) safety precautions and 3-layer packing checklist guidance.

Website Trek Catalog:
{treks_context}

Formatting & Tone Rules:
1. Always format responses using clean GitHub-flavored Markdown (bolding, bullet points, emoji headings).
2. For trek comparisons, contrast: Altitude, Duration, Difficulty, Best Season, Estimated Cost, and Scenic Highlights.
3. If asked about safety or AMS, emphasize the golden rule: Never ascend with symptoms, hydrate with 4-5L water daily, climb high sleep low, and take gradual ascents.
4. Keep answers concise, engaging, and mobile-friendly.
5. If the user asks in Hindi or Hinglish, reply warmly in natural Hinglish/Hindi or English as appropriate.
"""

def generate_chat_response(user_message: str, history: list = None) -> dict:
    """
    Generates a response using Google Gemini API with multi-turn conversation memory.
    Falls back gracefully to the local Trek Intelligence Engine if API key is missing or an error occurs.
    """
    client = get_genai_client()

    if client:
        # Try multiple Gemini models in order of priority
        candidate_models = [
            os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_name in candidate_models:
            try:
                from google.genai import types
                
                # Format multi-turn conversation history for Gemini API
                contents = []
                if history and isinstance(history, list):
                    for turn in history[-6:]:  # keep last 6 turns for context
                        role = "user"
                        text = ""
                        if isinstance(turn, dict):
                            if turn.get("role") in ["user", "model"]:
                                role = turn.get("role")
                                text = turn.get("text") or turn.get("content") or ""
                            elif turn.get("sender") == "user":
                                role = "user"
                                text = turn.get("text", "")
                            elif turn.get("sender") in ["bot", "assistant", "model"]:
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

                config = types.GenerateContentConfig(
                    system_instruction=get_system_prompt(),
                    temperature=0.7,
                    max_output_tokens=1024,
                )

                response = client.models.generate_content(
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
                print(f"⚠️ Gemini model '{model_name}' execution error: {e}")
                continue

    # Fallback to local trek intelligence engine
    return local_trek_engine_fallback(user_message)

def generate_smart_suggestions(query: str, reply: str) -> list:
    """Generate dynamic follow-up suggestion chips."""
    q_lower = query.lower()
    if "compare" in q_lower or " vs " in q_lower:
        return ["Show day-wise itinerary", "What gear should I pack?", "Best season to visit"]
    elif "beginner" in q_lower or "easy" in q_lower:
        return ["Kedarkantha Trek details", "Brahmatal Trek details", "Beginner packing checklist"]
    elif "ams" in q_lower or "altitude" in q_lower or "sickness" in q_lower:
        return ["AMS Prevention guide", "High-altitude medical kit", "Beginner friendly treks"]
    elif "winter" in q_lower or "snow" in q_lower:
        return ["Top winter snow treks", "Winter clothing guide", "Treks under ₹10,000"]
    elif "budget" in q_lower or "price" in q_lower or "cost" in q_lower or "10000" in q_lower:
        return ["Treks under ₹10,000", "Kedarkantha Trek", "Brahmatal Trek"]
    else:
        return ["Compare Kedarkantha vs Brahmatal", "Best beginner treks under ₹10k", "AMS Safety tips", "View Trek Essentials Checklist"]

def find_matched_treks(msg_lower: str):
    """Find matching treks from the catalog based on user query."""
    matched = []
    
    # Aliases
    alias_dict = {
        'ebc': 'everest-base-camp',
        'kgl': 'kashmir-great-lakes',
        'tmb': 'tour-du-mont-blanc',
        'kk': 'kedarkantha-summit',
        'kedar': 'kedarkantha-summit',
        'brahma': 'brahmatal-winter',
        'hampta': 'hampta-pass-crossover',
        'har ki dun': 'har-ki-dun-cradle',
        'roopkund': 'roopkund-mystery-lake',
        'kuari': 'kuari-pass-curzon',
        'chadar': 'chadar-frozen-river',
        'pin parvati': 'pin-parvati-pass',
        'rupin': 'rupin-pass-crossover',
        'bali pass': 'bali-pass-crossover',
        'valley of flowers': 'valley-of-flowers-hemkund',
        'vof': 'valley-of-flowers-hemkund',
        'annapurna': 'annapurna-circuit',
        'manaslu': 'manaslu-circuit',
        'langtang': 'langtang-valley',
        'gokyo': 'gokyo-ri-lakes',
        'island peak': 'island-peak-climb',
        'markha': 'markha-valley-ladakh',
        'tarsar': 'tarsar-marsar-lakes',
        'bhrigu': 'bhrigu-lake',
        'beas kund': 'beas-kund',
        'sandakphu': 'sandakphu-phalut',
        'goechala': 'goechala-pass-kanchenjunga',
        'dzongri': 'dzongri-viewpoint',
        'matterhorn': 'matterhorn-glacier-trail',
        'dolomites': 'dolomites-alta-via-1',
        'walker': 'walkers-haute-route',
        'mont blanc': 'tour-du-mont-blanc'
    }

    for alias, trek_id in alias_dict.items():
        if alias in msg_lower:
            t = next((item for item in treks_data.TREKS_DATA if item['id'] == trek_id), None)
            if t and t not in matched:
                matched.append(t)

    for t in treks_data.TREKS_DATA:
        t_id = t['id'].lower()
        t_name = t['name'].lower()
        clean_name = t_name.replace(' trek', '').replace(' pass', '').replace(' circuit', '').strip()
        
        if t_id in msg_lower or t_name in msg_lower:
            if t not in matched:
                matched.append(t)
        elif len(clean_name) >= 4 and clean_name in msg_lower:
            if t not in matched:
                matched.append(t)
        elif t_id.replace('-', ' ') in msg_lower:
            if t not in matched:
                matched.append(t)
                
    return matched

def local_trek_engine_fallback(msg: str) -> dict:
    """Rich rule-based fallback engine when Gemini API key is missing or offline."""
    msg_lower = msg.lower().strip()
    matched_treks = find_matched_treks(msg_lower)
    is_compare = any(k in msg_lower for k in ['compare', 'vs', 'versus', 'difference', 'better', 'which one', 'antar', 'tulna', 'dono', 'kon sa'])

    # 1. Comparison between 2 treks
    if len(matched_treks) >= 2 or (is_compare and len(matched_treks) >= 2):
        t1, t2 = matched_treks[0], matched_treks[1]
        reply = (
            f"⚖️ **Trek Comparison: {t1['name']} vs {t2['name']}**\n\n"
            f"🏔️ **1. Altitude & Difficulty:**\n"
            f"• **{t1['name']}:** {t1['max_altitude_text']} | {t1['difficulty']} ({t1['fitness_level']})\n"
            f"• **{t2['name']}:** {t2['max_altitude_text']} | {t2['difficulty']} ({t2['fitness_level']})\n\n"
            f"⏳ **2. Duration & Distance:**\n"
            f"• **{t1['name']}:** {t1['duration_text']} ({t1['distance_text']})\n"
            f"• **{t2['name']}:** {t2['duration_text']} ({t2['distance_text']})\n\n"
            f"🗓️ **3. Best Season:**\n"
            f"• **{t1['name']}:** {t1['best_season']}\n"
            f"• **{t2['name']}:** {t2['best_season']}\n\n"
            f"💰 **4. Pricing & Rating:**\n"
            f"• **{t1['name']}:** {t1['price']} (⭐ {t1['rating']})\n"
            f"• **{t2['name']}:** {t2['price']} (⭐ {t2['rating']})\n\n"
            f"🌟 **5. Highlights Comparison:**\n"
            f"• **{t1['name']}:** {', '.join(t1['highlights'][:3])}\n"
            f"• **{t2['name']}:** {', '.join(t2['highlights'][:3])}\n\n"
            f"🎯 **Sherpa Recommendation:**\n"
            f"• Choose **{t1['name']}** for: *{t1['tagline']}*.\n"
            f"• Choose **{t2['name']}** for: *{t2['tagline']}*."
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "compare_treks": [{'id': t1['id'], 'name': t1['name']}, {'id': t2['id'], 'name': t2['name']}],
            "suggestions": [f"Show itinerary for {t1['name']}", f"Show itinerary for {t2['name']}", "Compare other treks"]
        }

    # 2. General comparison intent
    if is_compare:
        return {
            "success": True,
            "source": "local-fallback",
            "reply": (
                "⚖️ **Trek Comparison Feature:**\n\n"
                "I can compare any 2 Himalayan or global treks side-by-side on **altitude, difficulty, duration, cost, best season, and scenic highlights**!\n\n"
                "**Popular Comparisons to Try:**\n"
                "• *Kedarkantha vs Brahmatal* (Winter Summits)\n"
                "• *Hampta Pass vs Kashmir Great Lakes* (Green Valleys vs Alpine Lakes)\n"
                "• *Rupin Pass vs Bali Pass* (High-Altitude Crossovers)\n"
                "• *Everest Base Camp vs Annapurna Circuit* (Nepal Classics)"
            ),
            "suggestions": ["Compare Kedarkantha vs Brahmatal", "Compare Hampta Pass vs Kashmir Great Lakes", "Compare Rupin Pass vs Bali Pass", "Compare EBC vs Annapurna Circuit"]
        }

    # 3. Single Specific Trek Details
    if len(matched_treks) == 1:
        t = matched_treks[0]
        t_clean_name = t['name'].replace(' Trek', '').replace(' Pass', '').strip()
        highlights_list = "\n • " + "\n • ".join(t.get('highlights', [])[:4])
        reply = (
            f"🏔️ **{t['name']}** ({t.get('region')}, {t.get('country')})\n\n"
            f"✨ *{t.get('tagline')}*\n\n"
            f"• **Max Altitude:** {t.get('max_altitude_text')}\n"
            f"• **Duration:** {t.get('duration_text')} ({t.get('distance_text')})\n"
            f"• **Difficulty:** {t.get('difficulty')} ({t.get('fitness_level')})\n"
            f"• **Best Season:** {t.get('best_season')}\n"
            f"• **Price:** {t.get('price')} (Rating: ⭐ {t.get('rating')})\n\n"
            f"📌 **Key Highlights:**{highlights_list}\n\n"
            f"💡 *{t.get('description')}*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "trek_id": t['id'],
            "trek_name": t['name'],
            "suggestions": [f"Show itinerary for {t_clean_name}", f"Compare {t['name']} vs Brahmatal", "Packing list for this trek"]
        }

    # 4. Greetings
    if any(w in msg_lower for w in ['hello', 'hi', 'hey', 'namaste', 'kem cho', 'salaam', 'yo', 'sup']):
        return {
            "success": True,
            "source": "local-fallback",
            "reply": "Namaste! 🏔️ Welcome to **Trekkers Heaven**. I'm **Sherpa AI**, your personal AI trek guide. I can help you choose the best trail, prepare your gear, plan your budget, or give safety tips. What would you like to explore today?",
            "suggestions": ["Best beginner treks under ₹10k", "Top winter snow treks", "How to prevent AMS?", "Compare Kedarkantha vs Brahmatal"]
        }

    # 5. Altitude Sickness / AMS
    if any(w in msg_lower for w in ['ams', 'altitude', 'sickness', 'headache', 'diamox', 'acclimatization', 'oxygen', 'high altitude']):
        reply = (
            "⚠️ **Acute Mountain Sickness (AMS) Prevention Guide:**\n\n"
            "1. 💧 **Hydration is Key:** Drink 4 to 5 liters of water daily with ORS/electrolytes.\n"
            "2. 🧗 **Ascend Gradually:** Do not increase your sleeping altitude by more than 1,000–1,500 ft/day above 9,000 ft.\n"
            "3. 🏔️ **Climb High, Sleep Low:** Go for evening acclimatization walks, then rest at camp.\n"
            "4. 🚫 **Avoid Alcohol & Smoking:** Both hinder oxygen absorption and cause dehydration.\n"
            "5. 💊 **Diamox (Acetazolamide):** Consult a doctor before taking 125mg–250mg twice daily preventive dosage.\n"
            "6. 🛑 **Golden Rule:** Never ascend with symptoms of headache, nausea, or dizziness. Inform your leader immediately."
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Essential gear list", "Easy beginner treks", "High mountain pass treks"]
        }

    # 6. Packing / Gear / Essentials
    if any(w in msg_lower for w in ['pack', 'gear', 'shoe', 'jacket', 'backpack', 'checklist', 'clothes', 'rucksack', 'layer', 'saman']):
        reply = (
            "🎒 **Trek Packing Essentials:**\n\n"
            "• **Footwear:** Waterproof high-ankle trekking shoes with deep vibram lugs + 4-5 pairs of synthetic/wool socks.\n"
            "• **3-Layer Clothing Rule:**\n"
            "   1. *Base Layer:* Moisture-wicking thermal top & bottom (avoid cotton!).\n"
            "   2. *Mid Layer:* Warm fleece or synthetic sweater.\n"
            "   3. *Outer Layer:* Windproof/waterproof down jacket (-10°C rated) + rain poncho.\n"
            "• **Gear:** 50–60L rucksack with rain cover, UV sunglasses (Cat 3/4), headlamp with extra batteries, trekking poles.\n"
            "• **Medical & Toiletries:** Sunscreen (SPF 50+), lip balm with SPF, personal medical kit (Diamox, Paracetamol, Band-aids, ORS).\n\n"
            "💡 *Tip: Check out the **Trek Essentials Checklist** button next to me in the navbar to track your items!*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Best winter snow treks", "Treks under ₹10,000", "Physical fitness routine"]
        }

    # 7. Beginner / Easy Treks
    if any(w in msg_lower for w in ['beginner', 'easy', 'first time', 'starter', 'novice', 'newbie', 'pehla', 'simple']):
        easy_treks = [t for t in treks_data.TREKS_DATA if t.get('difficulty_slug') == 'easy']
        lines = [f"• **{t['name']}** ({t['region']}) - {t['max_altitude_text']} | {t['duration_text']} | {t['price']}" for t in easy_treks[:5]]
        reply = (
            "🌟 **Top Recommended Beginner Treks:**\n\n"
            + "\n".join(lines) +
            "\n\n💡 *These treks feature gradual ascents, well-defined forest trails, and comfortable campsites with breathtaking Himalayan views!*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Tell me about Kedarkantha", "Tell me about Brahmatal", "Packing list for beginners"]
        }

    # 8. Budget / Price queries
    if any(w in msg_lower for w in ['budget', 'cheap', 'price', 'cost', 'under 10000', 'under 10k', '10,000', 'inexpensive', 'affordable', 'low cost']):
        budget_treks = [t for t in treks_data.TREKS_DATA if int(re.sub(r'[^\d]', '', t.get('price', '0')) or 0) <= 12000]
        lines = [f"• **{t['name']}** - **{t['price']}** ({t['duration_text']} in {t['region']})" for t in budget_treks[:5]]
        reply = (
            "💰 **Best Budget Himalayan Treks Under ₹12,000:**\n\n"
            + "\n".join(lines) +
            "\n\n💡 *All include guide fees, forest permits, camping tents, and high-altitude meals!*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Tell me about Bhrigu Lake", "Tell me about Kedarkantha", "Tell me about Har Ki Dun"]
        }

    # 9. Winter / Snow Treks
    if any(w in msg_lower for w in ['winter', 'snow', 'barf', 'december', 'january', 'february', 'thand', 'frozen', 'ice']):
        winter_treks = [t for t in treks_data.TREKS_DATA if any(m in ['December', 'January', 'February'] for m in t.get('best_months', []))]
        lines = [f"• **{t['name']}** ({t['region']}) - {t['max_altitude_text']} | {t['price']}" for t in winter_treks[:5]]
        reply = (
            "❄️ **Spectacular Winter Snow Treks:**\n\n"
            + "\n".join(lines) +
            "\n\n💡 *Expect deep snow, frozen alpine lakes (like Juda Ka Talab & Brahmatal), and crystalline summit views!*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Tell me about Chadar Trek", "Tell me about Kedarkantha", "Winter packing essentials"]
        }

    # 10. Regional Searches
    for reg in ['uttarakhand', 'himachal', 'kashmir', 'ladakh', 'sikkim', 'nepal', 'peru', 'switzerland', 'france', 'italy']:
        if reg in msg_lower:
            reg_treks = [t for t in treks_data.TREKS_DATA if reg in t.get('region', '').lower() or reg in t.get('country', '').lower()]
            if reg_treks:
                lines = [f"• **{t['name']}** - {t['max_altitude_text']} | {t['price']} ({t['difficulty']})" for t in reg_treks[:5]]
                reply = (
                    f"🗺️ **Treks in {reg.capitalize()}:**\n\n"
                    + "\n".join(lines) +
                    f"\n\nWhich of these would you like to know more about?"
                )
                return {
                    "success": True,
                    "source": "local-fallback",
                    "reply": reply,
                    "suggestions": [f"Tell me about {reg_treks[0]['name']}", "Best season for this region", "Packing checklist"]
                }

    # 11. Default friendly response
    return {
        "success": True,
        "source": "local-fallback",
        "reply": (
            "I'm here to help you plan your next mountain adventure on **Trekkers Heaven**!\n\n"
            "You can ask me questions like:\n"
            "• *'Tell me about Kedarkantha or Rupin Pass'*\n"
            "• *'What are the best winter snow treks?'*\n"
            "• *'How to prevent AMS (altitude sickness)?'*\n"
            "• *'Which treks are under ₹10,000?'*\n"
            "• *'What gear should I pack?'*"
        ),
        "suggestions": ["Compare Kedarkantha vs Brahmatal", "Best beginner treks under ₹10k", "Top winter snow treks", "How to prevent AMS?"]
    }

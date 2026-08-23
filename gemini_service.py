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

# Curated Trek Permits Database
PERMITS_DATA = {
    "kedarkantha": {
        "trek_name": "Kedarkantha Trek",
        "region": "Uttarakhand, India",
        "permits_required": [
            "Uttarakhand Forest Department Entry Permit (Sankri Range)",
            "Govind Pashu Vihar National Park & Sanctuary Entry Permit",
            "Local Eco-Development Committee (EDC) Environmental Fee"
        ],
        "documents_needed": [
            "Original Government Photo ID (Aadhar Card / Passport / Voter ID) + 2 photocopies",
            "Medical Fitness Certificate signed by an MBBS doctor (within 30 days)",
            "Trekker Disclaimer & Indemnity Undertaking Form"
        ],
        "fee_details": "Approx. ₹150–₹250 per day (Forest & Sanctuary fees)",
        "issuing_office": "Sankri Forest Checkpost Gate, Mori Block, Uttarkashi, Uttarakhand"
    },
    "everest-base-camp": {
        "trek_name": "Everest Base Camp (EBC)",
        "region": "Khumbu, Nepal",
        "permits_required": [
            "Sagarmatha National Park Entry Permit (NPR 3,000 / ~₹1,900)",
            "Khumbu Pasang Lhamu Rural Municipality Permit (NPR 2,000 / ~₹1,250)",
            "TIMS (Trekkers' Information Management System) Card"
        ],
        "documents_needed": [
            "Valid Passport with Nepal Tourist Visa",
            "4 Passport-sized Photographs",
            "High-Altitude Travel & Emergency Evacuation Insurance (up to 6,000m)"
        ],
        "fee_details": "Total approx. NPR 5,000–7,000 (~₹3,200–₹4,500)",
        "issuing_office": "Nepal Tourism Board (Kathmandu) or Monjo Checkpost at Sagarmatha National Park Gate"
    },
    "kashmir-great-lakes": {
        "trek_name": "Kashmir Great Lakes Trek (KGL)",
        "region": "Jammu & Kashmir, India",
        "permits_required": [
            "Indian Army Checkpost Security Clearance (Sonamarg Base & Naranag Checkposts)",
            "Jammu & Kashmir Wildlife Protection Department Entry Permit",
            "Sind Forest Division Environmental Clearance"
        ],
        "documents_needed": [
            "Original Government Photo ID (Aadhar Card / Passport) + 4 photocopies",
            "Medical Fitness Certificate with Blood Pressure & SpO2 reading",
            "Police Verification / Trekker Registry Form (Foreign nationals require prior MHA approval)"
        ],
        "fee_details": "Approx. ₹500–₹800 (Wildlife & Forest department entry fee)",
        "issuing_office": "Sonamarg Army Base Post & Tourist Reception Centre (TRC) Srinagar / Sonamarg Forest Range"
    },
    "hampta-pass": {
        "trek_name": "Hampta Pass Trek",
        "region": "Himachal Pradesh, India",
        "permits_required": [
            "Himachal Pradesh Forest Department Transit Permit (Kullu/Manali Division)",
            "Green Tax & Rohtang/Atal Tunnel Transit Clearance (Prini Checkpost)"
        ],
        "documents_needed": [
            "Government Photo ID Proof (Aadhar / Passport / Driving License)",
            "Medical Fitness Certificate",
            "Trekker Indemnity Undertaking"
        ],
        "fee_details": "Approx. ₹200–₹350 (Forest permit & local green cess)",
        "issuing_office": "Manali Forest Range Office / Prini Checkpost, Himachal Pradesh"
    },
    "roopkund-trek": {
        "trek_name": "Roopkund Mystery Lake Trek",
        "region": "Uttarakhand, India",
        "permits_required": [
            "Nanda Devi Biosphere Reserve & Trishul Wildlife Sanctuary Permit",
            "Uttarakhand Forest Department Camping Permit (Lohajung/Wan Range)"
        ],
        "documents_needed": [
            "Government Photo ID Proof + 2 self-attested copies",
            "Medical Certificate with ECG Report (recommended for high altitude)",
            "High-Altitude Indemnity Form & Environmental Undertaking"
        ],
        "fee_details": "Approx. ₹250–₹500 (Forest entry + Camping royalties)",
        "issuing_office": "Lohajung Forest Range Office / Tharali Forest Division, Chamoli, Uttarakhand"
    },
    "annapurna-circuit": {
        "trek_name": "Annapurna Circuit Trek",
        "region": "Annapurna, Nepal",
        "permits_required": [
            "Annapurna Conservation Area Project (ACAP) Permit (NPR 3,000)",
            "TIMS (Trekkers' Information Management System) Card (NPR 2,000)",
            "Mandatory Registered Licensed Guide (as per NTB safety regulations)"
        ],
        "documents_needed": [
            "Passport copy with valid Nepal entry visa",
            "2 Passport size photos",
            "Emergency High-Altitude Evacuation Insurance"
        ],
        "fee_details": "Total approx. NPR 5,000 (~₹3,150)",
        "issuing_office": "Nepal Tourism Board Office, Kathmandu or Tourist Service Center Pokhara"
    },
    "valley-of-flowers": {
        "trek_name": "Valley of Flowers & Hemkund Sahib",
        "region": "Uttarakhand, India",
        "permits_required": [
            "UNESCO World Heritage Valley of Flowers National Park Entry Permit (Valid for 3 consecutive days)",
            "Plastic Waste Deposit Registration (Non-biodegradable item tracking at checkpost)"
        ],
        "documents_needed": [
            "Valid Government Photo ID Proof (Aadhar / Voter ID / Passport)",
            "Entry Registration Slip from Ghangaria Gate"
        ],
        "fee_details": "₹200 for Indian Nationals | ₹800 for Foreign Nationals (Valid for 3 days)",
        "issuing_office": "Forest Checkpost Gate at Ghangaria, Chamoli District, Uttarakhand"
    },
    "chadar-trek": {
        "trek_name": "Chadar Frozen River Trek",
        "region": "Zanskar, Ladakh, India",
        "permits_required": [
            "Ladakh Autonomous Hill Development Council (LAHDC) Trekking Permit",
            "Wildlife Protection Department Environmental Entry Permit",
            "ALTOA Mandatory 3-Day Acclimatization Registration & SNM Hospital Leh Medical Clearance",
            "Local High-Altitude Disaster Rescue & Insurance Card"
        ],
        "documents_needed": [
            "Official Medical Clearance Certificate issued by SNM District Hospital, Leh after 3 mandatory rest days",
            "Original Government ID (Passport with Indian Visa for Foreigners)",
            "Local Rescue Insurance proof (₹2,500–₹3,000 card)"
        ],
        "fee_details": "Approx. ₹5,000–₹6,500 (LAHDC fee ₹2,000 + Wildlife ₹500 + Medical checkup ₹1,500 + Insurance ₹2,500)",
        "issuing_office": "Tourist Information Centre (TRC) Leh & Wildlife Department, Ladakh"
    },
    "tour-du-mont-blanc": {
        "trek_name": "Tour du Mont Blanc (TMB)",
        "region": "France, Italy, Switzerland (Alps)",
        "permits_required": [
            "No special trail permit required (within Schengen area)",
            "Mandatory Advance Mountain Refuge / Hut Reservations (Refuges/Rifugi/Gîtes booking vouchers must be carried; wild camping is strictly illegal below 2,500m in France/Italy)",
            "International Mountain Rescue & Repatriation Insurance"
        ],
        "documents_needed": [
            "Valid Passport with Schengen Visa (if applicable)",
            "Confirmed Refuge Accommodation Vouchers / Digital booking IDs",
            "Comprehensive Travel & Alpine Rescue Insurance Policy"
        ],
        "fee_details": "Refuge bookings approx. €55–€85/night (including dinner & breakfast)",
        "issuing_office": "Online booking via Association Tour du Mont Blanc (Montourisme) or individual refuges"
    },
    "bali-pass": {
        "trek_name": "Bali Pass Trek",
        "region": "Uttarakhand, India",
        "permits_required": [
            "Govind Wildlife Sanctuary Entry & Camping Permit (Sankri checkpost)",
            "Yamunotri Forest Division Alpine Transit Permit (Janki Chatti checkpost)"
        ],
        "documents_needed": [
            "Government Photo ID Proof (Aadhar / Passport) + 2 photocopies",
            "Doctor-signed Medical Fitness Certificate (mandatory for passes > 15,000 ft)",
            "Mountaineering / Trekking Indemnity Undertaking"
        ],
        "fee_details": "Approx. ₹300–₹500 (Forest entry + Camping fees)",
        "issuing_office": "Sankri Forest Gate & Purola Forest Division, Uttarkashi, Uttarakhand"
    },
    "kuari-pass": {
        "trek_name": "Kuari Pass Trek",
        "region": "Uttarakhand, India",
        "permits_required": [
            "Nanda Devi National Park Forest Entry Permit (Joshimath Range)",
            "Chamoli Forest Division Camping & Trail Clearance"
        ],
        "documents_needed": [
            "Government Photo ID Proof (Aadhar / Passport / Voter ID)",
            "Medical Fitness Certificate",
            "Indemnity Declaration Form"
        ],
        "fee_details": "Approx. ₹150–₹250 (Forest Department permits)",
        "issuing_office": "Joshimath Forest Range Checkpost / Dhak Gate, Chamoli, Uttarakhand"
    },
    "brahmatal-trek": {
        "trek_name": "Brahmatal Trek",
        "region": "Uttarakhand, India",
        "permits_required": [
            "Uttarakhand Forest Department Permit (Lohajung Range)",
            "Local Eco-Development Committee (EDC) Environmental Fee"
        ],
        "documents_needed": [
            "Government Photo ID Proof (Aadhar / Passport / Voter ID)",
            "Medical Certificate verifying fitness for high-altitude trekking",
            "Trekker Disclaimer Form"
        ],
        "fee_details": "Approx. ₹150–₹200 (Forest fee)",
        "issuing_office": "Lohajung Forest Range Checkpost, Chamoli District, Uttarakhand"
    },
    "goechala-trek": {
        "trek_name": "Goechala Trek",
        "region": "Sikkim, India",
        "permits_required": [
            "Kanchenjunga National Park (KNP) Entry Permit",
            "Sikkim Tourism & Civil Aviation Department Trekker's Permit",
            "Police Verification Clearance (Yuksom Police Post)",
            "Inner Line Permit (ILP) / PAP for Foreign Nationals"
        ],
        "documents_needed": [
            "Original Passport / Aadhar Card + 4 photocopies",
            "4 Passport-size photographs",
            "Medical Fitness Certificate",
            "Foreigners require minimum 2 trekkers registered with a licensed Sikkim agency"
        ],
        "fee_details": "Approx. ₹400–₹600 for Indians | ₹1,200–₹1,800 for Foreigners (Forest & Park fees)",
        "issuing_office": "KNP Forest Office & Police Checkpost at Yuksom, West Sikkim"
    },
    "har-ki-dun": {
        "trek_name": "Har Ki Dun Trek",
        "region": "Uttarakhand, India",
        "permits_required": [
            "Govind Pashu Vihar National Park & Sanctuary Entry Permit (Sankri Checkpost)",
            "Forest Department Camping Permit"
        ],
        "documents_needed": [
            "Government Photo ID Proof (Aadhar / Passport / Voter ID)",
            "Medical Fitness Certificate (signed by certified MBBS doctor)",
            "Trekker Indemnity Undertaking"
        ],
        "fee_details": "Approx. ₹150–₹250 per day",
        "issuing_office": "Sankri Forest Range Checkpost, Mori Block, Uttarkashi, Uttarakhand"
    },
    "pin-parvati-pass": {
        "trek_name": "Pin Parvati Pass Trek",
        "region": "Himachal Pradesh, India",
        "permits_required": [
            "Great Himalayan National Park (GHNP) Entry Permit (Kullu/Kasol Division)",
            "Pin Valley National Park Entry Permit (Spiti Wildlife Division, Kaza)",
            "SDM Kaza / Local Administration High-Altitude Expedition Clearance"
        ],
        "documents_needed": [
            "Government Photo ID + 4 photocopies",
            "Comprehensive Medical Fitness Certificate (ECG & Vitals)",
            "Search & Rescue High-Altitude Insurance Proof",
            "Experienced Trekker Resume / Prior 14,000+ ft trek proof"
        ],
        "fee_details": "Approx. ₹500–₹1,000 (GHNP + Pin Valley park royalties)",
        "issuing_office": "GHNP Office Shamshi (Kullu) & Wildlife Forest Office Kaza (Spiti)"
    },
    "tarsar-marsar": {
        "trek_name": "Tarsar Marsar Trek",
        "region": "Jammu & Kashmir, India",
        "permits_required": [
            "Aru Wildlife Sanctuary & Forest Protection Permit",
            "Indian Army Checkpost Security Clearance (Aru / Lidderwat Checkposts)",
            "Pahalgam Tourism Development Authority Registration"
        ],
        "documents_needed": [
            "Original Government Photo ID (Aadhar / Passport) + 3 photocopies",
            "Medical Fitness Certificate",
            "Disclaimer & Police Verification form"
        ],
        "fee_details": "Approx. ₹300–₹500 (Forest & Wildlife entry)",
        "issuing_office": "Aru Village Checkpost / TRC Pahalgam, Jammu & Kashmir"
    },
    "rupin-pass": {
        "trek_name": "Rupin Pass Trek",
        "region": "Uttarakhand to Himachal Pradesh, India",
        "permits_required": [
            "Uttarakhand Govind Wildlife Sanctuary Entry Permit (Dhaula Checkpost)",
            "Himachal Pradesh Forest Department Transit Permit (Sangla/Kinnaur Checkpost)"
        ],
        "documents_needed": [
            "Government Photo ID Proof (Aadhar / Passport) + 2 photocopies",
            "Medical Fitness Certificate",
            "Trekker Indemnity Form"
        ],
        "fee_details": "Approx. ₹300–₹450 (Interstate dual forest entry fees)",
        "issuing_office": "Dhaula Forest Post (Uttarakhand) & Sangla Forest Range Office (Himachal)"
    },
    "markha-valley": {
        "trek_name": "Markha Valley Trek",
        "region": "Ladakh, India",
        "permits_required": [
            "Hemis National Park Wildlife Protection Entry Permit",
            "Ladakh UT Ecology / Environmental Fee",
            "Inner Line Permit (ILP) for Restricted Border Villages (Chilling/Skiu)"
        ],
        "documents_needed": [
            "Government Photo ID (Passport with Indian Visa for Foreigners)",
            "Medical Fitness Self-Declaration",
            "Trekker Registration Slip from Leh"
        ],
        "fee_details": "Approx. ₹100/day for Indians | ₹200/day for Foreigners + ₹500 Environmental Fee",
        "issuing_office": "Wildlife Protection Department Office, Badami Bagh, Leh, Ladakh"
    },
    "bhrigu-lake": {
        "trek_name": "Bhrigu Lake Trek",
        "region": "Himachal Pradesh, India",
        "permits_required": [
            "Himachal Pradesh Forest Department Permit (Manali Range)",
            "Gulaba Checkpost Green Tax & Vehicle Environmental Permit"
        ],
        "documents_needed": [
            "Government Photo ID Proof (Aadhar / Passport)",
            "Medical Fitness Certificate"
        ],
        "fee_details": "Approx. ₹100–₹200",
        "issuing_office": "Gulaba Forest Checkpost / Manali Forest Range Office"
    },
    "manaslu-circuit": {
        "trek_name": "Manaslu Circuit Trek",
        "region": "Gorkha/Manaslu, Nepal",
        "permits_required": [
            "Manaslu Restricted Area Permit (RAP - Mandatory licensed guide + min. 2 trekkers)",
            "Manaslu Conservation Area Project (MCAP) Permit (NPR 3,000)",
            "Annapurna Conservation Area Project (ACAP) Permit (NPR 3,000 - for exit via Dharapani)",
            "TIMS Card"
        ],
        "documents_needed": [
            "Original Passport with minimum 6-month validity and valid Nepal visa",
            "4 Passport-size photographs",
            "Registered Nepali trekking agency authorization document"
        ],
        "fee_details": "RAP: $100/week (Autumn Sep–Nov) or $75/week (Dec–Aug) + MCAP/ACAP permits (~$50)",
        "issuing_office": "Department of Immigration, Kalikasthan, Kathmandu, Nepal"
    },
    "inca-trail": {
        "trek_name": "Classic Inca Trail to Machu Picchu",
        "region": "Cusco, Peru",
        "permits_required": [
            "Official SERNANP / Peruvian Ministry of Culture Inca Trail Permit (Strictly capped at 500 people/day; must be booked 4–6 months in advance)",
            "Machu Picchu Historic Sanctuary Entry Ticket"
        ],
        "documents_needed": [
            "Original Physical Passport (must exactly match passport number used during booking)",
            "ISIC Student Card (if booked under student discount)",
            "Travel & Evacuation Insurance"
        ],
        "fee_details": "Approx. $250–$350 USD (included in authorized guide package)",
        "issuing_office": "Peruvian Ministry of Culture (SERNANP), Cusco, Peru"
    },
    "mount-kilimanjaro": {
        "trek_name": "Mount Kilimanjaro (Machame Route)",
        "region": "Kilimanjaro, Tanzania",
        "permits_required": [
            "Kilimanjaro National Park (KINAPA) Entry Permit",
            "Tanzania National Parks Authority (TANAPA) Conservation & Camping Permit",
            "Mandatory TANAPA Licensed Mountain Guide, Porters & Cook Team Registration",
            "Mountain Rescue & Emergency Evacuation Fee"
        ],
        "documents_needed": [
            "Valid Passport with Tanzania Visa (or tourist eVisa)",
            "Yellow Fever Vaccination Certificate (if arriving from endemic zones)",
            "Comprehensive High-Altitude Mountain Rescue & Repatriation Insurance Policy"
        ],
        "fee_details": "Approx. $70/day park entry + $50/night camping + $20 rescue fee (~$800–$1,000 USD total)",
        "issuing_office": "TANAPA Headquarters, Machame Gate / Marangu Gate, Moshi, Tanzania"
    },
    "island-peak": {
        "trek_name": "Island Peak (Imja Tse)",
        "region": "Khumbu, Nepal",
        "permits_required": [
            "Nepal Mountaineering Association (NMA) Climbing Permit (Class A Peak)",
            "Sagarmatha National Park Entry Permit (NPR 3,000)",
            "Khumbu Pasang Lhamu Rural Municipality Permit (NPR 2,000)",
            "NMA Garbage Deposit Bond ($250 refundable)"
        ],
        "documents_needed": [
            "Valid Passport with Nepal Visa",
            "NMA Climbing Registration Form with certified Sherpa climbing guide",
            "Mountaineering Insurance covering technical rescue up to 6,500m"
        ],
        "fee_details": "NMA Permit: $250 (Spring) / $125 (Autumn) / $70 (Winter/Summer) + Park fees",
        "issuing_office": "Nepal Mountaineering Association (NMA) Office, Naxal, Kathmandu"
    },
    "mera-peak": {
        "trek_name": "Mera Peak Expedition",
        "region": "Hinku Valley, Nepal",
        "permits_required": [
            "NMA (Nepal Mountaineering Association) Climbing Permit (Group B Peak)",
            "Makalu Barun National Park Entry Permit (NPR 3,000)",
            "Local Municipality Entry Fee"
        ],
        "documents_needed": [
            "Valid Passport with Nepal Visa",
            "Certified Climbing Guide Registration",
            "Climbing Insurance with helicopter evacuation coverage up to 6,500m"
        ],
        "fee_details": "NMA Permit: $250 (Spring) / $125 (Autumn) + Makalu park permit",
        "issuing_office": "NMA Office, Kathmandu, Nepal"
    }
}

# Build System Prompt with full repository trek knowledge & permits
def get_system_prompt():
    treks_summary = []
    for t in treks_data.TREKS_DATA:
        t_id = t.get('id', '')
        permit_info = PERMITS_DATA.get(t_id)
        permit_str = ""
        if permit_info:
            permit_str = f"Required Permits={', '.join(permit_info['permits_required'])}, Docs Needed={', '.join(permit_info['documents_needed'][:2])}, Fee={permit_info['fee_details']}"
        
        treks_summary.append(
            f"- {t.get('name')} (ID: {t.get('id')}): Region={t.get('region')}, Country={t.get('country')}, "
            f"Max Altitude={t.get('max_altitude_text')}, Duration={t.get('duration_text')}, "
            f"Difficulty={t.get('difficulty')} ({t.get('fitness_level')}), "
            f"Best Season={t.get('best_season')}, Price={t.get('price')}, "
            f"{permit_str}"
        )
    treks_context = "\n".join(treks_summary)

    return f"""You are 'Sherpa AI', the elite AI High-Altitude Mountain Guide and Expedition Strategist on 'Trekkers Heaven' (a premier Himalayan & Global trekking platform).

Your Persona & Mission:
- Friendly, adventurous, safety-focused, and deeply knowledgeable about mountain trails and government regulations.
- You provide concise, actionable, and structured guidance for expeditions in the Himalayas (Uttarakhand, Himachal Pradesh, Jammu & Kashmir, Ladakh, Sikkim, Nepal) and International ranges (European Alps: Switzerland, France, Italy, Peru, Tanzania).
- You recommend ideal trails based on fitness, season, budget, and altitude comfort.
- You actively provide Altitude Sickness (AMS) safety protocols, 3-layer packing checklists, AND government/forest/wildlife PERMITS & DOCUMENTS requirements for each trek.

Website Trek Catalog & Permit Knowledge:
{treks_context}

Permit Guidelines:
1. When asked about permits for any trek, detail:
   • Official Permits & National Park / Wildlife Sanctuaries passes required
   • Mandatory identification documents (Aadhar, Passport, Medical Fitness Certificate signed by MBBS doctor)
   • Estimated fee details and issuing forest/police checkposts
   • Pro-tip: Explain that registered trekking agencies on Trekkers Heaven arrange forest & wildlife permits on behalf of trekkers at basecamp checkposts.
2. Use clean GitHub-flavored Markdown (bolding, bullet points, emoji headings).
3. If the user asks in Hindi or Hinglish, reply warmly in natural Hinglish/Hindi or English as appropriate.
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
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_name in candidate_models:
            try:
                from google.genai import types
                
                contents = []
                if history and isinstance(history, list):
                    for turn in history[-6:]:
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
    if "permit" in q_lower or "document" in q_lower:
        return ["What medical certificate is needed?", "Permits for Chadar Trek", "Permits for Everest Base Camp", "Packing essentials checklist"]
    elif "compare" in q_lower or " vs " in q_lower:
        return ["Show day-wise itinerary", "What gear should I pack?", "Required permits for this trek"]
    elif "beginner" in q_lower or "easy" in q_lower:
        return ["Kedarkantha Trek permits", "Brahmatal Trek permits", "Beginner packing checklist"]
    elif "ams" in q_lower or "altitude" in q_lower or "sickness" in q_lower:
        return ["AMS Prevention guide", "High-altitude medical kit", "Beginner friendly treks"]
    elif "winter" in q_lower or "snow" in q_lower:
        return ["Top winter snow treks", "Winter clothing guide", "Permits for Chadar Trek"]
    elif "budget" in q_lower or "price" in q_lower or "cost" in q_lower or "10000" in q_lower:
        return ["Treks under ₹10,000", "Kedarkantha Trek", "Brahmatal Trek"]
    else:
        return ["Required permits for Kedarkantha", "Compare Kedarkantha vs Brahmatal", "AMS Safety tips", "View Trek Essentials Checklist"]

def find_matched_treks(msg_lower: str):
    """Find matching treks from the catalog based on user query."""
    matched = []
    
    # Aliases
    alias_dict = {
        'ebc': 'everest-base-camp',
        'kgl': 'kashmir-great-lakes',
        'tmb': 'tour-du-mont-blanc',
        'kk': 'kedarkantha-summit',
        'kedar': 'kedarkantha',
        'kedarkantha': 'kedarkantha',
        'brahma': 'brahmatal-trek',
        'brahmatal': 'brahmatal-trek',
        'hampta': 'hampta-pass',
        'har ki dun': 'har-ki-dun',
        'roopkund': 'roopkund-trek',
        'kuari': 'kuari-pass',
        'chadar': 'chadar-trek',
        'pin parvati': 'pin-parvati-pass',
        'rupin': 'rupin-pass',
        'bali pass': 'bali-pass',
        'valley of flowers': 'valley-of-flowers',
        'vof': 'valley-of-flowers',
        'annapurna': 'annapurna-circuit',
        'manaslu': 'manaslu-circuit',
        'langtang': 'langtang-valley',
        'gokyo': 'gokyo-ri-lakes',
        'island peak': 'island-peak',
        'mera peak': 'mera-peak',
        'markha': 'markha-valley',
        'tarsar': 'tarsar-marsar',
        'bhrigu': 'bhrigu-lake',
        'beas kund': 'beas-kund',
        'sandakphu': 'sandakphu-phalut',
        'goechala': 'goechala-trek',
        'inca': 'inca-trail',
        'kilimanjaro': 'mount-kilimanjaro',
        'kili': 'mount-kilimanjaro',
        'stok': 'stok-kangri',
        'kang yatse': 'kang-yatse-2',
        'friendship': 'friendship-peak',
        'yunam': 'yunam-peak',
        'pangarchulla': 'pangarchulla-peak'
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

def get_permit_response_for_trek(trek: dict) -> dict:
    """Generate detailed permit response for a specific trek."""
    t_id = trek['id']
    p = PERMITS_DATA.get(t_id)
    
    if p:
        permits_bullets = "\n".join([f"• {item}" for item in p['permits_required']])
        docs_bullets = "\n".join([f"• {item}" for item in p['documents_needed']])
        
        reply = (
            f"📋 **Required Permits & Documents for {p['trek_name']}** ({p['region']})\n\n"
            f"🏛️ **Official Permits Required:**\n{permits_bullets}\n\n"
            f"📄 **Mandatory Identification & Medical Documents:**\n{docs_bullets}\n\n"
            f"💵 **Permit Fees:** {p['fee_details']}\n"
            f"📍 **Issuing Authority / Checkpost:** {p['issuing_office']}\n\n"
            f"💡 **Trekkers Heaven Pro-Tip:** *When you book your trek with registered operators on our platform, all local forest department, wildlife sanctuary, and camping permits are arranged for you at the basecamp checkpost!*"
        )
    else:
        reply = (
            f"📋 **Permits & Entry Details for {trek['name']}** ({trek.get('region')}, {trek.get('country')})\n\n"
            f"🏛️ **Forest & Trail Permits:**\n"
            f"• State Forest Department Transit & Camping Permit\n"
            f"• Local Wildlife Protection / Environmental Entry Pass\n\n"
            f"📄 **Mandatory Documents to Carry:**\n"
            f"• Original Government Photo ID Proof (Aadhar / Passport) + 2 photocopies\n"
            f"• Medical Fitness Certificate signed by a certified doctor\n"
            f"• Trekker Disclaimer / Indemnity Undertaking\n\n"
            f"💡 *All forest and entry permits are verified at the basecamp trailhead before entering the trail.*"
        )
        
    return {
        "success": True,
        "source": "local-fallback",
        "reply": reply,
        "trek_id": trek['id'],
        "trek_name": trek['name'],
        "suggestions": [f"Show itinerary for {trek['name']}", f"Packing list for {trek['name']}", "AMS Prevention rules"]
    }

def local_trek_engine_fallback(msg: str) -> dict:
    """Rich rule-based fallback engine when Gemini API key is missing or offline."""
    msg_lower = msg.lower().strip()
    matched_treks = find_matched_treks(msg_lower)
    is_permit_query = any(k in msg_lower for k in ['permit', 'permission', 'document', 'forest pass', 'id proof', 'parwana', 'entry fee', 'ilp', 'inner line', 'tims', 'acap', 'kinapa', 'nma', 'medical certificate'])
    is_compare = any(k in msg_lower for k in ['compare', 'vs', 'versus', 'difference', 'better', 'which one', 'antar', 'tulna', 'dono', 'kon sa'])

    # 1. Permit Query for a matched trek
    if is_permit_query and len(matched_treks) >= 1:
        return get_permit_response_for_trek(matched_treks[0])

    # 2. General Permit Query
    if is_permit_query and len(matched_treks) == 0:
        reply = (
            "📋 **Himalayan & Global Trek Permits Overview:**\n\n"
            "Depending on the region, different government, forest, and wildlife permits are required:\n\n"
            "🌲 **1. Uttarakhand Treks (Kedarkantha, Har Ki Dun, Roopkund, Valley of Flowers):**\n"
            "• Uttarakhand Forest Department Camping & Trail Entry Permits.\n"
            "• Govind Wildlife Sanctuary / Nanda Devi Biosphere Passes.\n"
            "• Documents: Aadhar/Passport + MBBS Doctor Medical Fitness Certificate.\n\n"
            "🏔️ **2. Himachal Pradesh Treks (Hampta Pass, Pin Parvati, Bhrigu Lake):**\n"
            "• Kullu/Manali Forest Division Entry & Rohtang Green Tax.\n"
            "• Great Himalayan National Park (GHNP) & Pin Valley SDM clearance for crossovers.\n\n"
            "🛡️ **3. Jammu & Kashmir & Ladakh (Kashmir Great Lakes, Chadar, Markha):**\n"
            "• Indian Army Checkpost Clearance & J&K Wildlife Protection Permit.\n"
            "• Chadar Trek requires mandatory 3-day Leh acclimatization + SNM Hospital Leh medical clearance.\n\n"
            "🇳🇵 **4. Nepal Expeditions (Everest Base Camp, Annapurna, Manaslu):**\n"
            "• Sagarmatha / Annapurna Conservation Area (ACAP) Permits + TIMS Card.\n"
            "• Manaslu requires Special Restricted Area Permit (RAP) with a licensed guide.\n\n"
            "💡 *Ask me about permits for any specific trek (e.g., 'Permits for Kedarkantha' or 'Chadar Trek permits') for a detailed breakdown!*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Permits for Kedarkantha", "Permits for Chadar Trek", "Permits for Everest Base Camp", "Permits for Kashmir Great Lakes"]
        }

    # 3. Comparison between 2 treks
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
            "suggestions": [f"Show itinerary for {t1['name']}", f"Show itinerary for {t2['name']}", f"Required permits for {t1['name']}"]
        }

    # 4. General comparison intent
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

    # 5. Single Specific Trek Details
    if len(matched_treks) == 1:
        t = matched_treks[0]
        t_clean_name = t['name'].replace(' Trek', '').replace(' Pass', '').strip()
        highlights_list = "\n • " + "\n • ".join(t.get('highlights', [])[:4])
        
        # Permit summary line
        p_info = PERMITS_DATA.get(t['id'])
        permit_line = f"• **Permits:** {p_info['permits_required'][0]}" if p_info else "• **Permits:** Forest Department & Local Entry Clearance"
        
        reply = (
            f"🏔️ **{t['name']}** ({t.get('region')}, {t.get('country')})\n\n"
            f"✨ *{t.get('tagline')}*\n\n"
            f"• **Max Altitude:** {t.get('max_altitude_text')}\n"
            f"• **Duration:** {t.get('duration_text')} ({t.get('distance_text')})\n"
            f"• **Difficulty:** {t.get('difficulty')} ({t.get('fitness_level')})\n"
            f"• **Best Season:** {t.get('best_season')}\n"
            f"• **Price:** {t.get('price')} (Rating: ⭐ {t.get('rating')})\n"
            f"{permit_line}\n\n"
            f"📌 **Key Highlights:**{highlights_list}\n\n"
            f"💡 *{t.get('description')}*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "trek_id": t['id'],
            "trek_name": t['name'],
            "suggestions": [f"Required permits for {t_clean_name}", f"Show itinerary for {t_clean_name}", f"Compare {t['name']} vs Brahmatal"]
        }

    # 6. Greetings
    if any(w in msg_lower for w in ['hello', 'hi', 'hey', 'namaste', 'kem cho', 'salaam', 'yo', 'sup']):
        return {
            "success": True,
            "source": "local-fallback",
            "reply": "Namaste! 🏔️ Welcome to **Trekkers Heaven**. I'm **Sherpa AI**, your personal AI mountain guide. I can help you with trail recommendations, required forest permits, packing checklists, and AMS safety advice. What trail are you exploring?",
            "suggestions": ["Required permits for treks", "Best beginner treks under ₹10k", "Top winter snow treks", "How to prevent AMS?"]
        }

    # 7. Altitude Sickness / AMS
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
            "suggestions": ["Essential gear list", "Easy beginner treks", "Required permits for treks"]
        }

    # 8. Packing / Gear / Essentials
    if any(w in msg_lower for w in ['pack', 'gear', 'shoe', 'jacket', 'backpack', 'checklist', 'clothes', 'rucksack', 'layer', 'saman']):
        reply = (
            "🎒 **Trek Packing Essentials:**\n\n"
            "• **Footwear:** Waterproof high-ankle trekking shoes with deep vibram lugs + 4-5 pairs of synthetic/wool socks.\n"
            "• **3-Layer Clothing Rule:**\n"
            "   1. *Base Layer:* Moisture-wicking thermal top & bottom (avoid cotton!).\n"
            "   2. *Mid Layer:* Warm fleece or synthetic sweater.\n"
            "   3. *Outer Layer:* Windproof/waterproof down jacket (-10°C rated) + rain poncho.\n"
            "• **Gear:** 50–60L rucksack with rain cover, UV sunglasses (Cat 3/4), headlamp with extra batteries, trekking poles.\n"
            "• **Medical & Documents:** Sunscreen (SPF 50+), personal medical kit, Aadhar card/Passport, and Doctor-signed Medical Fitness Certificate.\n\n"
            "💡 *Tip: Check out the **Trek Essentials Checklist** button next to me in the navbar to track your items!*"
        )
        return {
            "success": True,
            "source": "local-fallback",
            "reply": reply,
            "suggestions": ["Required permits for treks", "Best winter snow treks", "Physical fitness routine"]
        }

    # 9. Beginner / Easy Treks
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
            "suggestions": ["Permits for Kedarkantha", "Permits for Brahmatal", "Packing list for beginners"]
        }

    # 10. Budget / Price queries
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
            "suggestions": ["Permits for Kedarkantha", "Permits for Bhrigu Lake", "Permits for Har Ki Dun"]
        }

    # 11. Winter / Snow Treks
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
            "suggestions": ["Permits for Chadar Trek", "Permits for Kedarkantha", "Winter packing essentials"]
        }

    # 12. Regional Searches
    for reg in ['uttarakhand', 'himachal', 'kashmir', 'ladakh', 'sikkim', 'nepal', 'peru', 'switzerland', 'france', 'italy', 'tanzania']:
        if reg in msg_lower:
            reg_treks = [t for t in treks_data.TREKS_DATA if reg in t.get('region', '').lower() or reg in t.get('country', '').lower()]
            if reg_treks:
                lines = [f"• **{t['name']}** - {t['max_altitude_text']} | {t['price']} ({t['difficulty']})" for t in reg_treks[:5]]
                reply = (
                    f"🗺️ **Treks in {reg.capitalize()}:**\n\n"
                    + "\n".join(lines) +
                    f"\n\nWhich of these would you like to know more about or check required permits for?"
                )
                return {
                    "success": True,
                    "source": "local-fallback",
                    "reply": reply,
                    "suggestions": [f"Permits for {reg_treks[0]['name']}", f"Tell me about {reg_treks[0]['name']}", "Packing checklist"]
                }

    # 13. Default friendly response
    return {
        "success": True,
        "source": "local-fallback",
        "reply": (
            "I'm here to help you plan your next mountain adventure on **Trekkers Heaven**!\n\n"
            "You can ask me questions like:\n"
            "• *'What permits are required for Kedarkantha or Chadar Trek?'*\n"
            "• *'Compare Kedarkantha vs Brahmatal'*\n"
            "• *'What are the best winter snow treks?'*\n"
            "• *'How to prevent AMS (altitude sickness)?'*\n"
            "• *'Which treks are under ₹10,000?'*\n"
            "• *'What gear should I pack?'*"
        ),
        "suggestions": ["Required permits for Kedarkantha", "Permits for Chadar Trek", "Compare Kedarkantha vs Brahmatal", "AMS Safety tips"]
    }

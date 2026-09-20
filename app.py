import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import database
import treks_data
import gemini_service

# Load environment variables (.env)
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static', template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-auth-key-change-in-production-2026')
app.permanent_session_lifetime = timedelta(days=7)

# Explicit static route for Vercel serverless environment
@app.route('/static/<path:filename>')
def serve_vercel_static(filename):
    return send_from_directory(STATIC_DIR, filename)

# Initialize database tables on startup
database.init_db()

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

def validate_registration_data(name, email, password, confirm_password=None):
    """Validate registration input fields."""
    if not name or len(name.strip()) < 1:
        return False, "Please enter your full name."
    if not email or not re.match(EMAIL_REGEX, email.strip()):
        return False, "Please enter a valid email address."
    if not password:
        return False, "Please enter a password."
    if confirm_password is not None and password != confirm_password:
        return False, "Passwords do not match."
    return True, ""

@app.route('/')
def index():
    """Main route: redirect to treks if logged in, else show login/register."""
    if 'user_id' in session:
        return redirect(url_for('treks'))
    mode = request.args.get('mode', 'register')
    return render_template('auth.html', initial_mode=mode)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if 'user_id' in session:
        return redirect(url_for('treks'))

    if request.method == 'GET':
        return render_template('auth.html', initial_mode='register')

    # Handle JSON and Form data
    is_json = request.is_json
    data = request.get_json() if is_json else request.form

    name = data.get('name', '').strip()
    if not name:
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        name = f"{first_name} {last_name}".strip() if last_name else first_name

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    # Validate inputs
    is_valid, error_msg = validate_registration_data(name, email, password, confirm_password if confirm_password else None)
    if not is_valid:
        if is_json:
            return jsonify({'success': False, 'message': error_msg}), 400
        flash(error_msg, 'danger')
        return render_template('auth.html', initial_mode='register', prev_name=name, prev_email=email)

    # Check if user already exists
    existing_user = database.get_user_by_email(email)
    if existing_user:
        error_msg = "An account with this email address already exists. Please sign in."
        if is_json:
            return jsonify({'success': False, 'message': error_msg}), 409
        flash(error_msg, 'warning')
        return render_template('auth.html', initial_mode='login', prev_email=email)

    # Hash password securely and create user
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    result = database.create_user(name, email, password_hash)

    if result['success']:
        # Auto-login after registration
        session.permanent = True
        session['user_id'] = result['user_id']
        session['user_name'] = name
        session['user_email'] = email
        database.update_last_login(result['user_id'])

        success_msg = f"Account created successfully! Welcome, {name}."
        if is_json:
            return jsonify({
                'success': True,
                'message': success_msg,
                'redirect': url_for('treks')
            }), 201
        flash(success_msg, 'success')
        return redirect(url_for('treks'))
    else:
        err = result.get('error', 'Registration failed. Please try again.')
        if is_json:
            return jsonify({'success': False, 'message': err}), 500
        flash(err, 'danger')
        return render_template('auth.html', initial_mode='register', prev_name=name, prev_email=email)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if 'user_id' in session:
        return redirect(url_for('treks'))

    if request.method == 'GET':
        return render_template('auth.html', initial_mode='login')

    is_json = request.is_json
    data = request.get_json() if is_json else request.form

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = data.get('remember', False)

    if not email or not password:
        err = "Please enter both email and password."
        if is_json:
            return jsonify({'success': False, 'message': err}), 400
        flash(err, 'danger')
        return render_template('auth.html', initial_mode='login', prev_email=email)

    user = database.get_user_by_email(email)

    if not user or not check_password_hash(user['password_hash'], password):
        err = "Invalid email or password. Please try again."
        if is_json:
            return jsonify({'success': False, 'message': err}), 401
        flash(err, 'danger')
        return render_template('auth.html', initial_mode='login', prev_email=email)

    # Session setup
    session.permanent = bool(remember)
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    database.update_last_login(user['id'])

    success_msg = f"Welcome back, {user['name']}!"
    if is_json:
        return jsonify({
            'success': True,
            'message': success_msg,
            'redirect': url_for('treks')
        }), 200

    flash(success_msg, 'success')
    return redirect(url_for('treks'))

def enrich_achievement(ach):
    """Enrich achievement row with full technical trek metadata from TREKS_DATA."""
    ach_copy = dict(ach)
    trek_name = (ach_copy.get('trek_name') or '').strip().lower()
    trek_id = ach_copy.get('trek_id') or ''
    
    matching = next((t for t in treks_data.TREKS_DATA if t['id'] == trek_id or t['name'].lower() == trek_name or t['name'].lower() in trek_name or trek_name in t['name'].lower()), None)
    if matching:
        ach_copy['trek_id'] = matching['id']
        ach_copy['trek_name'] = matching['name']
        ach_copy['duration_text'] = matching.get('duration_text', f"{matching.get('duration_days')} Days")
        ach_copy['distance_text'] = matching.get('distance_text', f"{matching.get('distance_km')} km")
        ach_copy['altitude'] = ach_copy.get('altitude') or matching.get('max_altitude_text', '')
        ach_copy['altitude_ft'] = ach_copy.get('altitude_ft') or matching.get('max_altitude_ft', 0)
        ach_copy['difficulty'] = ach_copy.get('difficulty') or matching.get('difficulty', 'Moderate')
        ach_copy['difficulty_slug'] = matching.get('difficulty_slug', 'moderate')
        ach_copy['best_season'] = matching.get('best_season', '')
        ach_copy['location'] = ach_copy.get('location') or f"{matching.get('region', '')}, {matching.get('country', '')}"
        ach_copy['highlights'] = matching.get('highlights', [])
        ach_copy['tagline'] = matching.get('tagline', '')
    else:
        ach_copy['duration_text'] = ach_copy.get('duration_text') or ach_copy.get('duration') or ''
        ach_copy['distance_text'] = ach_copy.get('distance_text') or ach_copy.get('distance') or ''
        ach_copy['difficulty_slug'] = (ach_copy.get('difficulty') or 'moderate').lower().replace(' ', '-')
        ach_copy['best_season'] = ''
        ach_copy['highlights'] = []
        ach_copy['tagline'] = ''
    return ach_copy

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    """User profile management and completed treks dashboard."""
    if 'user_id' not in session:
        flash('Please log in to access your dashboard.', 'warning')
        return redirect(url_for('login'))

    user = database.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        flash('User account not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        is_json = request.is_json
        data = request.get_json() if is_json else request.form

        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        birthdate = data.get('birthdate', '').strip()
        age = data.get('age', '').strip()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        country = data.get('country', '').strip()

        if not name:
            err = "Name cannot be empty."
            if is_json:
                return jsonify({'success': False, 'message': err}), 400
            flash(err, 'danger')
            return redirect(url_for('dashboard'))

        result = database.update_user_profile(user['id'], {
            'name': name,
            'phone': phone,
            'birthdate': birthdate,
            'age': age,
            'city': city,
            'state': state,
            'country': country
        })

        if result.get('success'):
            session['user_name'] = name
            user = database.get_user_by_id(user['id'])
            success_msg = 'Profile updated successfully!'
            if is_json:
                return jsonify({'success': True, 'message': success_msg, 'user': dict(user)})
            flash(success_msg, 'success')
            return redirect(url_for('dashboard'))
        else:
            err = result.get('error', 'Failed to update profile.')
            if is_json:
                return jsonify({'success': False, 'message': err}), 500
            flash(err, 'danger')

    raw_achievements = database.get_user_achievements(user['id'])
    achievements = [enrich_achievement(a) for a in raw_achievements]
    return render_template('dashboard.html', user=user, achievements=achievements, all_treks=treks_data.TREKS_DATA)

@app.route('/change-password', methods=['POST'])
@app.route('/api/user/change-password', methods=['POST'])
def change_password():
    """Handle change password for logged in user."""
    if 'user_id' not in session:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        flash('Please log in to continue.', 'danger')
        return redirect(url_for('index', mode='login'))

    user = database.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        if request.is_json:
            return jsonify({'success': False, 'message': 'User account not found.'}), 404
        flash('User account not found.', 'danger')
        return redirect(url_for('index', mode='login'))

    data = request.get_json() if request.is_json else request.form
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_new_password = data.get('confirm_new_password', '').strip()

    if not current_password:
        msg = 'Please enter your current password.'
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'danger')
        return redirect(url_for('dashboard', tab='settings'))

    if not check_password_hash(user['password_hash'], current_password):
        msg = 'Incorrect current password. Please try again.'
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'danger')
        return redirect(url_for('dashboard', tab='settings'))

    if not new_password or len(new_password) < 6:
        msg = 'New password must be at least 6 characters long.'
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'danger')
        return redirect(url_for('dashboard', tab='settings'))

    if new_password == current_password:
        msg = 'New password cannot be the same as your current password.'
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'danger')
        return redirect(url_for('dashboard', tab='settings'))

    if new_password != confirm_new_password:
        msg = 'New passwords do not match.'
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'danger')
        return redirect(url_for('dashboard', tab='settings'))

    new_hash = generate_password_hash(new_password)
    res = database.update_user_password(user['id'], new_hash)
    if not res['success']:
        msg = 'Failed to update password. Please try again.'
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'danger')
        return redirect(url_for('dashboard', tab='settings'))

    success_msg = 'Password changed successfully!'
    if request.is_json:
        return jsonify({'success': True, 'message': success_msg})
    flash(success_msg, 'success')
    return redirect(url_for('dashboard', tab='settings'))

@app.route('/logout')
def logout():
    """Clear session and log out user."""
    name = session.get('user_name', 'User')
    session.clear()
    flash(f"You have been successfully logged out. Goodbye, {name}!", "info")
    return redirect(url_for('login'))

@app.route('/api/check-email', methods=['POST'])
def check_email():
    """Real-time email availability check."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email or not re.match(EMAIL_REGEX, email):
        return jsonify({'valid': False, 'message': 'Invalid email format'})

    user = database.get_user_by_email(email)
    return jsonify({
        'valid': True,
        'available': user is None,
        'message': 'Email is available' if user is None else 'Email is already registered'
    })

@app.route('/treks')
def treks():
    """Famous Treks Explorer page with sidebar filters."""
    user = None
    if 'user_id' in session:
        user = database.get_user_by_id(session['user_id'])
    return render_template('treks.html', treks=treks_data.TREKS_DATA, user=user)

@app.route('/treks/<trek_id>/guide')
def trek_guide_page(trek_id):
    """Render a dedicated, print-ready, in-browser Trek Expedition Guide & Itinerary page."""
    trek = next((t for t in treks_data.TREKS_DATA if t['id'] == trek_id), None)
    if not trek:
        flash("Trek not found.", "danger")
        return redirect(url_for('treks'))
    
    permits = gemini_service.PERMITS_DATA.get(trek_id, {
        'trek_name': trek['name'],
        'region': f"{trek.get('region', '')}, {trek.get('country', '')}",
        'permits_required': [
            'State Forest Department Transit & Camping Permit',
            'Local Wildlife Sanctuary / Environmental Entry Pass'
        ],
        'documents_needed': [
            'Original Government Photo ID Proof (Aadhaar / Passport / Voter ID) + 2 photocopies',
            'Medical Fitness Certificate signed by a certified MBBS doctor',
            'Trekker Disclaimer & Indemnity Undertaking Form'
        ],
        'fee_details': 'Approx. ₹150–₹350 per day (Forest & Sanctuary fees)',
        'issuing_office': f"{trek.get('start_point', 'Basecamp')} Forest Checkpost Gate"
    })
    
    emergency_sos = {
        'helpline_india': '112 / 1070 (Disaster Management)',
        'sdrf_uttarakhand': '+91-135-2710334 / 1070',
        'sdrf_himachal': '+91-177-2812344 / 1070',
        'jk_rescue': '+91-194-2452138 / 100',
        'ladakh_rescue': '+91-1982-255588',
        'nepal_rescue': '+977-1-4247041 (HRA Kathmandu) / 100',
        'ambulance': '108',
        'medical_guideline': 'Never ascend with AMS symptoms. Hydrate 4L/day, carry Diamox after medical consult, and inform trek leader immediately.'
    }
    
    user = None
    if 'user_id' in session:
        user = database.get_user_by_id(session['user_id'])
        
    return render_template('trek_guide.html', trek=trek, permits=permits, emergency_sos=emergency_sos, user=user)

@app.route('/api/treks')
def api_treks():
    """API endpoint to get all treks dataset for client-side filtering."""
    return jsonify(treks_data.TREKS_DATA)

@app.route('/api/treks/<trek_id>')
def api_trek_detail(trek_id):
    """Get single trek details."""
    trek = next((t for t in treks_data.TREKS_DATA if t['id'] == trek_id), None)
    if not trek:
        return jsonify({'error': 'Trek not found'}), 404
    return jsonify(trek)

@app.route('/api/treks/<trek_id>/guide')
def api_trek_guide(trek_id):
    """Get complete trek guide data including permits, emergency contacts, and packing guidelines."""
    trek = next((t for t in treks_data.TREKS_DATA if t['id'] == trek_id), None)
    if not trek:
        return jsonify({'success': False, 'error': 'Trek not found'}), 404
    
    permits = gemini_service.PERMITS_DATA.get(trek_id, {
        'trek_name': trek['name'],
        'region': f"{trek.get('region', '')}, {trek.get('country', '')}",
        'permits_required': [
            'State Forest Department Transit & Camping Permit',
            'Local Wildlife Sanctuary / Environmental Entry Pass'
        ],
        'documents_needed': [
            'Original Government Photo ID Proof (Aadhaar / Passport / Voter ID) + 2 photocopies',
            'Medical Fitness Certificate signed by a certified MBBS doctor',
            'Trekker Disclaimer & Indemnity Undertaking Form'
        ],
        'fee_details': 'Approx. ₹150–₹350 per day (Forest & Sanctuary fees)',
        'issuing_office': f"{trek.get('start_point', 'Basecamp')} Forest Checkpost Gate"
    })
    
    emergency_sos = {
        'helpline_india': '112 / 1070 (Disaster Management)',
        'sdrf_uttarakhand': '+91-135-2710334 / 1070',
        'sdrf_himachal': '+91-177-2812344 / 1070',
        'jk_rescue': '+91-194-2452138 / 100',
        'ladakh_rescue': '+91-1982-255588',
        'nepal_rescue': '+977-1-4247041 (HRA Kathmandu) / 100',
        'ambulance': '108',
        'medical_guideline': 'Never ascend with AMS symptoms. Inform trek leader immediately.'
    }
    
    return jsonify({
        'success': True,
        'trek': trek,
        'permits': permits,
        'emergency_sos': emergency_sos
    })

@app.route('/api/user/achievements', methods=['GET', 'POST'])
def api_user_achievements():
    """API endpoint for fetching and creating user achievements."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    if request.method == 'POST':
        data = request.get_json() or {}
        trek_name = data.get('trek_name', '').strip()
        if not trek_name:
            return jsonify({'error': 'Trek name is required'}), 400
        
        # If matching known trek in dataset, auto-fill rich attributes
        matching_trek = next((t for t in treks_data.TREKS_DATA if t['name'].lower() == trek_name.lower() or t['id'] == data.get('trek_id') or t['name'].lower() in trek_name.lower() or trek_name.lower() in t['name'].lower()), None)
        if matching_trek:
            data.setdefault('trek_id', matching_trek['id'])
            data.setdefault('trek_name', matching_trek['name'])
            data['altitude'] = data.get('altitude') or matching_trek.get('max_altitude_text', '')
            data['altitude_ft'] = data.get('altitude_ft') or matching_trek.get('max_altitude_ft', 0)
            data['distance'] = data.get('distance') or matching_trek.get('distance_text', '')
            data['difficulty'] = data.get('difficulty') or matching_trek.get('difficulty', '')
            data['location'] = data.get('location') or f"{matching_trek.get('region', '')}, {matching_trek.get('country', '')}"
            data['image_url'] = data.get('image_url') or matching_trek.get('image', '')
        
        res = database.add_user_achievement(user_id, data)
        if res.get('success'):
            raw = database.get_user_achievements(user_id)
            achievements = [enrich_achievement(a) for a in raw]
            return jsonify({'success': True, 'achievements': achievements}), 201
        return jsonify({'error': res.get('error', 'Failed to save achievement')}), 500

    raw = database.get_user_achievements(user_id)
    achievements = [enrich_achievement(a) for a in raw]
    return jsonify({'success': True, 'achievements': achievements})

@app.route('/api/user/achievements/<int:achievement_id>', methods=['DELETE'])
def api_delete_user_achievement(achievement_id):
    """API endpoint to delete a completed trek entry."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    database.delete_user_achievement(achievement_id, user_id)
    raw = database.get_user_achievements(user_id)
    achievements = [enrich_achievement(a) for a in raw]
    return jsonify({'success': True, 'achievements': achievements})

UPLOAD_CERT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'certificates')
try:
    os.makedirs(UPLOAD_CERT_FOLDER, exist_ok=True)
except Exception:
    pass

@app.route('/api/user/achievements/<int:achievement_id>/certificate', methods=['POST'])
def api_upload_achievement_certificate(achievement_id):
    """Upload summit / trek certificate file (PDF or Image)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    if 'certificate' not in request.files:
        return jsonify({'error': 'No file was submitted'}), 400
        
    file = request.files['certificate']
    if not file or file.filename == '':
        return jsonify({'error': 'No certificate file selected'}), 400
        
    orig_name = file.filename
    ext = os.path.splitext(orig_name)[1].lower()
    allowed_exts = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.svg']
    if ext not in allowed_exts:
        return jsonify({'error': 'Please upload a PDF, JPG, or PNG certificate.'}), 400
        
    safe_filename = f"cert_{user_id}_{achievement_id}_{int(datetime.now().timestamp())}{ext}"
    filepath = os.path.join(UPLOAD_CERT_FOLDER, safe_filename)
    file.save(filepath)
    
    cert_url = f"/static/uploads/certificates/{safe_filename}"
    database.update_achievement_certificate(achievement_id, user_id, cert_url, orig_name)
    raw = database.get_user_achievements(user_id)
    achievements = [enrich_achievement(a) for a in raw]
    return jsonify({
        'success': True,
        'certificate_url': cert_url,
        'certificate_name': orig_name,
        'achievements': achievements
    })

# ==========================================
# AI Chatbot Assistant Endpoint
# ==========================================
def find_matched_treks_for_query(msg_lower):
    alias_dict = {
        'ebc': 'everest-base-camp',
        'kgl': 'kashmir-great-lakes',
        'vof': 'valley-of-flowers',
        'kili': 'mount-kilimanjaro',
        'kilimanjaro': 'mount-kilimanjaro',
        'tmb': 'tour-du-mont-blanc',
        'mont blanc': 'tour-du-mont-blanc',
        'machu picchu': 'inca-trail',
        'friendship': 'friendship-peak',
        'friendship peak': 'friendship-peak',
        'yunam': 'yunam-peak',
        'yunam peak': 'yunam-peak',
        'kang yatse 1': 'kang-yatse-1',
        'kang yatse i': 'kang-yatse-1',
        'ky1': 'kang-yatse-1',
        'ky 1': 'kang-yatse-1',
        'ky i': 'kang-yatse-1',
        'kang yatse 2': 'kang-yatse-2',
        'kang yatse ii': 'kang-yatse-2',
        'ky2': 'kang-yatse-2',
        'ky 2': 'kang-yatse-2',
        'ky ii': 'kang-yatse-2',
        'stok': 'stok-kangri',
        'stok kangri': 'stok-kangri',
        'pangarchulla': 'pangarchulla-peak',
        'pangarchulla peak': 'pangarchulla-peak',
        'mera': 'mera-peak',
        'mera peak': 'mera-peak',
        'island': 'island-peak',
        'island peak': 'island-peak',
        'imja tse': 'island-peak'
    }
    
    matched = []
    
    # Check aliases
    for alias, trek_id in alias_dict.items():
        if alias in msg_lower:
            t = next((item for item in treks_data.TREKS_DATA if item['id'] == trek_id), None)
            if t and t not in matched:
                matched.append(t)
                
    # Check each trek
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

@app.route('/api/chat', methods=['POST'])
@app.route('/api/chatbot', methods=['POST'])
def api_chat():
    """
    Secure Google Gemini AI endpoint (POST /api/chat or POST /api/chatbot).
    Accepts user message and multi-turn conversation memory history.
    """
    data = request.get_json() or {}
    user_msg = (data.get('message') or data.get('prompt') or '').strip()
    history = data.get('history') or []
    
    if not user_msg:
        return jsonify({
            'success': True,
            'reply': "Namaste! 🏔️ I am **Sherpa AI**, powered by Google Gemini. Ask me anything about Himalayan trails, gear essentials, difficulty, safety, or budgets!",
            'suggestions': ["Compare Kedarkantha vs Brahmatal", "Best beginner treks under ₹10k", "Top winter snow treks", "How to prevent AMS?"]
        })

    try:
        response_data = gemini_service.generate_chat_response(user_msg, history=history)
        return jsonify(response_data)
    except Exception as e:
        print(f"Error handling Gemini chat request: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'reply': "I encountered an issue connecting to the mountain basecamp. Please try again in a moment.",
            'suggestions': ["Best beginner treks", "Top winter snow treks", "How to prevent AMS?"]
        }), 500

if __name__ == '__main__':
    print("Starting Auth & Treks Server on http://0.0.0.0:5000 (Local: http://127.0.0.1:5000) ...")
    app.run(host='0.0.0.0', port=5000, debug=True)



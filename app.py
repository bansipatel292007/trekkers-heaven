import os
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import database
import treks_data

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
        ach_copy['duration_text'] = ach_copy.get('distance', '')
        ach_copy['distance_text'] = ach_copy.get('distance', '')
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
    achievements = database.get_user_achievements(user_id)
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
    achievements = database.get_user_achievements(user_id)
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

@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    data = request.get_json() or {}
    user_msg = (data.get('message') or '').strip()
    msg_lower = user_msg.lower()
    
    if not user_msg:
        return jsonify({
            'reply': "Namaste! 👋 I am **Sherpa AI**, your personal mountain guide for Trekkers Heaven. Ask me about trek recommendations, comparisons, mountain passes, altitude sickness (AMS), packing essentials, or budgets!",
            'suggestions': ["Compare Kedarkantha vs Brahmatal", "Best beginner treks?", "Packing essentials", "Prevent altitude sickness"]
        })

    matched_treks = find_matched_treks_for_query(msg_lower)
    is_compare_intent = any(k in msg_lower for k in ['compare', 'vs', 'versus', 'difference', 'better', 'which one', 'antar', 'tulna', 'dono', 'kon sa'])

    # 1. Comparison between 2 or more treks
    if len(matched_treks) >= 2 or (is_compare_intent and len(matched_treks) >= 2):
        t1 = matched_treks[0]
        t2 = matched_treks[1]
        
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
            f"• Choose **{t1['name']}** if you want: *{t1['tagline']}*.\n"
            f"• Choose **{t2['name']}** if you want: *{t2['tagline']}*."
        )
        return jsonify({
            'reply': reply,
            'compare_treks': [
                {'id': t1['id'], 'name': t1['name']},
                {'id': t2['id'], 'name': t2['name']}
            ],
            'suggestions': [
                f"Show itinerary for {t1['name']}",
                f"Show itinerary for {t2['name']}",
                "Compare other treks"
            ]
        })

    # 2. Comparison asked generally or with only 1 trek
    if is_compare_intent:
        if len(matched_treks) == 1:
            t = matched_treks[0]
            other = next((item for item in treks_data.TREKS_DATA if item['id'] != t['id'] and (item['region'] == t['region'] or item['difficulty_slug'] == t['difficulty_slug'])), treks_data.TREKS_DATA[0])
            return jsonify({
                'reply': (
                    f"I can compare **{t['name']}** with any other trek! For example, would you like to compare **{t['name']} vs {other['name']}**?\n\n"
                    f"Type something like: *'Compare {t['name']} vs Brahmatal'* or *'Compare {t['name']} vs Kuari Pass'*."
                ),
                'suggestions': [
                    f"Compare {t['name']} vs {other['name']}",
                    f"Compare {t['name']} vs Brahmatal",
                    f"Compare {t['name']} vs Kuari Pass"
                ]
            })
        else:
            return jsonify({
                'reply': (
                    "⚖️ **Trek Comparison Feature:**\n\n"
                    "I can compare any 2 Himalayan or global treks side-by-side on **altitude, difficulty, duration, cost, best season, and scenic highlights**!\n\n"
                    "**Popular Comparisons to Try:**\n"
                    "• *Kedarkantha vs Brahmatal* (Winter Summits)\n"
                    "• *Hampta Pass vs Kashmir Great Lakes* (Green Valleys vs Alpine Lakes)\n"
                    "• *Rupin Pass vs Bali Pass* (Epic High Crossovers)\n"
                    "• *Everest Base Camp vs Annapurna Circuit* (Nepal Giants)"
                ),
                'suggestions': [
                    "Compare Kedarkantha vs Brahmatal",
                    "Compare Hampta Pass vs Kashmir Great Lakes",
                    "Compare Rupin Pass vs Bali Pass",
                    "Compare EBC vs Annapurna Circuit"
                ]
            })

    # 3. Single Specific Trek Details
    if len(matched_treks) == 1:
        t = matched_treks[0]
        t_clean_name = t['name'].replace(' Trek', '').replace(' Pass', '').strip()
        highlights_list = " • " + "\n • ".join(t.get('highlights', []))
        reply = (
            f"🏔️ **{t['name']}** ({t.get('region')}, {t.get('country')})\n\n"
            f"✨ *{t.get('tagline')}*\n\n"
            f"• **Max Altitude:** {t.get('max_altitude_text')}\n"
            f"• **Duration:** {t.get('duration_text')} ({t.get('distance_text')})\n"
            f"• **Difficulty:** {t.get('difficulty')} ({t.get('fitness_level')})\n"
            f"• **Best Season:** {t.get('best_season')}\n"
            f"• **Price:** {t.get('price')} (Rating: ⭐ {t.get('rating')})\n\n"
            f"📌 **Key Highlights:**\n{highlights_list}\n\n"
            f"💡 *{t.get('description')}*"
        )
        return jsonify({
            'reply': reply,
            'trek_id': t['id'],
            'trek_name': t['name'],
            'suggestions': [f"Show itinerary for {t_clean_name}", f"Compare {t['name']} with another trek", "Packing list for this trek"]
        })
            
    # 2. Greetings
    if any(w in msg_lower for w in ['hello', 'hi', 'hey', 'namaste', 'kem cho', 'salaam', 'yo', 'sup']):
        return jsonify({
            'reply': "Namaste! 🏔️ Welcome to **Trekkers Heaven**. I'm **Sherpa AI**, your personal AI trek guide. I can help you choose the best trail, prepare your gear, plan your budget, or give safety tips. What would you like to explore today?",
            'suggestions': ["Best beginner treks?", "Treks under ₹10,000", "Top winter snow treks", "How to prevent AMS?"]
        })

    # 3. Altitude Sickness / AMS / Acclimatization
    if any(w in msg_lower for w in ['ams', 'altitude', 'sickness', 'headache', 'diamox', 'acclimatization', 'oxygen', 'high altitude']):
        reply = (
            "⚠️ **Acute Mountain Sickness (AMS) Prevention Guide:**\n\n"
            "1. 💧 **Hydration is Key:** Drink 4 to 5 liters of water daily. Add ORS or electrolytes.\n"
            "2. 🧗 **Ascend Gradually:** Do not increase your sleeping altitude by more than 1,000–1,500 ft per day above 9,000 ft.\n"
            "3. 🏔️ **Climb High, Sleep Low:** Go for an evening acclimatization walk to higher ground, then sleep lower.\n"
            "4. 🚫 **Avoid Alcohol & Smoking:** Both increase dehydration and reduce oxygen uptake.\n"
            "5. 💊 **Diamox (Acetazolamide):** Consult a doctor before taking 125mg–250mg twice daily as a preventive measure.\n"
            "6. 🛑 **Golden Rule:** If you experience severe headache, nausea, dizziness, or loss of appetite, inform your trek leader and **never ascend with symptoms**."
        )
        return jsonify({
            'reply': reply,
            'suggestions': ["Essential gear list", "Easy beginner treks", "High mountain pass treks"]
        })

    # 4. Packing / Gear / Essentials
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
        return jsonify({
            'reply': reply,
            'suggestions': ["Best winter snow treks", "Treks under ₹10,000", "Physical fitness routine"]
        })

    # 5. Beginner / Easy Treks
    if any(w in msg_lower for w in ['beginner', 'easy', 'first time', 'starter', 'novice', 'newbie', 'pehla', 'simple']):
        easy_treks = [t for t in treks_data.TREKS_DATA if t.get('difficulty_slug') == 'easy']
        lines = []
        for t in easy_treks[:5]:
            lines.append(f"• **{t['name']}** ({t['region']}) - {t['max_altitude_text']} | {t['duration_text']} | {t['price']}")
        
        reply = (
            "🌟 **Top Recommended Beginner Treks:**\n\n"
            + "\n".join(lines) +
            "\n\n💡 *These treks feature gradual ascents, well-defined forest trails, and comfortable campsites with breathtaking Himalayan views!*"
        )
        return jsonify({
            'reply': reply,
            'suggestions': ["Tell me about Kedarkantha", "Tell me about Brahmatal", "Packing list for beginners"]
        })

    # 6. Budget / Price queries
    if any(w in msg_lower for w in ['budget', 'cheap', 'price', 'cost', 'under 10000', 'under 10k', '10,000', 'inexpensive', 'affordable', 'low cost']):
        budget_treks = [t for t in treks_data.TREKS_DATA if int(re.sub(r'[^\d]', '', t.get('price', '0')) or 0) <= 12000]
        lines = []
        for t in budget_treks[:5]:
            lines.append(f"• **{t['name']}** - **{t['price']}** ({t['duration_text']} in {t['region']})")
            
        reply = (
            "💰 **Best Budget Himalayan Treks Under ₹12,000:**\n\n"
            + "\n".join(lines) +
            "\n\n💡 *All include guide fees, forest permits, camping tents, and high-altitude meals!*"
        )
        return jsonify({
            'reply': reply,
            'suggestions': ["Tell me about Bhrigu Lake", "Tell me about Kedarkantha", "Tell me about Har Ki Dun"]
        })

    # 7. Winter / Snow Treks
    if any(w in msg_lower for w in ['winter', 'snow', 'barf', 'december', 'january', 'february', 'thand', 'frozen', 'ice']):
        winter_treks = [t for t in treks_data.TREKS_DATA if any(m in ['December', 'January', 'February'] for m in t.get('best_months', []))]
        lines = []
        for t in winter_treks[:5]:
            lines.append(f"• **{t['name']}** ({t['region']}) - {t['max_altitude_text']} | {t['price']}")
            
        reply = (
            "❄️ **Spectacular Winter Snow Treks:**\n\n"
            + "\n".join(lines) +
            "\n\n💡 *Expect deep snow, frozen alpine lakes (like Juda Ka Talab & Brahmatal), and crystalline summit views!*"
        )
        return jsonify({
            'reply': reply,
            'suggestions': ["Tell me about Chadar Trek", "Tell me about Kedarkantha", "Winter packing essentials"]
        })

    # 8. Difficult / High Pass / Expert Treks
    if any(w in msg_lower for w in ['difficult', 'hard', 'extreme', 'expert', 'challenging', 'crossover', 'pass', 'high altitude', 'tough']):
        diff_treks = [t for t in treks_data.TREKS_DATA if t.get('difficulty_slug') in ['difficult', 'expert']]
        lines = []
        for t in diff_treks[:5]:
            lines.append(f"• **{t['name']}** ({t['region']}) - {t['max_altitude_text']} | {t['price']}")
            
        reply = (
            "⚡ **Top Challenging & High-Pass Crossover Expeditions:**\n\n"
            + "\n".join(lines) +
            "\n\n🧗 *Requires strong physical stamina, cold tolerance, and mountain endurance!*"
        )
        return jsonify({
            'reply': reply,
            'suggestions': ["Tell me about Pin Parvati Pass", "Tell me about Rupin Pass", "Tell me about Goechala"]
        })

    # 9. Fitness / Training
    if any(w in msg_lower for w in ['fitness', 'workout', 'train', 'exercise', 'gym', 'preparation', 'running', 'stamina']):
        reply = (
            "🏃 **Himalayan Trek Fitness Plan (Start 4-6 weeks before trek):**\n\n"
            "1. 🫁 **Cardio Endurance:** Jog 5 km in under 30 minutes, 4 days a week (builds aerobic capacity).\n"
            "2. 🪜 **Stair Climbing:** Climb 30-40 flights of stairs wearing a 5-8 kg backpack twice a week.\n"
            "3. 🦵 **Leg Strength:** 3 sets of 20 squats, lunges, and calf raises.\n"
            "4. 🧘 **Core & Flexibility:** 60-second planks, hamstring and calf stretches to prevent cramps and knee stress.\n"
            "5. 👟 **Shoe Break-in:** Wear your trekking shoes on 3-4 long walks before the trek to avoid blisters."
        )
        return jsonify({
            'reply': reply,
            'suggestions': ["AMS prevention guide", "Packing essentials", "Beginner treks"]
        })

    # 10. General / Region Search
    for reg in ['uttarakhand', 'himachal', 'kashmir', 'ladakh', 'sikkim', 'nepal', 'peru', 'tanzania']:
        if reg in msg_lower:
            reg_treks = [t for t in treks_data.TREKS_DATA if reg in t.get('region', '').lower() or reg in t.get('country', '').lower()]
            if reg_treks:
                lines = [f"• **{t['name']}** - {t['max_altitude_text']} | {t['price']} ({t['difficulty']})" for t in reg_treks]
                reply = (
                    f"🗺️ **Treks in {reg.capitalize()}:**\n\n"
                    + "\n".join(lines) +
                    f"\n\nWhich of these would you like to know more about?"
                )
                return jsonify({
                    'reply': reply,
                    'suggestions': [f"Tell me about {reg_treks[0]['name']}", "Best season for this region", "Packing checklist"]
                })

    # 11. Default fallback helpful AI answer
    return jsonify({
        'reply': (
            f"I'm here to help you plan your next mountain adventure on **Trekkers Heaven**!\n\n"
            f"You can ask me questions like:\n"
            f"• *'Tell me about Kedarkantha or Rupin Pass'*\n"
            f"• *'What are the best winter snow treks?'*\n"
            f"• *'How to prevent AMS (altitude sickness)?'*\n"
            f"• *'Which treks are under ₹10,000?'*\n"
            f"• *'What gear should I pack?'*"
        ),
        'suggestions': ["Best beginner treks", "Snow treks", "AMS Prevention", "Packing Checklist"]
    })

if __name__ == '__main__':
    print("Starting Auth & Treks Server on http://0.0.0.0:5000 (Local: http://127.0.0.1:5000) ...")
    app.run(host='0.0.0.0', port=5000, debug=True)

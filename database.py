import sqlite3, os, shutil
from datetime import datetime, timezone

if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/users.db'
    seed_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')
    if not os.path.exists(DB_PATH) and os.path.exists(seed_db):
        try:
            shutil.copy2(seed_db, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

def db_query(query: str, params: tuple = (), fetchone: bool = False, commit: bool = False):
    """Execute SQL query with automatic connection lifecycle."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
        return cur.fetchone() if fetchone else cur

def init_db():
    """Initialize users and achievements tables."""
    db_query('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_login TEXT,
        phone TEXT,
        emergency_contact TEXT,
        blood_group TEXT,
        location TEXT,
        experience_level TEXT,
        bio TEXT,
        preferred_season TEXT
    )''', commit=True)

    db_query('''CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        trek_id TEXT,
        trek_name TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        altitude TEXT,
        altitude_ft INTEGER DEFAULT 0,
        distance TEXT,
        difficulty TEXT,
        location TEXT,
        image_url TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )''', commit=True)

    # Migrations for existing databases
    existing_cols = [row[1] for row in db_query("PRAGMA table_info(users)").fetchall()]
    new_cols = [
        ('phone', 'TEXT'),
        ('emergency_contact', 'TEXT'),
        ('blood_group', 'TEXT'),
        ('location', 'TEXT'),
        ('experience_level', 'TEXT'),
        ('bio', 'TEXT'),
        ('preferred_season', 'TEXT'),
        ('birthdate', 'TEXT'),
        ('age', 'TEXT'),
        ('city', 'TEXT'),
        ('state', 'TEXT'),
        ('country', 'TEXT')
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            try:
                db_query(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}", commit=True)
            except Exception:
                pass

    # Migrations for user_achievements table (certificates)
    existing_ach_cols = [row[1] for row in db_query("PRAGMA table_info(user_achievements)").fetchall()]
    for col_name, col_type in [('certificate_url', 'TEXT'), ('certificate_name', 'TEXT')]:
        if col_name not in existing_ach_cols:
            try:
                db_query(f"ALTER TABLE user_achievements ADD COLUMN {col_name} {col_type}", commit=True)
            except Exception:
                pass

def create_user(name: str, email: str, password_hash: str):
    """Create a new user record."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    try:
        cur = db_query(
            'INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
            (name.strip(), email.strip().lower(), password_hash, now),
            commit=True
        )
        return {'success': True, 'user_id': cur.lastrowid}
    except sqlite3.IntegrityError:
        return {'success': False, 'error': 'An account with this email address already exists.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_user_by_email(email: str):
    """Fetch user by email."""
    row = db_query('SELECT * FROM users WHERE email = ?', (email.strip().lower(),), fetchone=True)
    return dict(row) if row else None

def get_user_by_id(user_id: int):
    """Fetch user by id."""
    row = db_query('SELECT * FROM users WHERE id = ?', (user_id,), fetchone=True)
    return dict(row) if row else None

def update_last_login(user_id: int):
    """Update user last login timestamp."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    db_query('UPDATE users SET last_login = ? WHERE id = ?', (now, user_id), commit=True)

def update_user_profile(user_id: int, data: dict):
    """Update user profile information."""
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    birthdate = data.get('birthdate', '').strip()
    age = data.get('age', '').strip()
    city = data.get('city', '').strip()
    state = data.get('state', '').strip()
    country = data.get('country', '').strip()

    # Calculate age from birthdate if age is not explicitly given or auto-fill
    if birthdate and not age:
        try:
            bdate = datetime.strptime(birthdate, '%Y-%m-%d')
            today = datetime.now()
            calc_age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
            age = str(calc_age)
        except Exception:
            pass

    try:
        db_query('''UPDATE users SET 
            name = COALESCE(NULLIF(?, ''), name),
            phone = ?,
            birthdate = ?,
            age = ?,
            city = ?,
            state = ?,
            country = ?
            WHERE id = ?''',
            (name, phone, birthdate, age, city, state, country, user_id),
            commit=True
        )
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def update_user_password(user_id: int, new_password_hash: str):
    """Update user password hash."""
    try:
        db_query('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id), commit=True)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_user_achievements(user_id: int):
    """Fetch all completed treks for a user sorted by date descending."""
    rows = db_query('SELECT * FROM user_achievements WHERE user_id = ? ORDER BY COALESCE(start_date, created_at) DESC, id DESC', (user_id,))
    return [dict(r) for r in rows.fetchall()]

def add_user_achievement(user_id: int, trek_data: dict):
    """Add a completed trek to user achievements."""
    import re
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    trek_id = trek_data.get('trek_id', '')
    trek_name = trek_data.get('trek_name', '').strip()
    start_date = trek_data.get('start_date', '').strip()
    end_date = trek_data.get('end_date', '').strip()
    altitude = trek_data.get('altitude', '').strip()
    altitude_ft = trek_data.get('altitude_ft', 0)
    distance = trek_data.get('distance', '').strip()
    difficulty = trek_data.get('difficulty', '').strip()
    location = trek_data.get('location', '').strip()
    image_url = trek_data.get('image_url', '').strip()

    if not altitude_ft and altitude:
        m = re.search(r'([\d,]+)\s*ft', altitude)
        if m:
            try:
                altitude_ft = int(m.group(1).replace(',', ''))
            except Exception:
                pass

    try:
        cur = db_query('''INSERT INTO user_achievements (
            user_id, trek_id, trek_name, start_date, end_date, altitude, altitude_ft, distance, difficulty, location, image_url, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, trek_id, trek_name, start_date, end_date, altitude, altitude_ft, distance, difficulty, location, image_url, now),
        commit=True)
        return {'success': True, 'achievement_id': cur.lastrowid}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def delete_user_achievement(achievement_id: int, user_id: int):
    """Delete an achievement entry for a specific user."""
    try:
        db_query('DELETE FROM user_achievements WHERE id = ? AND user_id = ?', (achievement_id, user_id), commit=True)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def update_achievement_certificate(achievement_id: int, user_id: int, cert_url: str, cert_name: str):
    """Update certificate URL and original filename for a user achievement."""
    try:
        db_query('UPDATE user_achievements SET certificate_url = ?, certificate_name = ? WHERE id = ? AND user_id = ?',
                 (cert_url, cert_name, achievement_id, user_id), commit=True)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


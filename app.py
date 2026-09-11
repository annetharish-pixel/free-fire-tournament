import os
import re
import uuid
from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import db

app = Flask(__name__)
app.secret_key = 'super_secret_esports_tournament_key_2026'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'payments')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ensure database tables exist
with app.app_context():
    db.init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_admin_authenticated():
    return session.get('admin_logged_in', False)

# -------------------------------------------------------------
# PAGE ROUTES
# -------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/payments/<filename>')
def serve_payment_screenshot(filename):
    # Public or admin can view payment screenshot proof
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -------------------------------------------------------------
# PUBLIC API ENDPOINTS
# -------------------------------------------------------------

@app.route('/api/tournament-info', methods=['GET'])
def get_tournament_info():
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tournament_info WHERE id = 1")
    info = dict(cursor.fetchone())

    cursor.execute("SELECT COUNT(*) FROM teams")
    info['registered_teams'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM teams WHERE registration_status = 'Confirmed'")
    info['confirmed_teams'] = cursor.fetchone()[0]

    conn.close()
    return jsonify({'success': True, 'data': info})

@app.route('/api/register', methods=['POST'])
def register_team():
    try:
        # Check tournament status and max squad limit
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, max_teams FROM tournament_info WHERE id = 1")
        t_info = cursor.fetchone()
        t_status = t_info['status']
        max_teams = t_info['max_teams']

        if t_status != 'Open':
            conn.close()
            return jsonify({'success': False, 'message': 'Registration is currently closed by the organizer.'}), 400

        cursor.execute("SELECT COUNT(*) FROM teams")
        registered_count = cursor.fetchone()[0]
        if registered_count >= max_teams:
            conn.close()
            return jsonify({'success': False, 'message': f'Registration is full! Maximum squad limit of {max_teams} reached.'}), 400

        # Extract Form Fields
        team_name = request.form.get('team_name', '').strip()
        leader_name = request.form.get('leader_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        transaction_id = request.form.get('transaction_id', '').strip()

        # Extract 4 Players
        players_data = []
        for i in range(1, 5):
            p_name = request.form.get(f'player_{i}_name', '').strip()
            p_uid = request.form.get(f'player_{i}_uid', '').strip()
            p_ign = request.form.get(f'player_{i}_ign', '').strip() or p_name
            players_data.append({
                'number': i,
                'name': p_name,
                'uid': p_uid,
                'ign': p_ign
            })

        # --- VALIDATIONS ---
        # 1. Mandatory Fields
        if not team_name or not leader_name or not mobile or not email or not transaction_id:
            conn.close()
            return jsonify({'success': False, 'message': 'All team & payment details are required.'}), 400

        # 2. Validate all 4 players
        for p in players_data:
            if not p['name'] or not p['uid']:
                conn.close()
                return jsonify({'success': False, 'message': f'Please enter valid details for Player {p["number"]}. All 4 players are mandatory.'}), 400

        # 3. Email & Phone validation
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            conn.close()
            return jsonify({'success': False, 'message': 'Please enter a valid email address.'}), 400

        clean_mobile = re.sub(r'\D', '', mobile)
        if len(clean_mobile) < 10 or len(clean_mobile) > 13:
            conn.close()
            return jsonify({'success': False, 'message': 'Please enter a valid 10-digit mobile number.'}), 400

        # 4. Duplicate Team Name Check
        if db.is_team_name_taken(team_name):
            conn.close()
            return jsonify({'success': False, 'message': f'Team Name "{team_name}" is already registered. Please choose another name.'}), 400

        # 5. Internal UID Uniqueness Check (among 4 players in submission)
        submitted_uids = [p['uid'] for p in players_data]
        if len(set(submitted_uids)) < 4:
            conn.close()
            return jsonify({'success': False, 'message': 'Duplicate Free Fire UIDs found among your 4 players.'}), 400

        # 6. External DB UID Uniqueness Check
        existing_uids = db.check_duplicate_uids(submitted_uids)
        if existing_uids:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'The following Free Fire UID(s) are already registered with another team: {", ".join(existing_uids)}'
            }), 400

        # 7. Payment Screenshot Validation
        if 'payment_screenshot' not in request.files:
            conn.close()
            return jsonify({'success': False, 'message': 'Payment screenshot proof is required.'}), 400

        file = request.files['payment_screenshot']
        if file.filename == '' or not allowed_file(file.filename):
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid file format. Please upload JPG, PNG, or WEBP screenshot.'}), 400

        # Generate Unique Team ID (e.g. FFSB0001)
        team_id = db.generate_team_id()

        # Save Screenshot File
        ext = file.filename.rsplit('.', 1)[1].lower()
        saved_filename = f"{team_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)

        # Save Team to DB
        cursor.execute('''
            INSERT INTO teams (team_id, team_name, leader_name, mobile, email, registration_status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        ''', (team_id, team_name, leader_name, mobile, email))

        # Save Players to DB
        for p in players_data:
            cursor.execute('''
                INSERT INTO players (team_id, player_number, player_name, free_fire_uid, in_game_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (team_id, p['number'], p['name'], p['uid'], p['ign']))

        # Save Payment Record
        cursor.execute('''
            INSERT INTO payments (team_id, amount, transaction_id, payment_screenshot, payment_status)
            VALUES (?, 200.0, ?, ?, 'Pending')
        ''', (team_id, transaction_id, saved_filename))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Registration submitted successfully!',
            'data': {
                'team_id': team_id,
                'team_name': team_name,
                'registration_status': 'Pending',
                'payment_status': 'Pending Verification',
                'amount': 200
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server Error during registration: {str(e)}'}), 500

@app.route('/api/track/<team_id>', methods=['GET'])
def track_team(team_id):
    conn = db.get_db_connection()
    cursor = conn.cursor()

    formatted_id = team_id.strip().upper()
    cursor.execute("SELECT * FROM teams WHERE UPPER(team_id) = ? OR LOWER(team_name) = LOWER(?)", (formatted_id, team_id.strip()))
    team = cursor.fetchone()

    if not team:
        conn.close()
        return jsonify({'success': False, 'message': 'No registered team found with this Team ID or Team Name.'}), 404

    team_data = dict(team)

    cursor.execute("SELECT * FROM players WHERE team_id = ? ORDER BY player_number ASC", (team_data['team_id'],))
    players = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM payments WHERE team_id = ?", (team_data['team_id'],))
    payment_row = cursor.fetchone()
    payment_data = dict(payment_row) if payment_row else {}

    conn.close()

    return jsonify({
        'success': True,
        'data': {
            'team': team_data,
            'players': players,
            'payment': payment_data
        }
    })

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leaderboard ORDER BY rank ASC, points DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'data': rows})

# -------------------------------------------------------------
# ADMIN API ENDPOINTS
# -------------------------------------------------------------

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE username = ?", (username,))
    admin_row = cursor.fetchone()
    conn.close()

    if admin_row and check_password_hash(admin_row['password_hash'], password):
        session['admin_logged_in'] = True
        session['admin_username'] = username
        return jsonify({'success': True, 'message': 'Admin login successful.'})
    
    return jsonify({'success': False, 'message': 'Invalid admin username or password.'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return jsonify({'success': True, 'message': 'Logged out successfully.'})

@app.route('/api/admin/check-auth', methods=['GET'])
def check_auth():
    return jsonify({'authenticated': is_admin_authenticated(), 'username': session.get('admin_username', '')})

@app.route('/api/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM teams")
    total_teams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM teams WHERE registration_status = 'Confirmed'")
    confirmed_teams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM teams WHERE registration_status = 'Pending'")
    pending_teams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM teams WHERE registration_status = 'Rejected'")
    rejected_teams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM players")
    total_players = cursor.fetchone()[0]

    # Calculate total fee collected (₹200 per team submitted/confirmed)
    cursor.execute("SELECT SUM(amount) FROM payments WHERE payment_status = 'Approved'")
    total_collected = cursor.fetchone()[0] or 0.0

    conn.close()

    return jsonify({
        'success': True,
        'data': {
            'total_teams': total_teams,
            'confirmed_teams': confirmed_teams,
            'pending_teams': pending_teams,
            'rejected_teams': rejected_teams,
            'total_players': total_players,
            'total_collected': total_collected
        }
    })

@app.route('/api/admin/teams', methods=['GET'])
def admin_get_teams():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM teams ORDER BY created_at DESC")
    teams = [dict(t) for t in cursor.fetchall()]

    for t in teams:
        cursor.execute("SELECT * FROM players WHERE team_id = ? ORDER BY player_number ASC", (t['team_id'],))
        t['players'] = [dict(p) for p in cursor.fetchall()]

        cursor.execute("SELECT * FROM payments WHERE team_id = ?", (t['team_id'],))
        pay_row = cursor.fetchone()
        t['payment'] = dict(pay_row) if pay_row else {}

    conn.close()

    return jsonify({'success': True, 'data': teams})

@app.route('/api/admin/team/<team_id>/status', methods=['POST'])
def admin_update_team_status(team_id):
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    data = request.get_json() or {}
    new_status = data.get('status', '').strip()  # 'Confirmed' or 'Rejected' or 'Pending'

    if new_status not in ['Confirmed', 'Rejected', 'Pending']:
        return jsonify({'success': False, 'message': 'Invalid status option.'}), 400

    conn = db.get_db_connection()
    cursor = conn.cursor()

    payment_status = 'Approved' if new_status == 'Confirmed' else ('Rejected' if new_status == 'Rejected' else 'Pending')

    cursor.execute("UPDATE teams SET registration_status = ? WHERE team_id = ?", (new_status, team_id))
    cursor.execute("UPDATE payments SET payment_status = ? WHERE team_id = ?", (payment_status, team_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Team {team_id} status updated to {new_status}.'})

@app.route('/api/admin/team/<team_id>', methods=['DELETE'])
def admin_delete_team(team_id):
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    conn = db.get_db_connection()
    cursor = conn.cursor()

    # Get payment screenshot filename to delete file
    cursor.execute("SELECT payment_screenshot FROM payments WHERE team_id = ?", (team_id,))
    pay_row = cursor.fetchone()
    if pay_row and pay_row['payment_screenshot']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], pay_row['payment_screenshot'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    cursor.execute("DELETE FROM teams WHERE team_id = ?", (team_id,))
    cursor.execute("DELETE FROM players WHERE team_id = ?", (team_id,))
    cursor.execute("DELETE FROM payments WHERE team_id = ?", (team_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Team {team_id} deleted successfully.'})

@app.route('/api/admin/tournament-info', methods=['PUT'])
def admin_update_tournament_info():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    data = request.get_json() or {}
    name = data.get('name')
    game = data.get('game')
    fee = float(data.get('fee', 200))
    team_size = int(data.get('team_size', 4))
    reg_date = data.get('reg_date', '19/09/2026')
    date = data.get('date', '20/09/2026')
    time_str = data.get('time')
    max_teams = int(data.get('max_teams', 12))
    prize_pool = data.get('prize_pool')
    status = data.get('status')
    rules = data.get('rules')
    upi_id = data.get('upi_id')
    whatsapp = data.get('contact_whatsapp')
    email = data.get('contact_email')
    qr_code_url = data.get('qr_code_url')

    conn = db.get_db_connection()
    cursor = conn.cursor()
    if qr_code_url is not None:
        cursor.execute('''
            UPDATE tournament_info SET
                name = ?, game = ?, fee = ?, team_size = ?, reg_date = ?, date = ?, time = ?,
                max_teams = ?, prize_pool = ?, status = ?, rules = ?, upi_id = ?,
                contact_whatsapp = ?, contact_email = ?, qr_code_url = ?
            WHERE id = 1
        ''', (name, game, fee, team_size, reg_date, date, time_str, max_teams, prize_pool, status, rules, upi_id, whatsapp, email, qr_code_url))
    else:
        cursor.execute('''
            UPDATE tournament_info SET
                name = ?, game = ?, fee = ?, team_size = ?, reg_date = ?, date = ?, time = ?,
                max_teams = ?, prize_pool = ?, status = ?, rules = ?, upi_id = ?,
                contact_whatsapp = ?, contact_email = ?
            WHERE id = 1
        ''', (name, game, fee, team_size, reg_date, date, time_str, max_teams, prize_pool, status, rules, upi_id, whatsapp, email))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Tournament information updated successfully.'})

@app.route('/api/admin/upload-qr', methods=['POST'])
def admin_upload_qr():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401
    
    if 'qr_photo' not in request.files:
        return jsonify({'success': False, 'message': 'No image file uploaded.'}), 400
    
    file = request.files['qr_photo']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file format. Please upload PNG, JPG, JPEG, or WEBP image.'}), 400
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    saved_filename = f"qr_scanner_{uuid.uuid4().hex[:8]}.{ext}"
    qr_dir = os.path.join(app.root_path, 'static', 'uploads', 'qr')
    os.makedirs(qr_dir, exist_ok=True)
    filepath = os.path.join(qr_dir, saved_filename)
    file.save(filepath)
    
    qr_url = f"/static/uploads/qr/{saved_filename}"
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_info SET qr_code_url = ? WHERE id = 1", (qr_url,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Scanner QR image updated successfully!', 'qr_code_url': qr_url})

@app.route('/api/admin/reset-qr', methods=['POST'])
def admin_reset_qr():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_info SET qr_code_url = '' WHERE id = 1")
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Scanner QR reset to default.'})

@app.route('/api/admin/leaderboard', methods=['POST'])
def admin_save_leaderboard_entry():
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    data = request.get_json() or {}
    entry_id = data.get('id')
    rank = int(data.get('rank', 1))
    team_name = data.get('team_name', '').strip()
    points = int(data.get('points', 0))
    kills = int(data.get('kills', 0))
    booyahs = int(data.get('booyahs', 0))

    if not team_name:
        return jsonify({'success': False, 'message': 'Team name is required.'}), 400

    conn = db.get_db_connection()
    cursor = conn.cursor()

    if entry_id:
        cursor.execute('''
            UPDATE leaderboard SET rank = ?, team_name = ?, points = ?, kills = ?, booyahs = ?
            WHERE id = ?
        ''', (rank, team_name, points, kills, booyahs, entry_id))
    else:
        cursor.execute('''
            INSERT INTO leaderboard (rank, team_name, points, kills, booyahs)
            VALUES (?, ?, ?, ?, ?)
        ''', (rank, team_name, points, kills, booyahs))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Leaderboard entry saved successfully.'})

@app.route('/api/admin/leaderboard/<int:entry_id>', methods=['DELETE'])
def admin_delete_leaderboard_entry(entry_id):
    if not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401

    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leaderboard WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Leaderboard entry deleted.'})

if __name__ == '__main__':
    print("Starting Free Fire Squad Tournament Portal on http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)

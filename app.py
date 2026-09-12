import os
import re
import uuid
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import db

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'super_secret_esports_tournament_key_2026'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'payments')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB upload limit
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# SMTP Environment Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', os.getenv('EMAIL_USER', ''))
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', os.getenv('EMAIL_PASSWORD', os.getenv('APP_PASSWORD', '')))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', SMTP_USERNAME or 'support@ffsquadbattle.com')
SENDER_NAME = os.getenv('SENDER_NAME', 'Free Fire Squad Battle')

def send_registration_confirmation_email(team_id, team_name, leader_name, mobile, recipient_email, players_data, fee=200, status="Confirmed", tournament_name="Free Fire Squad Battle"):
    """
    Sends an automatic registration confirmation email to the team leader.
    Returns (success: bool, error_message: str).
    Does NOT affect database state if email delivery fails.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        err_msg = "SMTP credentials (SMTP_USERNAME / SMTP_PASSWORD) are not configured in environment variables."
        logger.warning(f"[EMAIL NOT SENT] {err_msg}")
        return False, err_msg

    try:
        current_time_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
        
        # Build HTML Email Body
        players_html = ""
        for p in players_data:
            players_html += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #2a2e3d; color: #e2e8f0; font-size: 14px;">Player {p['number']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #2a2e3d; color: #e2e8f0; font-size: 14px; font-weight: 600;">{p['name']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #2a2e3d; color: #ff9900; font-size: 14px; font-weight: 600;">{p['ign']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #2a2e3d; color: #94a3b8; font-size: 14px;">{p['uid']}</td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Registration Confirmed - {tournament_name}</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #0f111a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #e2e8f0;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f111a; padding: 30px 10px;">
                <tr>
                    <td align="center">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #171a29; border-radius: 12px; border: 1px solid #2e344e; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                            <!-- Header Banner -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #ff4655 0%, #ff9900 100%); padding: 25px; text-align: center;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">
                                        🎮 {tournament_name}
                                    </h1>
                                    <p style="margin: 5px 0 0 0; color: #ffffff; font-size: 14px; font-weight: 600; opacity: 0.95;">
                                        Official Registration Confirmation Receipt
                                    </p>
                                </td>
                            </tr>
                            <!-- Success Alert Badge -->
                            <tr>
                                <td style="padding: 20px 30px 10px 30px; text-align: center;">
                                    <div style="background-color: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; color: #4ade80; padding: 12px; border-radius: 8px; font-weight: 700; font-size: 15px; display: inline-block;">
                                        ✅ REGISTRATION CONFIRMED
                                    </div>
                                </td>
                            </tr>
                            <!-- Details Section -->
                            <tr>
                                <td style="padding: 20px 30px;">
                                    <p style="font-size: 15px; line-height: 1.6; color: #cbd5e1; margin-bottom: 20px;">
                                        Hello <strong style="color: #ffffff;">{leader_name}</strong>,<br>
                                        Your squad <strong style="color: #ff9900;">{team_name}</strong> has been successfully registered for <strong>{tournament_name}</strong>! Below are your official tournament registration details.
                                    </p>
                                    
                                    <!-- Summary Card -->
                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f111a; border-radius: 8px; border: 1px solid #262b3e; padding: 15px; margin-bottom: 25px;">
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px; width: 40%;">Tournament Name:</td>
                                            <td style="padding: 6px 0; color: #ffffff; font-size: 14px; font-weight: 700;">{tournament_name}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Team Name:</td>
                                            <td style="padding: 6px 0; color: #ff9900; font-size: 14px; font-weight: 700;">{team_name}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Team ID / Reg ID:</td>
                                            <td style="padding: 6px 0; color: #38bdf8; font-size: 14px; font-weight: 700; font-family: monospace;">{team_id}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Team Leader Name:</td>
                                            <td style="padding: 6px 0; color: #ffffff; font-size: 14px;">{leader_name}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Registered Email:</td>
                                            <td style="padding: 6px 0; color: #ffffff; font-size: 14px;">{recipient_email}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Mobile Number:</td>
                                            <td style="padding: 6px 0; color: #ffffff; font-size: 14px;">{mobile}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Registration Fee:</td>
                                            <td style="padding: 6px 0; color: #4ade80; font-size: 14px; font-weight: 700;">₹{fee}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Registration Status:</td>
                                            <td style="padding: 6px 0; color: #4ade80; font-size: 14px; font-weight: 700;">{status}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">Registration Date/Time:</td>
                                            <td style="padding: 6px 0; color: #cbd5e1; font-size: 13px;">{current_time_str}</td>
                                        </tr>
                                    </table>

                                    <!-- Squad Roster Table -->
                                    <h3 style="color: #ffffff; font-size: 16px; margin: 0 0 12px 0; border-bottom: 2px solid #ff4655; padding-bottom: 6px; display: inline-block;">
                                        🔥 Registered Squad Roster
                                    </h3>
                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; background-color: #0f111a; border-radius: 8px; overflow: hidden; border: 1px solid #262b3e;">
                                        <thead>
                                            <tr style="background-color: #1f2438;">
                                                <th style="padding: 10px 12px; text-align: left; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Role</th>
                                                <th style="padding: 10px 12px; text-align: left; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Player Name</th>
                                                <th style="padding: 10px 12px; text-align: left; color: #94a3b8; font-size: 12px; text-transform: uppercase;">In-Game Name (IGN)</th>
                                                <th style="padding: 10px 12px; text-align: left; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Free Fire UID</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {players_html}
                                        </tbody>
                                    </table>

                                    <div style="margin-top: 30px; padding: 15px; background-color: #121522; border-left: 4px solid #ff9900; border-radius: 4px;">
                                        <p style="margin: 0; font-size: 13px; color: #cbd5e1; line-height: 1.5;">
                                            <strong>📢 Next Steps:</strong> Keep your Team ID (<code>{team_id}</code>) handy. Room ID and password will be shared prior to tournament schedule.
                                        </p>
                                    </div>
                                </td>
                            </tr>
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #11131f; padding: 20px; text-align: center; border-top: 1px solid #262b3e;">
                                    <p style="margin: 0 0 6px 0; font-size: 13px; color: #94a3b8;">
                                        Good luck on the battlefield! May the Booyah be yours! 🏆
                                    </p>
                                    <p style="margin: 0; font-size: 11px; color: #64748b;">
                                        © 2026 {tournament_name}. All rights reserved.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        # Build Plain Text Fallback
        text_content = f"""
        🎮 {tournament_name} - Registration Confirmed
        ====================================================
        Hello {leader_name},

        Your squad '{team_name}' has been successfully registered!

        REGISTRATION DETAILS:
        - Tournament Name: {tournament_name}
        - Team Name: {team_name}
        - Team ID / Reg ID: {team_id}
        - Leader Name: {leader_name}
        - Registered Email: {recipient_email}
        - Mobile Number: {mobile}
        - Registration Fee: ₹{fee}
        - Registration Status: {status}
        - Date/Time: {current_time_str}

        SQUAD ROSTER:
        """
        for p in players_data:
            text_content += f"\n- Player {p['number']}: {p['name']} | IGN: {p['ign']} | UID: {p['uid']}"

        text_content += f"\n\nGood luck! Keep your Team ID ({team_id}) saved.\n\n© 2026 {tournament_name}"

        # Construct Email Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✅ Registration Confirmed: {team_name} ({team_id}) - {tournament_name}"
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Connect to SMTP Server
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            if SMTP_USE_TLS:
                server.starttls()

        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, [recipient_email], msg.as_string())
        server.quit()

        logger.info(f"[EMAIL SUCCESS] Confirmation email successfully sent to {recipient_email} for team {team_id}")
        return True, ""

    except Exception as e:
        err_msg = str(e)
        logger.error(f"[EMAIL ERROR] Failed to send confirmation email to {recipient_email} for team {team_id}: {err_msg}")
        return False, err_msg

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

        # Extract Leader Player Information
        players_data = []
        p1_name = request.form.get('player_1_name', '').strip() or leader_name
        p1_uid = request.form.get('player_1_uid', '').strip()
        p1_ign = request.form.get('player_1_ign', '').strip() or p1_name

        players_data.append({
            'number': 1,
            'name': p1_name,
            'uid': p1_uid,
            'ign': p1_ign
        })

        # --- VALIDATIONS ---
        # 1. Mandatory Fields
        if not team_name or not leader_name or not mobile or not email or not transaction_id:
            conn.close()
            return jsonify({'success': False, 'message': 'All team & payment details are required.'}), 400

        # 2. Validate Leader Player
        if not p1_name or not p1_uid:
            conn.close()
            return jsonify({'success': False, 'message': 'Please enter valid details for Leader Player (Name and Free Fire UID).'}), 400

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

        # 5. Internal UID Uniqueness Check
        submitted_uids = [p['uid'] for p in players_data if p['uid']]
        if len(set(submitted_uids)) < len(submitted_uids):
            conn.close()
            return jsonify({'success': False, 'message': 'Duplicate Free Fire UIDs found.'}), 400

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

        # Automatic Registration Confirmation Email
        email_sent, email_err = send_registration_confirmation_email(
            team_id=team_id,
            team_name=team_name,
            leader_name=leader_name,
            mobile=mobile,
            recipient_email=email,
            players_data=players_data,
            fee=200,
            status="Confirmed"
        )

        if email_sent:
            response_msg = "Registration successful! Confirmation email has been sent to your registered email."
        else:
            response_msg = "Registration successful! Confirmation email could not be sent to your registered email."

        return jsonify({
            'success': True,
            'email_sent': email_sent,
            'message': response_msg,
            'data': {
                'team_id': team_id,
                'team_name': team_name,
                'leader_name': leader_name,
                'email': email,
                'mobile': mobile,
                'registration_status': 'Confirmed',
                'payment_status': 'Submitted for Verification',
                'amount': 200,
                'email_sent': email_sent
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

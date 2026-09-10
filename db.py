import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Teams Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT UNIQUE NOT NULL,
            team_name TEXT UNIQUE NOT NULL,
            leader_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT NOT NULL,
            registration_status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Players Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            player_number INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            free_fire_uid TEXT NOT NULL,
            in_game_name TEXT NOT NULL,
            FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        )
    ''')

    # Payments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            amount REAL DEFAULT 200.0,
            transaction_id TEXT NOT NULL,
            payment_screenshot TEXT NOT NULL,
            payment_status TEXT DEFAULT 'Pending',
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        )
    ''')

    # Tournament Info Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_info (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT NOT NULL,
            game TEXT NOT NULL,
            fee REAL NOT NULL,
            team_size INTEGER NOT NULL,
            reg_date TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            max_teams INTEGER NOT NULL,
            prize_pool TEXT NOT NULL,
            status TEXT NOT NULL,
            rules TEXT NOT NULL,
            upi_id TEXT NOT NULL,
            contact_whatsapp TEXT NOT NULL,
            contact_email TEXT NOT NULL
        )
    ''')

    # Leaderboard Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rank INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0,
            booyahs INTEGER DEFAULT 0
        )
    ''')

    # Admin Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')

    # Seed Default Tournament Info if empty
    cursor.execute("SELECT COUNT(*) FROM tournament_info")
    if cursor.fetchone()[0] == 0:
        default_rules = "\n".join([
            "1. Each team must contain exactly 4 registered players.",
            "2. Registration fee is ₹200 per team and is non-refundable.",
            "3. Registration closes on 12/09/2026. Matches will be held on 13/09/2026.",
            "4. All players must provide their correct Free Fire UID and In-Game Name.",
            "5. One player cannot participate in multiple teams.",
            "6. Players must join the match custom room at the specified time.",
            "7. Any use of hacks, mods, or third-party tools will result in instant team disqualification.",
            "8. Payment transaction ID and screenshot proof must be verified before confirmation.",
            "9. The tournament organizer's decisions regarding disputes will be final."
        ])
        cursor.execute('''
            INSERT INTO tournament_info (id, name, game, fee, team_size, reg_date, date, time, max_teams, prize_pool, status, rules, upi_id, contact_whatsapp, contact_email)
            VALUES (1, 'Free Fire Squad Battle', 'Free Fire', 200.0, 4, '12/09/2026', '13/09/2026', 'To be announced', 12, '₹1,000 Total Pool', 'Open', ?, 'fftournament@upi', '+91 90525 96711', 'support@ffsquadbattle.com')
        ''', (default_rules,))

    # Seed Admin User if empty
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        default_hash = generate_password_hash('admin123')
        cursor.execute("INSERT INTO admin (username, password_hash) VALUES (?, ?)", ('admin', default_hash))

    # Seed sample teams if database is clean (for testing & immediate visualization)
    cursor.execute("SELECT COUNT(*) FROM teams")
    if cursor.fetchone()[0] == 0:
        # Sample Team 1 (Confirmed)
        cursor.execute('''
            INSERT INTO teams (team_id, team_name, leader_name, mobile, email, registration_status)
            VALUES ('FFSB0001', 'Fire Storm', 'Rahul Verma', '9876543210', 'rahul@example.com', 'Confirmed')
        ''')
        p1 = [
            ('FFSB0001', 1, 'Rahul Verma', '123456789', 'FS_Leader'),
            ('FFSB0001', 2, 'Amit Sharma', '234567890', 'FS_Sniper'),
            ('FFSB0001', 3, 'Vikas Kumar', '345678901', 'FS_Rusher'),
            ('FFSB0001', 4, 'Rohan Singh', '456789012', 'FS_Support')
        ]
        cursor.executemany("INSERT INTO players (team_id, player_number, player_name, free_fire_uid, in_game_name) VALUES (?, ?, ?, ?, ?)", p1)
        cursor.execute("INSERT INTO payments (team_id, amount, transaction_id, payment_screenshot, payment_status) VALUES ('FFSB0001', 200.0, 'UPI123456789012', 'sample_proof1.jpg', 'Approved')")

        # Sample Team 2 (Pending)
        cursor.execute('''
            INSERT INTO teams (team_id, team_name, leader_name, mobile, email, registration_status)
            VALUES ('FFSB0002', 'Warriors Esports', 'Arjun Patel', '9812345678', 'arjun@example.com', 'Pending')
        ''')
        p2 = [
            ('FFSB0002', 1, 'Arjun Patel', '567890123', 'WE_Arjun'),
            ('FFSB0002', 2, 'Suresh Reddy', '678901234', 'WE_Suresh'),
            ('FFSB0002', 3, 'Karan Malhotra', '789012345', 'WE_Karan'),
            ('FFSB0002', 4, 'Deepak Nair', '890123456', 'WE_Deepak')
        ]
        cursor.executemany("INSERT INTO players (team_id, player_number, player_name, free_fire_uid, in_game_name) VALUES (?, ?, ?, ?, ?)", p2)
        cursor.execute("INSERT INTO payments (team_id, amount, transaction_id, payment_screenshot, payment_status) VALUES ('FFSB0002', 200.0, 'UPI987654321098', 'sample_proof2.jpg', 'Pending')")

    conn.commit()
    conn.close()

def generate_team_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        next_num = row['id'] + 1
    else:
        next_num = 1
    return f"FFSB{next_num:04d}"

def is_team_name_taken(team_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM teams WHERE LOWER(team_name) = LOWER(?)", (team_name.strip(),))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def check_duplicate_uids(uids):
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(uids))
    cursor.execute(f"SELECT free_fire_uid FROM players WHERE free_fire_uid IN ({placeholders})", uids)
    rows = cursor.fetchall()
    conn.close()
    return [row['free_fire_uid'] for row in rows]

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")

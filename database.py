import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'securifi.db')

def start_connection():
	conn = sqlite3.connect(DB_PATH)
	# cu row factory il putem folosi si ca si dictionary, nu numai tuple
	conn.row_factory = sqlite3.Row
	return conn

def init_db():
	conn = start_connection()
	c = conn.cursor()

	# cam tot ce tine de info-ul dat de esp-uri
	# vedeti ca sql nu are bool, deci pt orice true / false trebuie transformat in int 1 / 0
	c.execute('''CREATE TABLE IF NOT EXISTS events (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		home_id TEXT,
		node_id TEXT,
		timestamp TEXT,
		movement INTEGER,
		state TEXT,
		warning_type TEXT
	)''')

	# ce tine de users
	c.execute('''CREATE TABLE IF NOT EXISTS fcm_tokens (
		user_id TEXT PRIMARY KEY,
		token TEXT
	)''')

	# ce tine de casa ta
	c.execute('''CREATE TABLE IF NOT EXISTS homes (
		home_id TEXT PRIMARY KEY,
		master_mac TEXT UNIQUE,
		owner_uid TEXT,
		armed INTEGER DEFAULT 0,
		registered_at TEXT
	)''')

	conn.commit()
	conn.close()
	print("Database ready :D")



# homes:
def get_or_create_home(master_mac: str) -> str:
	conn = start_connection()
	c = conn.cursor()

	row = c.execute("SELECT home_id FROM homes WHERE master_mac=?", (master_mac,)).fetchone()

	if row:
		home_id = row["home_id"]
	else:
		home_id = uuid.uuid4().hex[:8]
		c.execute("INSERT INTO homes (home_id, master_mac, armed, registered_at) VALUES (?, ?, 0, ?)", (home_id, master_mac, datetime.now().isoformat()))
		conn.commit()
		print(f"[DB]: New home registered: {home_id} (mac: {master_mac})")

	conn.close()
	return home_id


def claim_home(home_id: str, owner_uid: str):
	conn = start_connection()
	c = conn.cursor()
	
	c.execute("UPDATE homes SET owner_uid=? WHERE home_id=? AND owner_uid IS NULL", (owner_uid, home_id))
	conn.commit()
	conn.close()

def get_home_by_uid(owner_uid: str) -> dict | None:
	conn = start_connection()
	c = conn.cursor()

	row = c.execute("SELECT * FROM homes WHERE owner_uid=?", (owner_uid,)).fetchone()
	conn.close()

	if row:
		return dict(row)
	else:
		return None

def get_home_by_mac(master_mac: str) -> dict | None:
	conn = start_connection()
	c = conn.cursor()

	row = c.execute("SELECT * FROM homes WHERE master_mac=?", (master_mac,)).fetchone()
	conn.close()

	if row:
		return dict(row)
	else:
		return None


# arming / disarming:
def set_armed(home_id: str, armed: bool):
	conn = start_connection()
	c = conn.cursor()

	c.execute("UPDATE homes SET armed=? WHERE home_id=?", (int(armed), home_id))
	conn.commit()
	conn.close()

def get_armed(home_id: str) -> bool:
	conn = start_connection()
	c = conn.cursor()

	row = c.execute("SELECT armed FROM homes WHERE home_id=?", (home_id,)).fetchone()
	conn.close()

	if row:
		return bool(row["armed"])
	else:
		return False


# events:
def set_event(home_id: str, node_id: str, timestamp: str, movement: int, state: str, warning_type: str):
	conn = start_connection()
	c = conn.cursor()

	# la id e null ca sa nu il modificam sa ramana la fel
	c.execute("INSERT INTO events (home_id, node_id, timestamp, movement, state, warning_type) VALUES (?, ?, ?, ?, ?, ?)", (home_id, node_id, timestamp, movement, state, warning_type))
	conn.commit()
	conn.close()

def get_history(home_id: str, limit=100) -> list[dict]:
	conn = start_connection()
	c = conn.cursor()

	data = c.execute("SELECT * FROM events WHERE home_id=? ORDER BY timestamp DESC LIMIT ?", (home_id, limit)).fetchall()
	conn.close()

	# noi vrem de fapt o lista cu package-urile din history, care sunt dict ca e mai usor de lucrat cu ele decat cu tuple
	return [dict(d) for d in data]



# fcm:
def set_fcm_token(user_id: str, token: str):
	conn = start_connection()
	c = conn.cursor()

	c.execute("INSERT OR REPLACE INTO fcm_tokens (user_id, token) VALUES (?, ?)", (user_id, token))
	conn.commit()
	conn.close()

def get_fcm_token(user_id) -> str | None:
	conn = start_connection()
	c = conn.cursor()

	row = c.execute("SELECT token FROM fcm_tokens WHERE user_id=?", (user_id,)).fetchone()
	conn.close()

	if row:
		return row["token"]
	else:
		return None
import firebase_admin
from firebase_admin import credentials, firestore

from datetime import datetime
import uuid


# setup:
cred = credentials.Certificate('firebase.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

MIN_CACHE = 10 # cat de multe package-uri sunt necesare pt a da un verdict la cache analyse TODO
MAX_CACHE = 50 # cat de multe package-uri vrem sa salvam in cache TODO 
IDLE_CLOSE_COUNT = 30 # cate pachete idle vrem sa inchida o sesiune TODO

PACKAGE_PROBABILITY_THRESHOLD = 0.7 # TODO
PACKAGE_COUNT_THRESHOLD = 7 # TODO

print("[DB]: Firebase connected :D")


# users:
def create_user_profile(uid: str, email: str, phone: str):
    # firebase tine parola and shit, in firestore tinem minte profilul
    #in firestore se tin chiestiile neimportante like notif pref and shit
    db.collection("users").document(uid).set({
        "email": email,
        "phone": phone,
        "home_id": None,
        "fcm_token": None,
        "created_at": datetime.now().isoformat()
    }, merge=True) 

    print(f"[DB]: User profile created: {uid}")

def get_user(uid: str) -> dict | None:
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        return {
            "uid": uid,
            # **ceva.to_dict() - **ia fiecare key value pair si le baga ca si key pair in noul dict
            **doc.to_dict()
        }
    else:
        return None

def set_fcm_token(uid: str, token: str):
    db.collection("users").document(uid).update({"fcm_token": token})

def get_fcm_tokens(uid: str) -> str | None:
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        return doc.to_dict().get("fcm_token")
    else:
        return None
    

# onboarding:
def onboard_home(uid: str, master_mac: str) -> str:
    existing = db.collection("homes").where("master_mac", "==", master_mac).limit(1).get()
    if existing:
        home_id = existing[0].id
        db.collection("homes").document(home_id).update({"owner_uid": uid})
    else:
        home_id = uuid.uuid4().hex[:8]
        db.collection("homes").document(home_id).set({
            "master_mac": master_mac,
            "owner_uid": uid,
            "armed": False,
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        })

        print(f"[DB]: New home registered: {home_id} (mac: {master_mac})")

    db.collection("users").document(uid).update({"home_id": home_id})
    print(f"[DB]: Home {home_id} linked to user {uid}")
    return home_id


# homes:
def get_home_by_mac(master_mac: str) -> dict | None:
    docs = db.collection("homes").where("master_mac", "==", master_mac).limit(1).get()
    if docs:
        d = docs[0]
        return {
            "home_id": d.id,
            **d.to_dict()
        }
    else:
        return None

def get_home_by_uid(uid: str) -> dict | None:
    user = db.collection("users").document(uid).get()
    if not user.exists:
        return None

    home_id = user.to_dict().get("home_id")
    if not home_id:
        return None
    home = db.collection("homes").document(home_id).get()
    if home.exists:
        return {
            "home_id": home_id,
            **home.to_dict()
        }
    else:
        return None

def update_last_seen(home_id: str):
    db.collection("homes").document(home_id).update({"last_seen": datetime.now().isoformat()})
    

# (armed):
def set_armed(home_id: str, armed: bool):
    db.collection("homes").document(home_id).update({"armed": armed})

def get_armed(home_id: str) -> bool:
    doc = db.collection("homes").document(home_id).get()
    if doc.exists:
        return doc.to_dict().get("armed", False)
    else:
        return None



# cache:
def update_cache(home_id: str, package: dict) -> list:
    ref = db.collection("cache").document(home_id)
    doc = ref.get()

    if(doc.exists):
        packages = doc.to_dict().get("last_packages", [])
    else:
        packages = []
    packages.append(package)

    if len(packages) > MAX_CACHE:
        packages = packages[-MAX_CACHE:] # sterge primul element sau cate elemente trebuie de la inceput ca sa scape de overflow

    ref.set({"last_packages": packages})
    return packages

def get_cache(home_id: str) -> list:
    doc = db.collection("cache").document(home_id).get()
    if doc.exists:
        return doc.to_dict().get("last_packages", [])
    else:
        return []

# TODO de configurat incat sa dea return la feedback realist in functie de ultimele package-uri
def analyse_cache(packages: list) -> bool:
    # daca nu sunt suficiente, nu putem determina realist daca e sau nu
    if len(packages) < MIN_CACHE:
        return False

    recent = packages[-MIN_CACHE:]
    motion_count = 0
    for p in recent:
        if p.get("intruder_probability", 0) > PACKAGE_PROBABILITY_THRESHOLD:
            motion_count += 1

    return (motion_count >= PACKAGE_COUNT_THRESHOLD)


# session (adica un break in salvat):
def start_session(home_id: str, package: dict) -> str:
    session_id = uuid.uuid4().hex[:8]
    db.collection("events").document(home_id).collection("sessions").document(session_id).set({
        "started_at": datetime.now().isoformat(),
        "ended_at": None,
        "peak_probability": package.get("intruder_probability", 0),
        "trigger_package": package,
        "dismissed_by_user": False,
        "snapshot_pdf": None
    })

    print(f"[DB]: Session started: {session_id} for home: {home_id}")
    return session_id

def add_package_to_session(home_id: str, session_id: str, package: dict):
    db.collection("events").document(home_id).collection("sessions").document(session_id).collection("packages").add(package)

    session_ref = db.collection("events").document(home_id).collection("sessions").document(session_id)
    current = session_ref.get()

    if current.exists:
        current_peak = current.to_dict().get("peak_probability", 0)
        new_prob = package.get("intruder_probability", 0)

        if new_prob > current_peak:
            session_ref.update({"peak_probability": new_prob})

def close_session(home_id: str, session_id: str):
    db.collection("events").document(home_id).collection("sessions").document(session_id).update({"ended_at": datetime.now().isoformat()})

    print(f"[DB]: Session {session_id}, in home {home_id}, was closed")

# cand o opreste user-ul
def dismiss_session(home_id: str, session_id: str):
    db.collection("events").document(home_id).collection("sessions").document(session_id).update({
        "ended_at": datetime.now().isocalendar(),
        "dismissed_by_user": True
    })

    print(f"[DB]: Session {session_id}, in home {home_id}, was dismissed by the user")

# ca sa afisam lista de evenimente pe aplicatie
def get_sessions(home_id: str, limit: int = 20) -> list:
    docs = db.collection("events").document(home_id).collection("sessions").order_by("starting_at", direction=firestore.Query.DESCENDING).limit(limit).get()

    return_list = [None for i in range(limit)]
    for d in db:
        return_list.append({
            "session_id": d.id,
            **d.to_dict()
        })

    return return_list

def get_session_packages(home_id: str, session_id: str) -> list:
    docs = db.collection("events").document(home_id).collection("sessions").document(session_id).order_by("timestamp").get()

    return_list = [None for i in range(len(docs))]
    for d in docs:
        return_list.append(d.to__dict())

    return return_list

# ca user-ul sa salveze cache-ul curent ca si o sesiune care sa ramana
def save_snapshot(home_id: str, packages: list) -> str:
    session_id = uuid.uuid4().hex[:8]

    db.collection("events").document(home_id).collection("sessions").document(session_id).set({
        "started_at": packages[0].get("timestamp") if packages else datetime.now().isoformat(),
        "ended_at": datetime.now().isoformat(),
        "peak_probability": max((p.get("intruder_probability", 0) for p in packages), default=0),
        "trigger_package": None,
        "dismissed_by_user": False,
        "snapshot_pdf": None,
        "is_manual_snapshot": True
    })

    session_packages_ref = db.collection("events").document(home_id).collection("sessions").document(session_id).collection("packages")
    for pkg in packages:
        session_packages_ref.add(pkg)

    print(f"[DB]: Manual snapshot saved: {session_id} at the home {home_id}")
    return session_id
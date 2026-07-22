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
        home_id = uuid.uuid4.hex[:8]
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
            "home_id": home_id
            **home.to_dict()
        }
    else:
        None

def update_last_seen(home_id: str):
    db.collection("homes").document(home_id).update({"last_seen": datetime.now().isoformat()})
    

# (armed):
def set_armed(home_id: str, armed: bool):
    db.collection("homes").document(home_id).update({"armed": armed})

def get_armed(home_id: str) -> bool:
    doc = db.collection("homes").document(home_id).get()
    if doc:
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


    
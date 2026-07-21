# e un grafic, deci brace for impact ca e destul de vibe coded
import paho.mqtt.client as mqtt

# partea de window cu graficul in sine
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button

from collections import deque # deque e queue unde poti scoate si baga in ambele margini 
from datetime import datetime

import json
import os
import threading


# setup:
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

MAX_POINTS = 1200  # cam 10 points / secura din graph
GRAPHS_DIR = os.path.join(os.path.expanduser("-"), "Desktop", "SecuriFi-Nodes", "graphs")

NODES = {
    "securifi/node_1": {
        "lable": "Node 1", 
        "color": "#2D8518", 
        "shadow": "#A8E087"
    },

    "securifi/node_2": {
        "lable": "Node 2", 
        "color": "#852726", 
        "shadow": "#E08787"
    },

    "securifi/node_3": {
        "lable": "Node 3", 
        "color": "#103957", 
        "shadow": "#80B3D9"
    },

    "securifi/node_4": {
        "lable": "Node 4", 
        "color": "#4D0D59", 
        "shadow": "#D093DB"
    }
}

os.makedirs(GRAPHS_DIR, exist_ok=True) # creaza folderul in care sunt salvate graph-urile daca nu exista deja

data = {}
for topic in NODES: # topic-ul e cel de pe mqtt (securifi/node_x)
    data[topic] = deque(maxlen=MAX_POINTS)

lock = threading.Lock() # ca sa dai sync la threads (inputul din mosquitto si graph-ul in sine)


# mqtt:
def on_connect(client, userdata, flags, rc): # functie apelata de mqtt
    print(f"[MQTT]: Connected (rc={rc})")
    for topic in NODES:
        client.subscribe(topic)
        print(f"[MQTT]: Subscribed to {topic}")

def on_message(client, userdata, msg):
    topic = msg.topic
    if not topic in NODES:
        return
    
    
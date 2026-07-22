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
import re
import threading


# setup:
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

MAX_POINTS = 1200  # cam 10 points / secura din graph
GRAPHS_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "SecuriFi-Nodes", "graphs")

NODES = {
    "securifi/node_1": {
        "label": "Node 1", 
        "color": "#2D8518", 
        "shadow": "#A8E087"
    },

    "securifi/node_2": {
        "label": "Node 2", 
        "color": "#852726", 
        "shadow": "#E08787"
    },

    "securifi/node_3": {
        "label": "Node 3", 
        "color": "#103957", 
        "shadow": "#80B3D9"
    },

    "securifi/node_4": {
        "label": "Node 4", 
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
    if rc != 0:
        print(f"[MQTT]: Failed to connect (rc={rc})")
        return
    
    print(f"[MQTT]: Connected (rc={rc})")
    for topic in NODES:
        client.subscribe(topic)
        print(f"[MQTT]: Subscribed to {topic}")

def on_message(client, userdata, msg):
    topic = msg.topic
    if not topic in NODES:
        return
    
    try:
        payload = json.loads(msg.payload.decode())
        movement = payload.get("movement", 0)
        threshold = payload.get("threshold", 1)
        
        pct = 0
        if(threshold > 0):
            pct = int((movement / threshold) * 100)
        with lock:
            data[topic].append(pct)
    except Exception as e:
        print(f"[MQTT]: Parse error: {e}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()


# figure (window-ul): 
fig, ax = plt.subplots(figsize=(14,6))
plt.subplots_adjust(bottom=0.18)
fig.patch.set_facecolor('#0f0f0f')
ax.set_facecolor('#0f0f0f')

# save button:
ax_btn = fig.add_axes([0.44, 0.03, 0.12, 0.07])
btn = Button(ax_btn, 'Save PNG', color='#222222', hovercolor="#444444")
btn.label.set_color('white')
btn.label.set_fontsize(10)

def get_next_screenshot_index():
    max_index = 0

    for filename in os.listdir(GRAPHS_DIR):
        match = re.match(r"screenshot_(\d+)\.png", filename)

        if match:
            index = int(match.group(1))
            max_index = max(max_index, index)

    return max_index + 1

def save_png(event):
    path = os.path.join(GRAPHS_DIR, f"screenshot_{get_next_screenshot_index()}.png")
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='#0F0F0F')
    print(f"Saved: {path}")

btn.on_clicked(save_png)

def animate(frame):
    ax.clear()
    ax.set_facecolor('#0f0f0f')
 
    with lock:
        snapshot = {t: list(d) for t, d in data.items()}
 
    for topic, cfg in NODES.items():
        y = snapshot[topic]
        if not y:
            continue
        x = list(range(len(y)))
        ax.plot(x, y, color=cfg["color"], linewidth=1.5, label=cfg["label"])
        ax.fill_between(x, y, alpha=0.12, color=cfg["shadow"])
 
    # threshold line
    ax.axhline(y=100, color='#555555', linewidth=0.8, linestyle='--', label='100% threshold')
 
    ax.set_ylim(0, 200)
    ax.set_ylabel("Movement %", color='#888888', fontsize=10)
    ax.set_xlabel("Packets", color='#888888', fontsize=10)
    ax.set_title("SecuriFi — Live 4-Node View", color='#aaaaaa', fontsize=12, loc='left')
    ax.tick_params(colors='#555555')
    for spine in ax.spines.values():
        spine.set_color('#222222')
    ax.grid(True, alpha=0.08, color='white')
 
    legend = ax.legend(
        facecolor='#1a1a1a',
        labelcolor='white',
        fontsize=9,
        loc='upper left',
        framealpha=0.8
    )
 
    plt.tight_layout(rect=[0, 0.12, 1, 1])
 
ani = animation.FuncAnimation(fig, animate, interval=200, cache_frame_data=False)

try:
    plt.show()
finally:
    client.loop_stop()
    client.disconnect()
    print("Done")
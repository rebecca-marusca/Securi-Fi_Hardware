import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button
from collections import deque
import json
import os
import re
import threading

MQTT_BROKER = "192.168.137.1"  # TODO: Pi IP 
MQTT_PORT = 1883
MQTT_TOPIC = "securifi/master"

MAX_POINTS = 1200 

GRAPHS_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "Securi-Fi_Nodes", "graphs")
os.makedirs(GRAPHS_DIR, exist_ok=True)

NODE_PALETTE = [
    {"color": "#2D8518", "shadow": "#A8E087"},  
    {"color": "#852726", "shadow": "#E08787"},  
    {"color": "#103957", "shadow": "#80B3D9"},  
    {"color": "#4D0D59", "shadow": "#D093DB"}, 
    {"color": "#8C6D00", "shadow": "#E0C060"}, 
    {"color": "#005C5C", "shadow": "#60D0D0"}, 
    {"color": "#8C3300", "shadow": "#E08860"}, 
    {"color": "#3D3D3D", "shadow": "#AAAAAA"}, 
]

data: dict = {}

node_styles: dict = {}

node_order: list = []

lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print(f"[MQTT] Failed to connect (rc={rc})")
        return
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT] Connected, subscribed to {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        nodes = payload.get("nodes", [])

        if not isinstance(nodes, list):
            return

        with lock:
            for node in nodes:
                node_id = node.get("node_id")
                if not node_id:
                    continue

                if node_id not in node_styles:
                    index = len(node_styles)
                    if index >= len(NODE_PALETTE):
                        index = len(NODE_PALETTE) - 1
                    node_styles[node_id] = NODE_PALETTE[index]
                    node_order.append(node_id)
                    data[node_id] = deque(maxlen=MAX_POINTS)

                try:
                    data[node_id].append(int(node.get("raw_mq2_reading", 0)))
                except (TypeError, ValueError):
                    data[node_id].append(0)

    except Exception as e:
        print(f"[MQTT] Parse error: {e}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()


# Figure
fig, ax = plt.subplots(figsize=(14, 6))
plt.subplots_adjust(bottom=0.18)
fig.patch.set_facecolor('#0f0f0f')
ax.set_facecolor('#0f0f0f')

# Save button
ax_btn = fig.add_axes([0.44, 0.03, 0.12, 0.07])
btn = Button(ax_btn, 'Save PNG', color='#222222', hovercolor='#444444')
btn.label.set_color('white')
btn.label.set_fontsize(10)

def get_next_graph_index():
    max_index = 0
    for filename in os.listdir(GRAPHS_DIR):
        match = re.match(r"graph_(\d+)\.png", filename)
        if match:
            index = int(match.group(1))
            max_index = max(max_index, index)
    return max_index + 1

def save_png(event):
    path = os.path.join(GRAPHS_DIR, f"graph_{get_next_graph_index()}.png")
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='#0f0f0f')
    print(f"[Graph] Saved: {path}")

btn.on_clicked(save_png)

# Animation
def animate(frame):
    ax.clear()
    ax.set_facecolor('#0f0f0f')

    with lock:
        # Snapshot both data and order under lock so they're consistent
        snapshot = {node_id: list(data[node_id]) for node_id in node_order}
        styles = dict(node_styles)
        order = list(node_order)

    for node_id in order:
        y = snapshot.get(node_id, [])
        if not y:
            continue
        style = styles[node_id]
        x = list(range(len(y)))
        ax.plot(x, y, color=style["color"], linewidth=1.5, label=node_id)
        ax.fill_between(x, y, alpha=0.12, color=style["shadow"])

   
    ax.axhline(y=1500, color='#555555', linewidth=0.8, linestyle='--', label='1500 gas threshold')
    ax.set_ylim(0, 4095)
    ax.set_ylabel("MQ2 Raw Value", color='#888888', fontsize=10)
    node_count = len(order)
    title = f"SecuriFi — Live View ({node_count} node{'s' if node_count != 1 else ''})"

    ax.set_xlabel("Packets", color='#888888', fontsize=10)
    ax.set_title(title, color='#aaaaaa', fontsize=12, loc='left')
    ax.tick_params(colors='#555555')
    for spine in ax.spines.values():
        spine.set_color('#222222')
    ax.grid(True, alpha=0.08, color='white')

    ax.legend(
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
    print("[Graph] Done")
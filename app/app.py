# app/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback, sys

# graph & data libs
import networkx as nx
from scripts.preprocess import load_and_clean

app = Flask(__name__)
CORS(app)   # allow requests from frontend (localhost:3000)


def build_graph(df):
    """
    Build a directed NetworkX graph from DataFrame rows.
    Each edge stores: cost, duration, distance, mode, (optionally) from_lat/from_lng/to_lat/to_lng
    """
    G = nx.DiGraph()
    for _, r in df.iterrows():
        src = r['source']
        dst = r['destination']
        # ensure node exists
        if src not in G:
            G.add_node(src)
        if dst not in G:
            G.add_node(dst)

        # edge attributes
        attr = {
            "cost": float(r.get("cost", 0.0)),
            "duration": float(r.get("duration_hours", r.get("duration", 0.0))),
            "distance": float(r.get("distance_km", r.get("distance", 0.0))),
            "mode": str(r.get("mode", "train"))
        }
        # optional coordinates if present in df
        if "from_lat" in r and not pd_is_null(r["from_lat"]):
            attr["from_lat"] = float(r["from_lat"])
            attr["from_lng"] = float(r["from_lng"])
        if "to_lat" in r and not pd_is_null(r["to_lat"]):
            attr["to_lat"] = float(r["to_lat"])
            attr["to_lng"] = float(r["to_lng"])

        # add edge (store cost & duration under named keys)
        # we avoid passing "weight" here to prevent conflicts — weight will be computed separately
        G.add_edge(src, dst, **attr)
    return G

def pd_is_null(x):
    """small helper to check pandas NaN / None without importing pandas here"""
    try:
        import math
        return x is None or (isinstance(x, float) and math.isnan(x))
    except Exception:
        return x is None

def format_breakdown_for_path(G, path):
    breakdown = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i+1]
        e = G.get_edge_data(u, v)
        if e is None:
            # shouldn't happen if path came from this graph
            continue
        item = {
            "from": u,
            "to": v,
            "mode": e.get("mode"),
            "cost": float(e.get("cost", 0.0)),
            "duration_hours": float(e.get("duration", 0.0)),
            "distance_km": float(e.get("distance", 0.0))
        }
        # include coordinates if present
        if "from_lat" in e:
            item["from_lat"] = e.get("from_lat")
            item["from_lng"] = e.get("from_lng")
        if "to_lat" in e:
            item["to_lat"] = e.get("to_lat")
            item["to_lng"] = e.get("to_lng")
        breakdown.append(item)
    return breakdown

def find_cheapest_path(G, src, dst, transfer_penalty=50.0):
    """
    Compute cheapest path. To discourage many transfers, we add a per-edge penalty when computing the path.
    Implementation: build a temporary graph H where edge 'w' = cost + transfer_penalty, then run shortest_path on 'w'.
    Return dict with path, raw_cost, total_cost (raw + penalty), breakdown, num_edges, transfer_penalty.
    """
    try:
        H = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            cost = float(data.get("cost", 0.0))
            w = cost + float(transfer_penalty)
            # store original data but weight key is 'w'
            H.add_edge(u, v, w=w, **data)

        path = nx.shortest_path(H, source=src, target=dst, weight='w')
        # compute raw cost from original G (sum of 'cost' values)
        raw_cost = sum(float(G.get_edge_data(path[i], path[i+1])['cost']) for i in range(len(path)-1))
        num_edges = max(0, len(path)-1)
        total_cost = raw_cost + (num_edges * float(transfer_penalty))
        breakdown = format_breakdown_for_path(G, path)

        return {
            "path": path,
            "raw_cost": float(raw_cost),
            "total_cost": float(total_cost),
            "transfer_penalty": float(transfer_penalty),
            "num_edges": int(num_edges),
            "breakdown": breakdown
        }
    except nx.NetworkXNoPath:
        return {"error": f"No path between {src} and {dst}"}
    except Exception as e:
        return {"error": str(e)}

def find_fastest_path(G, src, dst, transfer_penalty=50.0, transfer_penalty_time=0.5):
    """
    Compute fastest path by minimizing duration.
    For path selection we add a small time penalty per transfer to discourage many hops (transfer_penalty_time in hours).
    We still return monetary totals (raw_cost) and compute total_cost = raw_cost + (num_edges * transfer_penalty)
    """
    try:
        H = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            duration = float(data.get("duration", 0.0))
            # effective weight = duration + transfer_time_penalty
            w = duration + float(transfer_penalty_time)
            H.add_edge(u, v, w=w, **data)

        path = nx.shortest_path(H, source=src, target=dst, weight='w')
        raw_cost = sum(float(G.get_edge_data(path[i], path[i+1])['cost']) for i in range(len(path)-1))
        num_edges = max(0, len(path)-1)
        total_cost = raw_cost + (num_edges * float(transfer_penalty))
        breakdown = format_breakdown_for_path(G, path)

        return {
            "path": path,
            "raw_cost": float(raw_cost),
            "total_cost": float(total_cost),
            "transfer_penalty": float(transfer_penalty),
            "num_edges": int(num_edges),
            "breakdown": breakdown
        }

    except nx.NetworkXNoPath:
        return {"error": f"No path between {src} and {dst}"}
    except Exception as e:
        return {"error": str(e)}

def find_balanced_path(G, src, dst, alpha=0.6, transfer_penalty=50.0, transfer_penalty_time=0.5):
    """
    Balanced path: combine normalized cost and normalized duration.
    alpha in [0,1] controls weight given to cost (alpha=1 -> cost only, alpha=0 -> duration only).
    We normalize cost and duration per-edge using the max observed in the graph to put them on same scale.
    For selection we use a combined normalized weight; final monetary total = raw_cost + (num_edges * transfer_penalty)
    """
    try:
        # collect maxima for normalization
        costs = []
        durations = []
        for _, _, data in G.edges(data=True):
            costs.append(float(data.get("cost", 0.0)))
            durations.append(float(data.get("duration", 0.0)))
        max_cost = max(costs) if costs else 1.0
        max_duration = max(durations) if durations else 1.0

        H = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            cost = float(data.get("cost", 0.0))
            duration = float(data.get("duration", 0.0))
            # normalized
            cost_n = cost / max_cost if max_cost > 0 else 0.0
            dur_n = duration / max_duration if max_duration > 0 else 0.0
            combined = alpha * cost_n + (1.0 - alpha) * dur_n
            # add a small per-edge penalty to discourage many hops (scaled to combined space)
            w = combined + (transfer_penalty / (max_cost if max_cost > 0 else 1.0))  # normalized penalty
            H.add_edge(u, v, w=w, **data)

        path = nx.shortest_path(H, source=src, target=dst, weight='w')
        raw_cost = sum(float(G.get_edge_data(path[i], path[i+1])['cost']) for i in range(len(path)-1))
        num_edges = max(0, len(path)-1)
        total_cost = raw_cost + (num_edges * float(transfer_penalty))
        breakdown = format_breakdown_for_path(G, path)

        return {
            "path": path,
            "raw_cost": float(raw_cost),
            "total_cost": float(total_cost),
            "transfer_penalty": float(transfer_penalty),
            "num_edges": int(num_edges),
            "breakdown": breakdown
        }

    except nx.NetworkXNoPath:
        return {"error": f"No path between {src} and {dst}"}
    except Exception as e:
        return {"error": str(e)}

# Load dataset and build graph on startup
try:
    # load_and_clean signature in your repo is load_and_clean(path) -> DataFrame
    df = load_and_clean("data/multi_modal_routes_realistic.csv")
    G = build_graph(df)
except Exception as e:
    print("!!! Failed to load dataset or build graph:", e, file=sys.stdout)
    traceback.print_exc(file=sys.stdout)
    G = nx.DiGraph()  # empty graph to avoid crashes

@app.route("/")
def home():
    return "✅ Travel Planner Backend is Live!"

@app.route("/route")
def route():
    src = request.args.get("src")
    dst = request.args.get("dst")
    mode = request.args.get("mode", "cheapest").lower()

    if not src or not dst:
        return jsonify({"error": "src and dst query params required"}), 400

    # choose algorithm
    if mode == "fastest":
        res = find_fastest_path(G, src, dst, transfer_penalty=50.0, transfer_penalty_time=0.5)
    elif mode == "balanced":
        # alpha controls cost vs duration: 0.6 favors cost modestly
        res = find_balanced_path(G, src, dst, alpha=0.6, transfer_penalty=50.0, transfer_penalty_time=0.5)
    else:
        # default cheapest
        res = find_cheapest_path(G, src, dst, transfer_penalty=50.0)

    return jsonify(res)

if __name__ == "__main__":
    print(">>> Starting Flask app (app/app.py) ...", flush=True)
    try:
        app.run(host="127.0.0.1", port=5000, debug=True)
    except Exception as e:
        print("!!! Flask failed to start:", e)
        traceback.print_exc(file=sys.stdout)

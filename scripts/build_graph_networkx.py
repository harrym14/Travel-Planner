# scripts/build_graph_networkx.py
import networkx as nx
from scripts.preprocess import load_and_clean

def build_graph(df):
    """
    Build a directed NetworkX graph from dataframe.
    Edges store attributes: cost, duration, distance, mode
    """
    G = nx.DiGraph()
    for _, r in df.iterrows():
        src = r['source']
        dst = r['destination']
        # store cost, duration, distance and mode
        G.add_edge(
            src,
            dst,
            cost=float(r['cost']),
            duration=float(r['duration_hours']),
            distance=float(r['distance_km']),
            mode=str(r['mode'])
        )
    return G

def path_breakdown(G, path):
    """Return breakdown list and summary numbers (raw cost, raw duration)."""
    breakdown = []
    raw_cost = 0.0
    raw_duration = 0.0
    for i in range(len(path)-1):
        e = G.get_edge_data(path[i], path[i+1])
        breakdown.append({
            "from": path[i],
            "to": path[i+1],
            "mode": e.get("mode"),
            "cost": float(e.get("cost")),
            "duration_hours": float(e.get("duration")),
            "distance_km": float(e.get("distance"))
        })
        raw_cost += float(e.get("cost"))
        raw_duration += float(e.get("duration"))
    return breakdown, raw_cost, raw_duration

def find_cheapest_path(G, src, dst, transfer_penalty=50.0):
    """
    Find path minimizing monetary cost, with a per-edge transfer penalty.
    We create a temp graph H where each edge weight = cost + transfer_penalty,
    then use NX shortest_path on that weight. Final total cost = raw_cost + n_edges*transfer_penalty
    """
    try:
        H = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            w = float(data.get("cost", 0.0)) + float(transfer_penalty)
            H.add_edge(u, v, weight=w)
        path = nx.shortest_path(H, source=src, target=dst, weight='weight')
        breakdown, raw_cost, raw_duration = path_breakdown(G, path)
        num_edges = max(0, len(path)-1)
        total_cost = raw_cost + num_edges * float(transfer_penalty)
        return {
            "path": path,
            "breakdown": breakdown,
            "raw_cost": float(raw_cost),
            "raw_duration": float(raw_duration),
            "num_edges": num_edges,
            "transfer_penalty": float(transfer_penalty),
            "total_cost": float(total_cost)
        }
    except nx.NetworkXNoPath:
        return {"error": f"No path between {src} and {dst}"}
    except Exception as e:
        return {"error": str(e)}

def find_fastest_path(G, src, dst, transfer_penalty_time=0.5):
    """
    Find path minimizing travel time (duration). transfer_penalty_time adds a small penalty (hours)
    for each additional segment (represents transfer time).
    """
    try:
        H = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            # use duration as base weight, add a small penalty per transfer to discourage many tiny hops
            w = float(data.get("duration", 0.0)) + float(transfer_penalty_time)
            H.add_edge(u, v, weight=w)
        path = nx.shortest_path(H, source=src, target=dst, weight='weight')
        breakdown, raw_cost, raw_duration = path_breakdown(G, path)
        total_time = raw_duration + (len(path)-1) * float(transfer_penalty_time)
        # compute monetary total (no transfer monetary penalty here)
        return {
            "path": path,
            "breakdown": breakdown,
            "raw_cost": float(raw_cost),
            "raw_duration": float(raw_duration),
            "num_edges": max(0, len(path)-1),
            "transfer_penalty_time": float(transfer_penalty_time),
            "total_time_hours": float(total_time),
            "total_cost": float(raw_cost)  # keep field for frontend
        }
    except nx.NetworkXNoPath:
        return {"error": f"No path between {src} and {dst}"}
    except Exception as e:
        return {"error": str(e)}

def find_balanced_path(G, src, dst, alpha=0.6, transfer_penalty=50.0, transfer_penalty_time=0.5):
    """
    Balanced multi-objective: combine cost and duration into a single weight.
    alpha in [0,1] is weight for cost importance (higher -> prefers cheaper).
    We normalize cost and duration by their maximum across all edges (to get unitless metrics)
    then create per-edge weight = alpha * (cost / max_cost) + (1-alpha) * (duration / max_duration) + small per-edge penalties.
    """
    try:
        # compute max cost and max duration across edges for normalization
        costs = [float(d.get("cost", 0.0)) for _, _, d in G.edges(data=True)]
        durs = [float(d.get("duration", 0.0)) for _, _, d in G.edges(data=True)]
        max_cost = max(costs) if costs else 1.0
        max_dur = max(durs) if durs else 1.0

        H = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            c = float(data.get("cost", 0.0))
            dur = float(data.get("duration", 0.0))
            # normalized components
            norm_cost = c / max_cost
            norm_dur = dur / max_dur
            weight = alpha * norm_cost + (1.0 - alpha) * norm_dur
            # scale up slightly and add small penalties to discourage many hops
            weight = weight + (transfer_penalty / (max_cost + 1e-9)) + (transfer_penalty_time / (max_dur + 1e-9))
            H.add_edge(u, v, weight=weight)
        path = nx.shortest_path(H, source=src, target=dst, weight='weight')
        breakdown, raw_cost, raw_duration = path_breakdown(G, path)
        num_edges = max(0, len(path)-1)
        total_cost = raw_cost + num_edges * float(transfer_penalty)
        total_time = raw_duration + num_edges * float(transfer_penalty_time)
        return {
            "path": path,
            "breakdown": breakdown,
            "raw_cost": float(raw_cost),
            "raw_duration": float(raw_duration),
            "num_edges": num_edges,
            "transfer_penalty": float(transfer_penalty),
            "transfer_penalty_time": float(transfer_penalty_time),
            "total_cost": float(total_cost),
            "total_time_hours": float(total_time),
            "alpha": float(alpha)
        }
    except nx.NetworkXNoPath:
        return {"error": f"No path between {src} and {dst}"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    df = load_and_clean()
    G = build_graph(df)
    src = "Mumbai"
    dst = "Delhi"
    print("Cheapest:", find_cheapest_path(G, src, dst))
    print("Fastest:", find_fastest_path(G, src, dst))
    print("Balanced:", find_balanced_path(G, src, dst))

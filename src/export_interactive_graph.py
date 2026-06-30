import argparse
import json
import statistics
from pathlib import Path

import networkx as nx

from utils.db_utils import DBDataLoader
from ego_network_analyzer import EgoNetworkAnalyzer
from cluster_statistics import compute_statistics

OUTPUT_DIR = "output/graphs"
POSITION_SCALE = 900


def write_graph_index(dataset_path="."):
    graphs_dir = Path(dataset_path) / OUTPUT_DIR
    graphs_dir.mkdir(parents=True, exist_ok=True)

    egos = []
    for path in sorted(graphs_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else -1):
        if not path.is_dir() or not path.name.isdigit():
            continue
        ego_id = path.name
        entry = {"id": ego_id}
        egos.append(entry)

    index_path = graphs_dir / "index.json"
    with index_path.open("w", encoding="utf-8") as index_file:
        json.dump({"egos": egos}, index_file, ensure_ascii=False, indent=2)


def rgb_to_hex(rgb):
    r, g, b = rgb
    return "#{:02x}{:02x}{:02x}".format(
        int(max(0, min(255, round(r * 255)))),
        int(max(0, min(255, round(g * 255)))),
        int(max(0, min(255, round(b * 255)))),
    )


def build_cluster_legend(feat_clusters, graph_nodes, cluster_colors):
    graph_node_set = {int(node) for node in graph_nodes}
    legend = []

    for cluster_label, members in feat_clusters.items():
        members_in_graph = [m for m in members if m in graph_node_set]
        if not members_in_graph:
            continue

        legend.append(
            {
                "name": cluster_label,
                "color": rgb_to_hex(cluster_colors[cluster_label]) if cluster_label in cluster_colors else "#888888",
                "node_count": len(members_in_graph),
            }
        )

    return legend


def mean(values):
    return float(statistics.fmean(values)) if values else 0.0


def median(values):
    return float(statistics.median(values)) if values else 0.0


def compute_graph_statistics(graph, node_to_clusters):
    nodes = list(graph.nodes)
    all_cluster_names = sorted(set(
        c for clusters in node_to_clusters.values() for c in clusters
    ))

    all_degrees = [int(graph.degree(n)) for n in nodes]
    overall = {
        "node_count": len(nodes),
        "mean_degree": mean(all_degrees),
        "median_degree": median(all_degrees),
        "density": float(nx.density(graph)),
    }

    per_cluster = []
    for cluster_name in all_cluster_names:
        cluster_nodes = [n for n in nodes if cluster_name in node_to_clusters.get(int(n), [])]
        subgraph = graph.subgraph(cluster_nodes)
        per_cluster.append({
            "name": cluster_name,
            "node_count": len(cluster_nodes),
            "internal_density": float(nx.density(subgraph)) if subgraph.number_of_nodes() > 1 else 0.0,
        })

    return {
        "overall": overall,
        "per_cluster": per_cluster,
    }


def build_graph(analyzer, ego_id, graph_type):
    if graph_type == "edges":
        graph = analyzer.construir_grafo_edges(ego_id)
        if graph is None:
            raise ValueError(f"Nenhuma aresta encontrada para ego_id {ego_id}")
        return graph
    return analyzer.construir_grafo_feats(ego_id)


def export_graph_data(ego_id, graph_type, dataset_path="."):
    db_path = Path(dataset_path) / "output/ego_network_users.db"
    data_loader = DBDataLoader(db_path)
    analyzer = EgoNetworkAnalyzer(dataset_path, data_loader)

    graph = build_graph(analyzer, ego_id, graph_type)

    graph_utils = analyzer.graph_utils

    feat_clusters = data_loader.carregar_feat_clusters(ego_id)
    node_to_clusters = {int(node): [] for node in graph.nodes}
    for cluster_label, members in feat_clusters.items():
        for member in members:
            if member in node_to_clusters:
                node_to_clusters[member].append(cluster_label)

    node_colors = graph_utils.set_node_color(ego_id, list(graph.nodes))
    cluster_colors = graph_utils.get_cluster_colors(ego_id, list(graph.nodes))
    pos = graph_utils.get_layout(ego_id, graph)
    graph_stats = compute_graph_statistics(graph, node_to_clusters)
    cluster_legend = build_cluster_legend(feat_clusters, graph.nodes, cluster_colors)
    advanced_stats = compute_statistics(ego_id, graph, node_to_clusters) if graph_type == "edges" else None

    nodes = []
    for node in graph.nodes:
        node_id = int(node)
        xy = pos.get(node, (0.0, 0.0))
        x = float(xy[0]) * POSITION_SCALE
        y = float(xy[1]) * POSITION_SCALE

        node_data = {
            "id": str(node_id),
            "label": str(node_id),
            "color": rgb_to_hex(node_colors[node]),
            "degree": int(graph.degree(node)),
            "clusters": node_to_clusters.get(node_id, []),
            "cluster_count": len(node_to_clusters.get(node_id, [])),
        }

        if graph.is_directed():
            node_data["in_degree"] = int(graph.in_degree(node))
            node_data["out_degree"] = int(graph.out_degree(node))

        nodes.append(
            {
                "data": node_data,
                "position": {"x": x, "y": y},
            }
        )

    edges = []
    for idx, (u, v, data) in enumerate(graph.edges(data=True)):
        weight = int(data.get("weight", 0))
        edge_color = graph_utils.EDGE_COLORS.get(weight, "#888888")
        edges.append(
            {
                "data": {
                    "id": f"e{idx}",
                    "source": str(int(u)),
                    "target": str(int(v)),
                    "weight": weight,
                    "color": edge_color,
                }
            }
        )

    payload = {
        "metadata": {
            "ego_id": ego_id,
            "graph_type": graph_type,
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "is_directed": graph.is_directed(),
            "clusters": cluster_legend,
            "statistics": {
                "current": graph_stats,
            },
            "advanced_statistics": advanced_stats,
        },
        "elements": {
            "nodes": nodes,
            "edges": edges,
        },
    }

    output_dir = Path(dataset_path) / OUTPUT_DIR / str(ego_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{ego_id}_{graph_type}_interactive.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    write_graph_index(dataset_path)

    print(f"JSON interativo salvo em: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Exporta JSON para visualizacao interativa no navegador.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("ego_id", type=int, nargs="?", help="ID da ego-network")
    group.add_argument("--todos", action="store_true", help="Exporta todos os egos")
    parser.add_argument("--tipo", choices=["edges", "feats", "ambos"], default="ambos", help="Tipo do grafo")
    parser.add_argument("--dataset-path", default=".", help="Diretorio base do projeto")
    args = parser.parse_args()

    tipos = ["edges", "feats"] if args.tipo == "ambos" else [args.tipo]

    if args.todos:
        db_path = Path(args.dataset_path) / "output/ego_network_users.db"
        ego_ids = DBDataLoader(db_path).carregar_ego_ids_por_nos()
        total = len(ego_ids)
        print(f"Exportando {total} egos...")
        for i, ego_id in enumerate(ego_ids, 1):
            print(f"[{i}/{total}] ego_id={ego_id}")
            for tipo in tipos:
                try:
                    export_graph_data(ego_id, tipo, args.dataset_path)
                except Exception as exc:
                    print(f"  ERRO ({tipo}): {exc}")
    else:
        for tipo in tipos:
            export_graph_data(args.ego_id, tipo, args.dataset_path)


if __name__ == "__main__":
    main()

"""
cluster_statistics.py
---------------------
Compara métricas de coesão intra-cluster vs. o grafo global para cada ego-network,
com o objetivo de provar que dentro dos clusters os usuários se seguem mais.

Estatísticas geradas
--------------------
- densidade_global        : densidade global do grafo
- seguir_mesmo_cluster    : P(A→B | A e B no mesmo cluster)
- seguir_outro_cluster    : P(A→B | A e B em clusters diferentes)
- razao_seguimento        : seguir_mesmo_cluster / seguir_outro_cluster  (> 1 = tese confirmada)
- modularidade            : Q de modularidade (> 0 = estrutura de comunidade presente)
- condutancia_media       : conductância média dos clusters (< 1 = clusters coesos)
- embeddedness_medio      : fração média das vizinhanças de cada nó que está no mesmo cluster
- fracao_arestas_intra    : fração das arestas totais que são intra-cluster
- media_permutacao        : média da fracao_arestas_intra em permutações aleatórias
- p_valor_aprox           : proporção de permutações >= valor observado (< 0.05 = significativo)

Uso
---
    python src/cluster_statistics.py
    python src/cluster_statistics.py --ego-id 100318079
"""

import argparse
import csv
import random
import statistics
import sys
from pathlib import Path

import networkx as nx

# Permite importar utils/ estando em src/ ou na raiz
sys.path.insert(0, str(Path(__file__).parent))
from utils.db_utils import DBDataLoader

DB_PATH = "output/ego_network_users.db"
OUTPUT_CSV = "output/cluster_statistics.csv"
DEFAULT_PERMUTATION_RUNS = 300  # número de permutações para o teste estatístico

COLUMNS = [
    "ego_id",
    "nos",
    "arestas",
    "clusters",
    "densidade_global",
    "media_densidade_intra_cluster",
    "seguir_mesmo_cluster",
    "seguir_outro_cluster",
    "razao_seguimento",
    "modularidade",
    "embeddedness_medio",
    "fracao_arestas_intra",
    "media_permutacao",
    "p_valor_aprox",
]


def _node_to_clusters_map(nodes, feat_clusters: dict) -> dict:
    """Mapeia cada nó para a lista de clusters a que pertence."""
    mapping = {int(n): [] for n in nodes}
    for cluster_label, members in feat_clusters.items():
        for m in members:
            if m in mapping:
                mapping[m].append(cluster_label)
    return mapping


def _build_directed_graph(data_loader: DBDataLoader, ego_id: int) -> nx.DiGraph | None:
    edges = data_loader.carregar_edges_db(ego_id)
    if not edges:
        return None
    _, node_ids = data_loader.carregar_feats_e_ids(ego_id)
    G = nx.DiGraph()
    G.add_nodes_from(node_ids)
    G.add_edges_from(edges)
    return G


def compute_statistics(ego_id: int, graph: nx.DiGraph, node_to_clusters: dict, n_permutations: int = DEFAULT_PERMUTATION_RUNS) -> dict | None:
    nodes = list(graph.nodes())
    total_edges = graph.number_of_edges()
    n = len(nodes)

    if n < 3 or total_edges == 0:
        return None

    all_cluster_names = sorted({
        c for clusters in node_to_clusters.values() for c in clusters
    })
    if not all_cluster_names:
        return None

    # ── Densidade global ───────────────────────────────────────────────────
    global_density = nx.density(graph)

    # ── Arestas intra vs. inter cluster ────────────────────────────────────
    intra_edges = 0
    for u, v in graph.edges():
        cu = set(node_to_clusters.get(int(u), []))
        cv = set(node_to_clusters.get(int(v), []))
        if cu & cv:
            intra_edges += 1

    inter_edges = total_edges - intra_edges

    # ── Probabilidade condicional de seguimento ─────────────────────────────
    # Pares ordenados possíveis dentro do mesmo cluster
    same_cluster_possible = 0
    for cluster_name in all_cluster_names:
        members = [nd for nd in nodes if cluster_name in node_to_clusters.get(int(nd), [])]
        nc = len(members)
        same_cluster_possible += nc * (nc - 1)

    different_cluster_possible = n * (n - 1) - same_cluster_possible

    p_follow_same = intra_edges / same_cluster_possible if same_cluster_possible > 0 else 0.0
    p_follow_diff = inter_edges / different_cluster_possible if different_cluster_possible > 0 else 0.0
    follow_ratio = p_follow_same / p_follow_diff if p_follow_diff > 0 else float("inf")


    # ── Média das densidades intra-cluster ──────────────────────────────────
    intra_densities = []
    for cluster_name in all_cluster_names:
        members = [nd for nd in nodes if cluster_name in node_to_clusters.get(int(nd), [])]
        if len(members) > 1:
            subg = graph.subgraph(members)
            intra_densities.append(nx.density(subg))
    media_densidade_intra_cluster = statistics.mean(intra_densities) if intra_densities else 0.0

    # ── Modularidade ────────────────────────────────────────────────────────
    # Partição crisp: cada nó vai para seu primeiro cluster; sem cluster → singleton
    partition_dict: dict = {}
    for nd in nodes:
        clusters_of_node = node_to_clusters.get(int(nd), [])
        if clusters_of_node:
            partition_dict.setdefault(clusters_of_node[0], set()).add(nd)
        else:
            partition_dict.setdefault(f"__unclustered_{nd}", set()).add(nd)

    communities = list(partition_dict.values())
    try:
        modularity = nx.community.modularity(graph, communities)
    except Exception:
        modularity = None

    # ── Embeddedness médio ──────────────────────────────────────────────────
    embeddings = []
    for nd in nodes:
        node_clusters = set(node_to_clusters.get(int(nd), []))
        if not node_clusters:
            continue
        neighbors = set(graph.successors(nd)) | set(graph.predecessors(nd))
        if not neighbors:
            continue
        intra_nb = sum(
            1 for nb in neighbors
            if node_clusters & set(node_to_clusters.get(int(nb), []))
        )
        embeddings.append(intra_nb / len(neighbors))
    mean_embeddedness = statistics.mean(embeddings) if embeddings else 0.0

    # ── Teste de permutação ─────────────────────────────────────────────────
    observed_intra_fraction = intra_edges / total_edges

    cluster_labels_list = [node_to_clusters.get(int(nd), []) for nd in nodes]
    shuffled_fractions = []
    for _ in range(n_permutations):
        random.shuffle(cluster_labels_list)
        shuffled_map = {nd: cluster_labels_list[i] for i, nd in enumerate(nodes)}
        shuffled_intra = sum(
            1 for u, v in graph.edges()
            if set(shuffled_map.get(u, [])) & set(shuffled_map.get(v, []))
        )
        shuffled_fractions.append(shuffled_intra / total_edges)

    perm_mean = statistics.mean(shuffled_fractions)
    p_value_approx = sum(1 for f in shuffled_fractions if f >= observed_intra_fraction) / n_permutations

    return {
        "ego_id": ego_id,
        "nos": n,
        "arestas": total_edges,
        "clusters": len(all_cluster_names),
        "densidade_global": round(global_density, 6),
        "media_densidade_intra_cluster": round(media_densidade_intra_cluster, 6),
        "seguir_mesmo_cluster": round(p_follow_same, 6),
        "seguir_outro_cluster": round(p_follow_diff, 6),
        "razao_seguimento": round(follow_ratio, 4) if follow_ratio != float("inf") else "inf",
        "modularidade": round(modularity, 4) if modularity is not None else "N/A",
        "embeddedness_medio": round(mean_embeddedness, 4),
        "fracao_arestas_intra": round(observed_intra_fraction, 4),
        "media_permutacao": round(perm_mean, 4),
        "p_valor_aprox": round(p_value_approx, 4),
    }


def _print_table(results: list[dict]) -> None:
    if not results:
        print("Nenhum resultado para exibir.")
        return

    col_widths = {col: max(len(col), max(len(str(r.get(col, ""))) for r in results)) for col in COLUMNS}
    header = "  ".join(col.ljust(col_widths[col]) for col in COLUMNS)
    separator = "  ".join("-" * col_widths[col] for col in COLUMNS)

    print("\n" + header)
    print(separator)
    for row in results:
        print("  ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in COLUMNS))

    print(f"\n{len(results)} ego-network(s) processada(s).")


def _save_csv(results: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nCSV salvo em: {output_path}")


def run(ego_ids: list[int], n_permutations: int = DEFAULT_PERMUTATION_RUNS) -> list[dict]:
    db_path = Path(".") / DB_PATH
    data_loader = DBDataLoader(db_path)

    results = []
    total = len(ego_ids)

    for i, ego_id in enumerate(ego_ids, 1):
        print(f"[{i}/{total}] Processando ego_id={ego_id}...", end=" ", flush=True)

        graph = _build_directed_graph(data_loader, ego_id)
        if graph is None:
            print("sem arestas — ignorado.")
            continue

        feat_clusters = data_loader.carregar_feat_clusters(ego_id)
        node_to_clusters = _node_to_clusters_map(graph.nodes(), feat_clusters)

        stats = compute_statistics(ego_id, graph, node_to_clusters, n_permutations)
        if stats is None:
            print("grafo muito pequeno ou sem clusters — ignorado.")
            continue

        results.append(stats)
        print(
            f"OK  |  razao_seguimento={stats['razao_seguimento']}  "
            f"modularidade={stats['modularidade']}  "
            f"p_valor≈{stats['p_valor_aprox']}"
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera estatísticas de coesão intra-cluster vs. global."
    )
    parser.add_argument("--ego-id", type=int, help="Processa apenas este ego_id")
    parser.add_argument("--no-csv", action="store_true", help="Não salva o arquivo CSV")
    parser.add_argument(
        "--permutations", type=int, default=DEFAULT_PERMUTATION_RUNS,
        help=f"Número de permutações para o teste estatístico (padrão: {DEFAULT_PERMUTATION_RUNS})"
    )
    args = parser.parse_args()

    db_path = Path(".") / DB_PATH
    data_loader = DBDataLoader(db_path)

    if args.ego_id:
        ego_ids = [args.ego_id]
    else:
        ego_ids = data_loader.carregar_ego_ids_por_nos()

    results = run(ego_ids, args.permutations)

    _print_table(results)

    if not args.no_csv:
        _save_csv(results, Path(".") / OUTPUT_CSV)


if __name__ == "__main__":
    main()

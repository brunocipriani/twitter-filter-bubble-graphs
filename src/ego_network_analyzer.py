import networkx as nx
from utils.graph_utils import GraphUtils

class EgoNetworkAnalyzer:
    MIN_COMMUN_FEATS = 1 # Número mínimo de feats em comum para criar aresta

    def __init__(self, dataset_path, data_loader):
        self.dataset_path = dataset_path
        self.data_loader = data_loader
        self.graph_utils = GraphUtils(data_loader)

    def construir_grafo_feats(self, ego_id: int) -> nx.Graph:
        import itertools
        nodes_feats, node_ids = self.data_loader.carregar_feats_e_ids(ego_id)
        G = nx.Graph()
        G.add_nodes_from(node_ids)
        edge_ratios = []

        # gerar arestas com base na similaridade de feats
        for i, j in itertools.combinations(range(len(node_ids)), 2):
            feats_i = set(idx for idx, v in enumerate(nodes_feats[i]) if v == 1)
            feats_j = set(idx for idx, v in enumerate(nodes_feats[j]) if v == 1)

            inter = feats_i & feats_j # interseção dos feats dos dois nós
            union = feats_i | feats_j # união dos feats dos dois nós

            if len(inter) >= self.MIN_COMMUN_FEATS:
                ratio = len(inter) / len(union) if len(union) > 0 else 0    # índice de Jaccard
                edge_ratios.append((node_ids[i], node_ids[j], ratio))

        ratios_vals = [r for _, _, r in edge_ratios]
        media = sum(ratios_vals) / len(ratios_vals) if ratios_vals else 1

        # atribuir peso às arestas com base na razão inter/union
        for u, v, ratio in edge_ratios:
            if ratio > 1.2 * media:
                peso = 1
            elif ratio >= 0.8 * media:
                peso = 0
            else:
                peso = -1
            G.add_edge(u, v, weight=peso)

        return G

    def construir_grafo_edges(self, ego_id: int) -> nx.DiGraph:
        edges = self.data_loader.carregar_edges_db(ego_id)
        if not edges:
            return None

        G = nx.DiGraph() # grafo direcionado

        # adicionar nós ao grafo
        _, node_ids = self.data_loader.carregar_feats_e_ids(ego_id)
        G.add_nodes_from(node_ids)

        for u, v in edges:
            G.add_edge(u, v)

        common_neighbors_counts = []
        for u, v in G.edges():
            viz_u = set(G.successors(u)).union(set(G.predecessors(u))) # vizinhanca de u
            viz_v = set(G.successors(v)).union(set(G.predecessors(v))) # vizinhanca de v
            common_neighbors_counts.append(len(viz_u & viz_v))

        # calcular tercis para classificar as arestas
        if common_neighbors_counts:
            sorted_counts = sorted(common_neighbors_counts)
            tercil1 = sorted_counts[len(sorted_counts) // 3]
            tercil2 = sorted_counts[2 * len(sorted_counts) // 3]
        else:
            tercil1 = tercil2 = 0

        for idx, (u, v) in enumerate(G.edges()):
            count = common_neighbors_counts[idx]
            if count > tercil2:
                G[u][v]['weight'] = 1
            elif count > tercil1:
                G[u][v]['weight'] = 0
            else:
                G[u][v]['weight'] = -1

        return G
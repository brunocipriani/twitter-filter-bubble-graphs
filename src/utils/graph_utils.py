import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

class GraphUtils:
    EDGE_COLORS = {-1: "#ff0000", 0: "#888888", 1: "#33cc33"}

    def __init__(self, data_loader):
        self.data_loader = data_loader
        self._layout_cache = {}

    def get_all_nodes(self, ego_id):
        _, feats_node_ids = self.data_loader.carregar_feats_e_ids(ego_id)
        node_ids = set(feats_node_ids)
        edges = self.data_loader.carregar_edges_db(ego_id)
        for u, v in edges:
            node_ids.add(u)
            node_ids.add(v)
        return sorted(node_ids)

    def build_graph_layout(self, ego_id, all_nodes):
        g_layout = nx.Graph()
        g_layout.add_nodes_from(all_nodes)
        valid_nodes = set(all_nodes)

        for u, v in self.data_loader.carregar_edges_db(ego_id):
            if u not in valid_nodes or v not in valid_nodes or u == v:
                continue
            if g_layout.has_edge(u, v):
                g_layout[u][v]["weight"] += 1.0
            else:
                g_layout.add_edge(u, v, weight=1.0)

        return g_layout

    def set_spring_layout(self, subgraph, seed_offset=0):
        n = max(2, subgraph.number_of_nodes())
        k = max(0.5, min(1.4, 2.8 / np.sqrt(n)))
        return nx.spring_layout(subgraph, seed=42 + seed_offset, k=k, iterations=500, weight="weight")

    def create_layout(self, ego_id, all_nodes):
        g_layout = self.build_graph_layout(ego_id, all_nodes)
        ug = g_layout.to_undirected() if g_layout.is_directed() else g_layout
        components = sorted(nx.connected_components(ug), key=len, reverse=True)
        if len(components) == 1:
            return self.set_spring_layout(g_layout)
        
        main_nodes = list(components[0])
        combined_pos = {}
        main_pos = self.set_spring_layout(g_layout.subgraph(main_nodes))
        for node, xy in main_pos.items():
            combined_pos[node] = np.array(xy, dtype=float)

        main_coords = np.array(list(main_pos.values()))
        main_x_min, main_y_min = main_coords.min(axis=0).tolist()
        main_x_max, main_y_max = main_coords.max(axis=0).tolist()
        main_span = max(main_x_max - main_x_min, main_y_max - main_y_min, 1e-6)
        main_cx = (main_x_min + main_x_max) / 2.0
        n_main = len(main_nodes)
        y_cursor = main_y_min
        for i, comp_nodes in enumerate(components[1:]):
            n_sub = len(comp_nodes)
            sub_half = max(n_sub / n_main, 0.05) * main_span / 2.0
            sub_pos = self.set_spring_layout(g_layout.subgraph(comp_nodes), seed_offset=i + 1)
            sub_coords = np.array(list(sub_pos.values()))
            sub_center = sub_coords.mean(axis=0)
            sub_span = max(
                float(sub_coords[:, 0].max() - sub_coords[:, 0].min()),
                float(sub_coords[:, 1].max() - sub_coords[:, 1].min()),
                1e-6,
            )
            sub_cy = y_cursor - sub_half * 0.5 - sub_half
            for node, xy in sub_pos.items():
                combined_pos[node] = np.array([
                    (xy[0] - sub_center[0]) / sub_span * sub_half + main_cx,
                    (xy[1] - sub_center[1]) / sub_span * sub_half + sub_cy,
                ])
            y_cursor = sub_cy - sub_half
            
        return combined_pos

    def get_layout(self, ego_id, graph):
        if ego_id not in self._layout_cache:
            all_nodes = self.get_all_nodes(ego_id)
            self._layout_cache[ego_id] = self.create_layout(ego_id, all_nodes)
        pos = self._layout_cache[ego_id]
        return {n: pos[n] for n in graph.nodes if n in pos}

    def set_node_color(self, ego_id, all_nodes):
        cluster_colors = self.get_cluster_colors(ego_id, all_nodes)
        
        if not cluster_colors:
            return {node: np.array([0.8, 0.8, 0.8]) for node in all_nodes}

        feat_clusters = self.data_loader.carregar_feat_clusters(ego_id)
        all_nodes_set = set(all_nodes)
        cluster_list = [
            (label, [m for m in members if m in all_nodes_set])
            for label, members in feat_clusters.items()
            if members
        ]

        node_color_groups = {node: [] for node in all_nodes}
        for label, members in cluster_list:
            for node in members:
                if label in cluster_colors:
                    node_color_groups[node].append(cluster_colors[label])

        node_colors = {}
        for node in all_nodes:
            if node_color_groups[node]:
                node_colors[node] = np.mean(node_color_groups[node], axis=0)
            else:
                node_colors[node] = np.array([0.8, 0.8, 0.8])

        return node_colors

    def get_cluster_colors(self, ego_id, all_nodes):
        feat_clusters = self.data_loader.carregar_feat_clusters(ego_id)
        all_nodes_set = set(all_nodes)
        cluster_list = [
            (label, [m for m in members if m in all_nodes_set])
            for label, members in feat_clusters.items()
            if members
        ]

        if not cluster_list:
            return {}

        cmap = plt.cm.get_cmap("tab20", max(len(cluster_list), 1))
        return {
            label: np.array(cmap(i)[:3])
            for i, (label, _) in enumerate(cluster_list)
        }

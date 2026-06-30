import sqlite3
from pathlib import Path

def create_tables(c):
    # usuários por networks
    c.execute('''CREATE TABLE IF NOT EXISTS user_ego_network (
                        usuario_id TEXT,
                        ego_network_id TEXT,
                        PRIMARY KEY (usuario_id, ego_network_id)
                    )''')

    # feats por ego-network
    c.execute('''CREATE TABLE IF NOT EXISTS feat (
                        feat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        feat_name TEXT,
                        ego_network_id TEXT
                    )''')

    # relacionamento usuário-feat por ego-network
    c.execute('''CREATE TABLE IF NOT EXISTS user_feat (
                        usuario_id TEXT,
                        feat_id INTEGER,
                        ego_network_id TEXT,
                        FOREIGN KEY (feat_id) REFERENCES feat(feat_id)
                    )''')

    # conexões entre usuários em uma network
    c.execute('''CREATE TABLE IF NOT EXISTS user_connections (
                        source_id TEXT,
                        target_id TEXT,
                        networks TEXT,
                        PRIMARY KEY (source_id, target_id)
                    )''')

    # featnames do ego da network
    c.execute('''CREATE TABLE IF NOT EXISTS egofeat (
                        ego_network_id TEXT PRIMARY KEY,
                        featnames TEXT
                    )''')

    # círculos (circles) das networks
    c.execute('''CREATE TABLE IF NOT EXISTS circle (
                        ego_network_id TEXT,
                        circle_name TEXT,
                        members TEXT,
                        PRIMARY KEY (ego_network_id, circle_name)
                    )''')

class DBDataLoader:
    def __init__(self, db_path):
        self.db_path = Path(db_path)

    def connect(self):
        return sqlite3.connect(self.db_path)

    def carregar_edges_db(self, ego_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT source_id, target_id FROM user_connections
                WHERE networks LIKE ?
            """, (f'%{ego_id}%',))
            return [(int(row[0]), int(row[1])) for row in cur.fetchall()]

    def carregar_feats_e_ids(self, ego_id):
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT feat_id FROM feat WHERE ego_network_id = ? ORDER BY feat_id
            """, (ego_id,))
            feat_ids = [row[0] for row in cur.fetchall()]
            if not feat_ids:
                return [], []

            cur.execute("""
                SELECT usuario_id FROM user_ego_network WHERE ego_network_id = ? ORDER BY usuario_id
            """, (ego_id,))
            node_ids = [int(row[0]) for row in cur.fetchall()]
            nodes_feats = []
            for uid in node_ids:
                cur.execute("""
                    SELECT feat_id FROM user_feat WHERE usuario_id = ? AND ego_network_id = ?
                """, (uid, ego_id))
                user_feats = set(row[0] for row in cur.fetchall())
                feats_bin = [1 if fid in user_feats else 0 for fid in feat_ids]
                nodes_feats.append(feats_bin)
            return nodes_feats, node_ids

    def carregar_featnames(self, ego_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT feat_name FROM feat WHERE ego_network_id = ? ORDER BY feat_id", (ego_id,))
            return [row[0] for row in cur.fetchall()]

    def carregar_egofeat(self, ego_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT feat_id FROM feat WHERE ego_network_id = ? ORDER BY feat_id", (ego_id,))
            feat_ids = [row[0] for row in cur.fetchall()]
            if not feat_ids:
                return []
            cur.execute("""
                SELECT uf.feat_id
                FROM user_feat uf
                WHERE uf.usuario_id = ? AND uf.ego_network_id = ?
            """, (ego_id, ego_id))
            ego_feats = set(row[0] for row in cur.fetchall())
            return [1 if fid in ego_feats else 0 for fid in feat_ids]

    def carregar_ego_ids_por_nos(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT ego_network_id
                FROM user_ego_network
                GROUP BY ego_network_id
                ORDER BY COUNT(usuario_id) ASC, ego_network_id
            """)
            return [int(row[0]) for row in cur.fetchall()]

    def carregar_circles(self, ego_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT circle_name, members FROM circle WHERE ego_network_id = ?",
                (ego_id,)
            )
            circles = {}
            for circle_name, members_str in cur.fetchall():
                if members_str:
                    circles[circle_name] = [int(m) for m in members_str.split(',') if m]
            return circles

    def carregar_feat_clusters(self, ego_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT f.feat_name, uf.usuario_id
                FROM user_feat uf
                JOIN feat f ON uf.feat_id = f.feat_id
                          AND f.ego_network_id = uf.ego_network_id
                WHERE uf.ego_network_id = ?
            """, (ego_id,))
            clusters: dict = {}
            for feat_name, user_id in cur.fetchall():
                label = feat_name
                if ' (' in label:
                    label = label[:label.index(' (')]
                parts = label.strip().split(' ', 1)
                label = parts[1].strip() if len(parts) == 2 and parts[0].isdigit() else label.strip()
                clusters.setdefault(label, []).append(int(user_id))
            return clusters

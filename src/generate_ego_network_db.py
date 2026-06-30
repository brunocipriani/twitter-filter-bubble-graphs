import os
import sqlite3
from collections import defaultdict

from utils.db_utils import create_tables
from utils.network_utils import get_ego_networks

DB_NAME = 'output/ego_network_users.db'

def main():
    # remove DB caso já exista
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    # conexão com DB
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # criar tabelas
    create_tables(c)

    # obter arquivos .edges por ego_id
    ego_files = get_ego_networks()

    combined_edges = defaultdict(set)

    for ego_file in ego_files:
        ego_id = os.path.splitext(os.path.basename(ego_file))[0]

        # cria arestas entre 2 usuários
        users = set()
        with open(ego_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    a, b = parts  # direcionado: a -> b
                    combined_edges[(a, b)].add(ego_id)
                    users.update(parts)

        # insere usuários na tabela user_ego_network
        for user in users:
            c.execute(
                'INSERT OR IGNORE INTO user_ego_network (usuario_id, ego_network_id) VALUES (?, ?)',
                (user, ego_id)
            )

        file_path = ego_file
        ego_dir = os.path.dirname(file_path)

        circles_path = os.path.join(ego_dir, f'{ego_id}.circles')

        # insere círculos da network na tabela circle
        if os.path.exists(circles_path):
            with open(circles_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        circle_name = parts[0]
                        members = ','.join(parts[1:])
                        c.execute(
                            '''INSERT OR REPLACE INTO circle (ego_network_id, circle_name, members) 
                            VALUES (?, ?, ?)''',
                            (ego_id, circle_name, members)
                        )
                    elif len(parts) == 1 and parts[0]:
                        # círculo sem membros
                        c.execute(
                            '''INSERT OR REPLACE INTO circle (ego_network_id, circle_name, members) 
                            VALUES (?, ?, ?)''',
                            (ego_id, parts[0], '')
                        )


        featnames_path = os.path.join(ego_dir, f'{ego_id}.featnames')
        feats_path = os.path.join(ego_dir, f'{ego_id}.feat')

        if os.path.exists(featnames_path) and os.path.exists(feats_path):
            featnames = []
            with open(featnames_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2:
                        featnames.append(parts[1])
                    else:
                        featnames.append(parts[0])

            # insere feats na tabela feat
            feat_ids = []
            for feat_name in featnames:
                c.execute('INSERT INTO feat (feat_name, ego_network_id) VALUES (?, ?)', (feat_name, ego_id))
                feat_ids.append(c.lastrowid)

            # insere feats dos usuários na tabela user_feat
            with open(feats_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 1:
                        usuario_id = parts[0]
                        feat_values = parts[1:]
                        for idx, val in enumerate(feat_values):
                            if val == '1':
                                c.execute(
                                    '''INSERT INTO user_feat (usuario_id, feat_id, ego_network_id) 
                                    VALUES (?, ?, ?)''',
                                          (usuario_id, feat_ids[idx], ego_id))
                                
        egofeat_path = os.path.join(ego_dir, f'{ego_id}.egofeat')

        # insere egofeat (feats do usuário central) para essa network
        if os.path.exists(egofeat_path) and os.path.exists(featnames_path):
            featnames = []
            with open(featnames_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2:
                        featnames.append(parts[1])
                    else:
                        featnames.append(parts[0])

            # lê vetor binário do .egofeat
            with open(egofeat_path, 'r', encoding='utf-8') as f:
                egofeat_bin = f.readline().strip().split()

            # filtra featnames presentes (binário 1)
            featnames_presentes = [fn for fn, val in zip(featnames, egofeat_bin) if val == '1']
            featnames_str = ','.join(featnames_presentes)
            c.execute('INSERT OR REPLACE INTO egofeat (ego_network_id, featnames) VALUES (?, ?)', (ego_id, featnames_str))

    # insere as edges acumuladas na tabela user_connections
    for (a, b), networks in combined_edges.items():
        networks_str = ','.join(sorted(networks))
        c.execute(
            'INSERT OR IGNORE INTO user_connections (source_id, target_id, networks) VALUES (?, ?, ?)',
            (a, b, networks_str)
        )

    conn.commit()
    conn.close()
    
    print(f'Banco de dados {DB_NAME} criado com sucesso!')

main()
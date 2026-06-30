import os

def get_ego_networks():
    # retorna os caminhos dos arquivos .edges por ego_id.
    ego_paths = {}
    if os.path.isdir('data/clustered'):
        for root, dirs, files in os.walk('data/clustered'):
            for f in files:
                if f.endswith('.edges'):
                    ego_id = os.path.splitext(f)[0]
                    ego_paths[ego_id] = os.path.join(root, f)
    return list(ego_paths.values())

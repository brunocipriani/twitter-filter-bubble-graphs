from pathlib import Path
import shutil
import os

from utils.lemma_utils import *

def process_ego_network(ego_id):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ego_dir = Path(current_dir).parent / 'data/raw' / str(ego_id)

    gemini_json = Path(current_dir).parent / 'data' / 'clusters_gemini' / f'{ego_id}.json'
    out_dir_name = 'clustered' if gemini_json.exists() else 'lemma'
    out_ego_dir = Path(current_dir).parent / f'data/{out_dir_name}' / str(ego_id)
    out_ego_dir.mkdir(parents=True, exist_ok=True)

    fn_file = ego_dir / f'{ego_id}.featnames'
    feat_file = ego_dir / f'{ego_id}.feat'
    egofeat_file = ego_dir / f'{ego_id}.egofeat'

    featnames = load_featnames(fn_file)
    feat_map, new_featnames = group_featnames(featnames)

    # Só aplica clusters se houver JSON do Gemini
    if gemini_json.exists():
        import json
        with open(gemini_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'clusters' in data:
            data = data['clusters']
        cluster_map = data
        # Normaliza featnames para comparação
        def norm(x):
            return clean(remove_id(x))
        # Cria um dicionário: cluster -> lista de featnames agrupados
        cluster_to_feats = {k: [] for k in cluster_map.keys()}
        # Para cada grupo, verifica se algum featname original está listado no cluster do JSON
        grouped_dict = {name: [] for name in new_featnames}
        for fn, name in feat_map.items():
            grouped_dict[name].append(fn)
        for group, origs in grouped_dict.items():
            for cluster, keywords in cluster_map.items():
                keywords_norm = set(norm(kw) for kw in keywords)
                if any(norm(f) in keywords_norm for f in origs):
                    cluster_to_feats[cluster].extend(origs)
                    break
        # Remove clusters vazios
        cluster_to_feats = {k: v for k, v in cluster_to_feats.items() if v}
        valid_groups = list(cluster_to_feats.keys())
        grouped_dict = cluster_to_feats
    else:
        # Sem clusters: só agrupa featnames normalmente
        grouped_dict = {name: [] for name in new_featnames}
        for fn, name in feat_map.items():
            grouped_dict[name].append(fn)
        valid_groups = [name for name in new_featnames if len(name) >= 2]

    col_map = {i: valid_groups.index(feat_map[fn]) for i, fn in enumerate(featnames) if fn in feat_map and feat_map[fn] in valid_groups}
    user_ids, new_feats = update_feats(feat_file, valid_groups, col_map)
    new_egofeat = update_egofeat(egofeat_file, valid_groups, col_map)

    featnames_out = []
    for idx, name in enumerate(valid_groups):
        grouped_no_id = ', '.join(sorted(set(remove_id(f) for f in grouped_dict[name] if len(clean(f)) >= 2)))
        if grouped_no_id:
            line = f"{idx} {name} ({grouped_no_id})"
        else:
            line = f"{idx} {name} ({remove_id(grouped_dict[name][0])})"
        featnames_out.append(line)

    save_featnames(out_ego_dir / f'{ego_id}.featnames', featnames_out)
    save_feats(out_ego_dir / f'{ego_id}.feat', new_feats, user_ids)
    save_egofeat(out_ego_dir / f'{ego_id}.egofeat', new_egofeat)

    for ext in ['edges', 'circles']:
        src = ego_dir / f'{ego_id}.{ext}'
        dst = out_ego_dir / f'{ego_id}.{ext}'
        if src.exists():
            shutil.copy(src, dst)

    print(f'Processamento concluído. Arquivos salvos em {out_ego_dir}')

def main():
    import sys
    import argparse
    from pathlib import Path

    current_dir = os.path.dirname(os.path.abspath(__file__))
    ego_dir = Path(current_dir).parent / 'data/raw'

    parser = argparse.ArgumentParser(description="Lematiza e agrupa featnames de ego networks.")
    parser.add_argument('ego_id', nargs='?', help='ID da ego network (omitir para processar todos)')
    args = parser.parse_args()

    if args.ego_id is None:
        ego_ids = [f.stem for f in ego_dir.glob('*/*.featnames')]
        if not ego_ids:
            print("Nenhum arquivo .featnames encontrado em 'data/raw/'.")
            sys.exit(1)

        print(f"Processando todos os ego_ids: {ego_ids}")
        for ego_id in ego_ids:
            process_ego_network(ego_id)
    else:
        process_ego_network(args.ego_id)

main()
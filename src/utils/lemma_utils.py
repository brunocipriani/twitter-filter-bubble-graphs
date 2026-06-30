import re
import numpy as np
import spacy

nlp = spacy.load("en_core_web_md")

# retorna forma lematizada de um texto
def lemmatize(text):
    doc = nlp(text)
    return " ".join([token.lemma_ for token in doc])

# limpa featname: remove id, converte para minúsculo e remove caracteres especiais
def clean(feat):
    txt = feat.split(' ', 1)[-1] if ' ' in feat else feat
    txt = txt.lower()
    txt = re.sub(r'[^\w]', '', txt)
    return txt

def remove_id(feat):
    return feat.split(' ', 1)[-1] if ' ' in feat else feat

# agrupa featnames por similaridade semântica
def group_featnames(featnames, sim_threshold=0.75):
    processed_featnames = []
    no_vector_featnames = []

    for f in featnames:
        cleaned = clean(f)

        # pula featnames curtos (com menos de 3 caracteres)
        if len(cleaned) < 3: 
            continue

        # obtém forma lematizada do featname limpo
        lemma = lemmatize(cleaned)

        # obtém vetor semântico do texto
        doc = nlp(lemma)

        # verifica se o vetor é válido
        if doc.vector_norm == 0:
            no_vector_featnames.append((f, lemma))
        else:
            processed_featnames.append((f, lemma, doc))

    filtered_featnames = [f for f, lemma, doc in processed_featnames]
    docs = {f: doc for f, lemma, doc in processed_featnames}
    lemmas = {f: lemma for f, lemma, doc in processed_featnames}

    groups = []
    used = set()

    # agrupa featnames com base na similaridade dos vetores semânticos
    for i, f1 in enumerate(filtered_featnames):
        if f1 in used:
            continue
        doc1 = docs[f1]
        group = [f1]
        for j, f2 in enumerate(filtered_featnames):
            if i != j and f2 not in used:
                doc2 = docs[f2]
                sim = doc1.similarity(doc2)
                if sim >= sim_threshold:
                    group.append(f2)
                    used.add(f2)
        used.add(f1)
        groups.append(group)

    feat_map = {}
    new_featnames = []

    # define nome representativo do grupo como o lematizado mais curto
    for group in groups:
        name = min([lemmas[f] for f in group], key=len)
        new_featnames.append(name)
        for f in group:
            feat_map[f] = name

    # para featnames sem vetor atribui o próprio texto como nome do grupo (grupo irá conter apenas ele mesmo)
    for f, lemma in no_vector_featnames:
        feat_map[f] = lemma
        if lemma not in new_featnames:
            new_featnames.append(lemma)

    return feat_map, new_featnames

# aplica mapeamento de clusters externos (Zenbrief)
def apply_cluster_overrides(feat_map: dict, new_featnames: list, cluster_map: dict) -> tuple:
    # filtra apenas labels que foram clusterizados
    label_remap = {label: cluster_map[label] for label in new_featnames if label in cluster_map}

    for fn in feat_map:
        old_label = feat_map[fn]
        if old_label in label_remap:
            feat_map[fn] = label_remap[old_label]

    seen: set = set()
    result: list = []
    for name in new_featnames:
        final = label_remap.get(name, name)
        if final not in seen:
            seen.add(final)
            result.append(final)

    return feat_map, result

# atualiza feats dos usuários com base nos grupos válidos e mapeamento de colunas
def update_feats(feat_file, valid_groups, col_map):
    user_ids, feats = load_feats(feat_file)
    new_feats = np.zeros((len(feats), len(valid_groups)), dtype=int)
    for i, row in enumerate(feats):
        for j, v in enumerate(row):
            if j in col_map and v == 1:
                new_feats[i, col_map[j]] = 1
    return user_ids, new_feats.tolist()

# atualiza egofeat com base nos grupos válidos e mapeamento de colunas
def update_egofeat(egofeat_file, valid_groups, col_map):
    egofeat = load_egofeat(egofeat_file)
    new_egofeat = [0] * len(valid_groups)
    for j, v in enumerate(egofeat):
        if j in col_map and v == 1:
            new_egofeat[col_map[j]] = 1
    return new_egofeat

# retorna mapping de featname original para nome do grupo clusterizado
def load_cluster_mapping(csv_path) -> dict:
    import csv
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row['Cluster Label'].strip().strip('"')
            keywords_str = row['Keywords'].strip().strip('"')
            for kw in keywords_str.split(';'):
                kw = kw.strip().lower()
                if kw:
                    mapping[kw] = label
    return mapping
        
def load_featnames(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f]

def load_feats(path):
    feats = []
    user_ids = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                user_ids.append(parts[0])
                feats.append(list(map(int, parts[1:])))
    return user_ids, feats

def load_egofeat(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(map(int, f.readline().strip().split()))

def save_featnames(path, featnames):
    with open(path, 'w', encoding='utf-8') as f:
        for fn in featnames:
            f.write(fn + '\n')

def save_feats(path, feats, user_ids):
    with open(path, 'w', encoding='utf-8') as f:
        for user_id, row in zip(user_ids, feats):
            f.write(user_id + ' ' + ' '.join(map(str, row)) + '\n')

def save_egofeat(path, egofeat):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(' '.join(map(str, egofeat)) + '\n')
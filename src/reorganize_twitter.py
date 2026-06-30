"""
Organiza arquivos da pasta 'raw' em subpastas nomeadas pelo ego-id
"""

import shutil
from pathlib import Path

def reorganize_twitter_folder(twitter_dir):
    twitter_dir = Path(twitter_dir)
    for file in twitter_dir.iterdir():
        if file.is_file():
            # Extrai o ID da file (antes do primeiro ponto)
            parts = file.name.split('.')
            if len(parts) > 1 and parts[0].isdigit():
                id_folder = twitter_dir / parts[0]
                id_folder.mkdir(exist_ok=True)
                dest = id_folder / file.name
                print(f"Movendo {file} para {dest}")
                shutil.move(str(file), str(dest))

def main():
    twitter_path = Path(__file__).parent.parent / "data/raw"
    reorganize_twitter_folder(twitter_path)
    print("Reorganização concluída.")

main()
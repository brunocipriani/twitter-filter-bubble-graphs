
import os
import sys
import argparse
from typing import Dict, List
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class ClusterSchema(BaseModel):
    clusters: Dict[str, List[str]] = Field(
        description="Dicionário onde a chave é o nome do cluster (categoria) e o valor é a lista de hashtags pertencentes a ele."
    )

client = genai.Client()

def main():

    parser = argparse.ArgumentParser(description="Classifica hashtags em clusters usando Gemini.")
    parser.add_argument("id", nargs="?", help="ID do arquivo na pasta exports (opcional se usar --all-exports)")
    parser.add_argument("--max-hashtags", type=int, default=None, help="Limite máximo de hashtags a enviar para a API (desabilite com --max-hashtags 0 ou omita para enviar todas)")
    parser.add_argument("--all-exports", action="store_true", help="Processa todos os arquivos .txt em data/exports/")
    args = parser.parse_args()

    def process_file(id_str):
        exports_path = os.path.join("data", "exports", f"{id_str}.txt")
        if not os.path.isfile(exports_path):
            print(f"Arquivo não encontrado: {exports_path}")
            return

        with open(exports_path, "r", encoding="utf-8") as f:
            hashtags_list = [line.strip() for line in f if line.strip()]

        if not hashtags_list:
            print(f"Nenhuma hashtag encontrada em {exports_path}")
            return

        # Limite de hashtags configurável
        if args.max_hashtags and args.max_hashtags > 0:
            if len(hashtags_list) > args.max_hashtags:
                print(f"Aviso: arquivo contém {len(hashtags_list)} hashtags. Limitando para as primeiras {args.max_hashtags}.")
                hashtags_list = hashtags_list[:args.max_hashtags]
        else:
            print(f"Enviando todas as {len(hashtags_list)} hashtags para a API Gemini...")

        print(f"Enviando {len(hashtags_list)} hashtags para a API Gemini...")
        print(f"Primeiras hashtags: {hashtags_list[:10]}")

        prompt_conteudo = f"""
Classifique a lista de hashtags fornecida em categorias lógicas para análise de grafos (como Ecossistema Microsoft, Big Techs, Mídia Tech, Localidades, etc.). 
Distribua todas as hashtags da lista no formato estruturado solicitado. Ignore as hashtags que não conseguir classificar. Seja conciso e direto, evitando explicações ou justificativas.

Lista de Hashtags:
{', '.join(hashtags_list)}
"""

        print("Chamando a API Gemini...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_conteudo,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        print("Resposta recebida da API.")

        output_dir = os.path.join('data', 'clusters_gemini')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'{id_str}.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f'Resultado salvo em: {output_path}')

    if args.all_exports:
        exports_dir = os.path.join("data", "exports")
        for filename in os.listdir(exports_dir):
            if filename.endswith(".txt"):
                id_str = os.path.splitext(filename)[0]
                print(f"\n=== Processando {filename} ===")
                process_file(id_str)
    else:
        if not args.id:
            print("Erro: forneça um ID ou use --all-exports.")
            sys.exit(1)
        process_file(args.id)


if __name__ == "__main__":
    main()

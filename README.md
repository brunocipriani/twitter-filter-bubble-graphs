## Como usar (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
.\pipeline.ps1

### Web
Abra `http://localhost:8000/web/interactive_graph.html` após execução do pipeline.
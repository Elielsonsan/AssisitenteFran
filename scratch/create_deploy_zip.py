import os
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_NAME = os.path.join(BASE_DIR, "Assistente_Fran_Deploy.zip")

INCLUDE_FILES = [
    "app.py",
    "guia_fle_data.py",
    "requirements.txt",
    "deploy_gcp.sh",
    "assistente_fran.db",
    "database_setup.py",
    "seed_planos_aula.py",
    "seed_populacao_graficos.py"
]

INCLUDE_DIRS = [
    "templates",
    "static",
    "imagens"
]

print(f"Compactando projeto em: {ZIP_NAME}")

with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zf:
    for filename in INCLUDE_FILES:
        filepath = os.path.join(BASE_DIR, filename)
        if os.path.exists(filepath):
            zf.write(filepath, filename)
            print(f"  + Arquivo: {filename}")

    for dirname in INCLUDE_DIRS:
        dirpath = os.path.join(BASE_DIR, dirname)
        if os.path.exists(dirpath):
            for root, dirs, files in os.walk(dirpath):
                # Ignorar __pycache__
                if "__pycache__" in root:
                    continue
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    zf.write(full_path, rel_path)
            print(f"  + Pasta: {dirname}/")

zip_size_mb = os.path.getsize(ZIP_NAME) / (1024 * 1024)
print(f"\n✓ Arquivo criado com sucesso! Tamanho: {zip_size_mb:.2f} MB")

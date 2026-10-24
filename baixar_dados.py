import os
import zipfile
from pathlib import Path
import gdown

# Definição dos caminhos base
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Link da pasta pública no Google Drive
DRIVE_URL = "https://drive.google.com/drive/folders/1b9Yc_s9gm6TAERY3BjOw2bixu70X3tZL?usp=sharing"

# Ficheiros CSV esperados conforme os requisitos do projeto
ARQUIVOS_ESPERADOS = [
    "2025_Viagem.csv",
    "2025_Pagamento.csv",
    "2025_Passagem.csv",
    "2025_Trecho.csv"
]


def descompactar_zips(diretorio: Path) -> None:
    """Procura ficheiros .zip no diretório e extrai todos os conteúdos."""
    zips_encontrados = list(diretorio.glob("*.zip"))
    if not zips_encontrados:
        print("ℹ️  Nenhum ficheiro compactado (.zip) encontrado para extrair.")
        return

    for arquivo_zip in zips_encontrados:
        print(f"📦 Extraindo {arquivo_zip.name}...")
        try:
            with zipfile.ZipFile(arquivo_zip, "r") as zip_ref:
                zip_ref.extractall(diretorio)
            print(f"✅ Conteúdo de {arquivo_zip.name} extraído com sucesso!")
        except zipfile.BadZipFile:
            print(f"❌ Erro: {arquivo_zip.name} é um ficheiro ZIP corrompido ou inválido.")


def validar_arquivos_extraidos(diretorio: Path) -> None:
    """Verifica e lista os CSVs disponíveis no diretório."""
    print("\n📋 Verificando ficheiros na pasta 'data/':")
    arquivos_atuais = {item.name for item in diretorio.iterdir() if item.is_file()}

    todos_presentes = True
    for esperado in ARQUIVOS_ESPERADOS:
        if esperado in arquivos_atuais:
            tamanho_mb = (diretorio / esperado).stat().st_size / (1024 * 1024)
            print(f"  ✔️  {esperado} ({tamanho_mb:.2f} MB)")
        else:
            print(f"  ⚠️  Faltando: {esperado}")
            todos_presentes = False

    if todos_presentes:
        print("\n🚀 Todos os 4 ficheiros CSV necessários estão prontos para a Camada Raw!")
    else:
        print("\n⚠️  Atenção: Nem todos os ficheiros esperados foram localizados.")


def extrair_dados() -> None:
    """Executa o download e a extração dos ficheiros de dados."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("🚀 [Início] Pipeline de Extração de Dados")
    print(f"📂 Diretório de destino: {DATA_DIR}")

    try:
        print("⬇️  Descarregando ficheiros do Google Drive via gdown...")
        gdown.download_folder(
            url=DRIVE_URL,
            output=str(DATA_DIR),
            quiet=False,
            use_cookies=False
        )
        print("✅ Download concluído com sucesso!")

        # Extração de zips se houver
        descompactar_zips(DATA_DIR)

        # Validação final dos ficheiros CSV
        validar_arquivos_extraidos(DATA_DIR)

    except Exception as erro:
        print(f"\n❌ Falha durante a extração: {erro}")
        print("💡 Dica: Se o Google Drive bloquear por cota temporária, faça o download direto pelo navegador e salve os 4 CSVs dentro da pasta 'data/'.")


if __name__ == "__main__":
    extrair_dados()
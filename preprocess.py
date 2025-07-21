# preprocess.py (Versão Otimizada para Produção)
import os
import shutil
import gdown

# --- CONFIGURAÇÃO ---
# URL da sua pasta no Google Drive que contém os arquivos PARQUET
URL_PASTA_PARQUET_DRIVE = 'https://drive.google.com/drive/u/0/folders/1NTLOk60QFLcCGaXD_IEtg7LR4nuW__gc'

# Pasta final onde os Parquets serão salvos no servidor
PASTA_PARQUET_SAIDA = 'data_processed'

def executar_pipeline_completo():
    """
    Pipeline simplificado: Apenas baixa os arquivos Parquet já processados do Google Drive.
    """
    print("--- Iniciando pipeline de dados otimizado ---")
    
    # Garante que não há dados antigos, limpando execuções anteriores
    if os.path.exists(PASTA_PARQUET_SAIDA):
        shutil.rmtree(PASTA_PARQUET_SAIDA)
        print(f"Diretório antigo '{PASTA_PARQUET_SAIDA}' removido.")
    
    os.makedirs(PASTA_PARQUET_SAIDA)
    print(f"Diretório de saída '{PASTA_PARQUET_SAIDA}' criado.")
    
    print(f"Baixando arquivos Parquet pré-processados...")
    try:
        # Baixa os arquivos diretamente para a pasta de saída
        gdown.download_folder(URL_PASTA_PARQUET_DRIVE, output=PASTA_PARQUET_SAIDA, quiet=False)
        print("Arquivos Parquet baixados com sucesso.")
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao baixar os arquivos Parquet do Google Drive.")
        print(f"Detalhe do erro: {e}")
        # Se falhar aqui, a aplicação não poderá iniciar
        raise e

    print("--- Pipeline de dados otimizado finalizado. ---")

if __name__ == '__main__':
    # Permite que você teste o script localmente rodando 'python preprocess.py'
    executar_pipeline_completo()
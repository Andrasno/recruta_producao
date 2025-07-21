import os
import json
import pandas as pd
import gdown
import shutil

# --- CONFIGURAÇÃO CENTRAL ---
# URL da pasta no Google Drive que contém os arquivos JSON
URL_PASTA_DRIVE = 'https://drive.google.com/drive/u/0/folders/1Bl-bjq9PgNLymcJD1nNmw7G0UU_EFURf'

# Define os nomes das pastas que serão usadas. Usar variáveis torna o código mais limpo.
PASTA_JSON_TEMP = 'json_temp'      # Pasta temporária para baixar os JSONs
PASTA_PARQUET_SAIDA = 'data_processed' # Pasta final para salvar os arquivos Parquet

def baixar_e_preparar_dados():
    """
    Orquestra o download dos dados do Google Drive e a preparação das pastas.
    Retorna True se bem-sucedido, False caso contrário.
    """
    print("--- Etapa 1: Baixando dados do Google Drive ---")
    
    # Garante que não há dados antigos, limpando execuções anteriores
    if os.path.exists(PASTA_JSON_TEMP):
        shutil.rmtree(PASTA_JSON_TEMP)
    
    os.makedirs(PASTA_JSON_TEMP)
    
    try:
        gdown.download_folder(URL_PASTA_DRIVE, output=PASTA_JSON_TEMP, quiet=False)
        print("Download concluído com sucesso.")
        return True
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao baixar os arquivos do Google Drive. A aplicação não pode continuar.")
        print(f"Detalhe do erro: {e}")
        return False

def processar_e_salvar_arquivos():
    """
    Lê os arquivos JSON baixados, processa-os com pandas e salva como Parquet.
    """
    print("\n--- Etapa 2: Processando arquivos JSON para Parquet ---")

    # Caminhos completos para os arquivos JSON baixados
    vagas_path = os.path.join(PASTA_JSON_TEMP, 'vagas.json')
    prospects_path = os.path.join(PASTA_JSON_TEMP, 'prospects.json')
    applicants_path = os.path.join(PASTA_JSON_TEMP, 'applicants.json')

    def carregar_json(filepath):
        # Sua função original, agora lendo da pasta temporária
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERRO: Arquivo esperado não foi encontrado em '{filepath}'. Verifique se o arquivo existe no Google Drive.")
            return None
        except Exception as e:
            print(f"Erro ao carregar {filepath}: {e}")
            return None

    # Carregar todos os dados
    dados_vagas = carregar_json(vagas_path)
    dados_prospects = carregar_json(prospects_path)
    dados_applicants = carregar_json(applicants_path)

    if not all([dados_vagas, dados_prospects, dados_applicants]):
        print("Processamento interrompido: um ou mais arquivos JSON não puderam ser carregados.")
        return

    # --- Sua lógica de processamento original (mantida intacta) ---
    vagas_list = [ {'id_vaga': id_vaga, **detalhes.get('informacoes_basicas', {}), **detalhes.get('perfil_vaga', {})} for id_vaga, detalhes in dados_vagas.items() ]
    df_vagas = pd.DataFrame(vagas_list)
    
    prospects_list = [ {'id_vaga': id_vaga, **prospect} for id_vaga, detalhes in dados_prospects.items() for prospect in detalhes.get('prospects', []) ]
    df_prospects = pd.DataFrame(prospects_list)
    if 'codigo' in df_prospects.columns:
        df_prospects['codigo'] = df_prospects['codigo'].astype(str)

    applicants_list = []
    for id_candidato, informacoes in dados_applicants.items():
        registro = {'id_candidato': str(id_candidato)}
        for secao, valores in informacoes.items():
            if isinstance(valores, dict): registro.update(valores)
            else: registro[secao] = valores
        applicants_list.append(registro)
    df_applicants = pd.DataFrame(applicants_list)
    
    # --- Fim da lógica original ---

    # Cria a pasta de saída se ela não existir
    if not os.path.exists(PASTA_PARQUET_SAIDA):
        os.makedirs(PASTA_PARQUET_SAIDA)

    # Salvar os DataFrames processados na pasta de saída
    df_vagas.to_parquet(os.path.join(PASTA_PARQUET_SAIDA, 'vagas.parquet'))
    df_prospects.to_parquet(os.path.join(PASTA_PARQUET_SAIDA, 'prospects.parquet'))
    df_applicants.to_parquet(os.path.join(PASTA_PARQUET_SAIDA, 'applicants.parquet'))

    print("\nDados pré-processados e salvos com sucesso em:")
    print(f"- {os.path.join(PASTA_PARQUET_SAIDA, 'vagas.parquet')}")
    print(f"- {os.path.join(PASTA_PARQUET_SAIDA, 'prospects.parquet')}")
    print(f"- {os.path.join(PASTA_PARQUET_SAIDA, 'applicants.parquet')}")

def limpar_arquivos_temporarios():
    """
    Remove a pasta temporária com os arquivos JSON para liberar espaço.
    """
    print("\n--- Etapa 3: Limpando arquivos temporários ---")
    if os.path.exists(PASTA_JSON_TEMP):
        shutil.rmtree(PASTA_JSON_TEMP)
        print(f"Pasta '{PASTA_JSON_TEMP}' removida com sucesso.")

def executar_pipeline_completo():
    """
    Função principal que orquestra todo o pipeline de pré-processamento.
    """
    if baixar_e_preparar_dados():
        processar_e_salvar_arquivos()
        limpar_arquivos_temporarios()
    print("\n--- Pipeline de pré-processamento finalizado. ---")


if __name__ == "__main__":
    # Este bloco será executado quando você rodar 'python preprocess.py'
    executar_pipeline_completo()
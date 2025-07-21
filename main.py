import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Dict, Any

# Importa o Middleware de CORS para permitir a comunicação com o frontend
from fastapi.middleware.cors import CORSMiddleware

# Importa a função para carregar o arquivo .env
from dotenv import load_dotenv

# Importa nosso logger configurado para gerar logs estruturados
from logger_config import logger

# Imports do nosso módulo de agente, que contém a lógica principal
from agent import BaseDeDados, AgenteScreener, AgenteEntrevistador

# Imports para o LLM
from llama_index.llms.groq import Groq

# --- MUDANÇA: Importa a função de pipeline e a variável de pasta do nosso script de pré-processamento
from preprocess import executar_pipeline_completo, PASTA_PARQUET_SAIDA

# Carrega as variáveis do arquivo .env para o ambiente do sistema
load_dotenv()

# --- Modelos de Dados da API (Pydantic) ---
# Define como devem ser os dados que chegam e saem da API
class PredictRequest(BaseModel):
    session_id: str
    user_input: str

class PredictResponse(BaseModel):
    session_id: str
    agent_reply: str

# --- Variáveis Globais e Ciclo de Vida da API ---
# O dicionário 'state' irá conter objetos que vivem durante toda a execução da API
state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Função que gerencia o ciclo de vida da API.
    O código aqui roda QUANDO A API INICIA.
    """
    logger.info("API do Agente Decision iniciando...")
    
    # --- MUDANÇA: Executa todo o pipeline de download e processamento ANTES de carregar a base.
    # Isso garante que os arquivos Parquet existirão quando a aplicação tentar usá-los.
    executar_pipeline_completo()
    
    # --- MUDANÇA: Constrói os caminhos para os arquivos Parquet usando a pasta de saída correta.
    caminho_vagas = os.path.join(PASTA_PARQUET_SAIDA, 'vagas.parquet')
    caminho_prospects = os.path.join(PASTA_PARQUET_SAIDA, 'prospects.parquet')
    caminho_applicants = os.path.join(PASTA_PARQUET_SAIDA, 'applicants.parquet')

    # 1. Carrega a base de dados a partir dos arquivos Parquet pré-processados
    logger.info(f"Carregando base de dados dos arquivos em '{PASTA_PARQUET_SAIDA}'...")
    state['db'] = BaseDeDados(
        vagas_path=caminho_vagas,
        prospects_path=caminho_prospects,
        applicants_path=caminho_applicants
    )
    
    # 2. Carrega a chave da API do ambiente (arquivo .env) e inicializa o LLM
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        logger.critical("A chave da API da Groq não foi encontrada. A aplicação será encerrada.")
        raise ValueError("Defina GROQ_API_KEY no seu arquivo .env")
        
    state['llm'] = Groq(model="llama-3.3-70b-versatile", api_key=api_key)
    
    # 3. Cria um dicionário para armazenar as sessões de conversa ativas
    state['sessions'] = {}
    
    logger.info("API iniciada e pronta para receber requisições.")
    
    yield  # A API fica rodando aqui
    
    # Código que roda QUANDO A API ENCERRA (limpeza)
    logger.info("API encerrando.")
    state.clear()

# --- O restante do seu arquivo permanece exatamente o mesmo ---
# --- Criação da Aplicação FastAPI ---
app = FastAPI(
    title="Decision Recrutamento AI",
    description="API para interagir com o agente de recrutamento inteligente.",
    version="2.0.0",
    lifespan=lifespan
)

# Habilita o CORS... (código idêntico)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints da API ---
@app.post("/predict", response_model=PredictResponse, summary="Interage com o agente de recrutamento")
async def predict(request: PredictRequest):
    # ... (código do endpoint idêntico)
    start_time = time.time()
    session_id = request.session_id
    user_input = request.user_input
    
    logger.info("Requisição recebida", extra={"session_id": session_id, "input_length": len(user_input)})

    try:
        if session_id not in state['sessions']:
            vagas_encontradas = state['db'].buscar_vaga_por_texto(user_input)
            if vagas_encontradas.empty:
                logger.warning("Vaga não encontrada na busca inicial", extra={"query": user_input, "session_id": session_id})
                return PredictResponse(session_id=session_id, agent_reply="Peço desculpas, mas no momento não encontrei um processo seletivo com este nome. Agradeço seu interesse!")
            
            vaga_confirmada = vagas_encontradas.iloc[0]
            logger.info("Vaga Identificada", extra={
                "session_id": session_id, "id_vaga": vaga_confirmada.get('id_vaga'),
                "titulo_vaga": vaga_confirmada.get('titulo_vaga'), "nivel_profissional": vaga_confirmada.get('nivel profissional')
            })
            
            state['sessions'][session_id] = {"state": "AWAITING_CANDIDATE_NAME", "vaga_info": vaga_confirmada}
            return PredictResponse(session_id=session_id, agent_reply=f"Excelente! Encontrei a vaga '{vaga_confirmada['titulo_vaga']}'. Para continuarmos, por favor, me informe seu nome completo.")

        current_session = state['sessions'][session_id]
        
        if current_session['state'] == "AWAITING_CANDIDATE_NAME":
            vaga_info = current_session['vaga_info']
            candidato_existente = state['db'].buscar_candidato_em_vaga(user_input, vaga_info['id_vaga'])
            
            if candidato_existente is None:
                logger.info("Novo candidato detectado", extra={"session_id": session_id, "nome_informado": user_input})
                current_session['agent'] = AgenteScreener(vaga_info=vaga_info, nome_candidato=user_input, llm_instance=state['llm'])
                current_session['state'] = "IN_CONVERSATION"
                agent_reply = current_session['agent'].conversar("Por favor, inicie a entrevista de triagem se apresentando.")
            else:
                id_candidato = candidato_existente['codigo']
                logger.info("Candidato existente localizado", extra={"session_id": session_id, "codigo_candidato": id_candidato})
                dossie = state['db'].get_dossie_entrevista(vaga_info['id_vaga'], id_candidato)
                if dossie is None: raise HTTPException(status_code=500, detail="Erro ao montar dossiê para candidato existente.")
                current_session['agent'] = AgenteEntrevistador(dossie=dossie, llm_instance=state['llm'])
                current_session['state'] = "IN_CONVERSATION"
                agent_reply = current_session['agent'].conversar("Por favor, inicie a entrevista aprofundada se apresentando.")

            return PredictResponse(session_id=session_id, agent_reply=agent_reply)

        elif current_session['state'] == "IN_CONVERSATION":
            agent = current_session['agent']
            agent_reply = agent.conversar(user_input)
            return PredictResponse(session_id=session_id, agent_reply=agent_reply)

        else:
            raise HTTPException(status_code=500, detail="Estado da sessão inválido.")

    except Exception as e:
        logger.error("Erro inesperado no endpoint /predict", extra={"session_id": session_id, "detalhe_erro": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno no servidor.")
    finally:
        duration = time.time() - start_time
        logger.info("Requisição finalizada", extra={"session_id": session_id, "duration_ms": round(duration * 1000, 2)})

@app.get("/", summary="Endpoint de status", include_in_schema=False)
async def root():
    return {"message": "API do Agente de Recrutamento da Decision está online."}
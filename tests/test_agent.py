# tests/test_agent.py

import pytest
import pandas as pd
from unittest.mock import MagicMock

# Importa as classes do seu projeto que vamos testar
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent import BaseDeDados, AgenteScreener, AgenteEntrevistador
from llama_index.core.llms import ChatMessage # Importar para usar no 'spec' do mock

# --- Dados Falsos (Mocks) para os Testes ---

@pytest.fixture
def mock_db():
    """Cria uma instância falsa da BaseDeDados com dados pré-definidos."""
    db = MagicMock(spec=BaseDeDados)
    
    vagas_data = {
        'id_vaga': ['v01', 'v02'],
        'titulo_vaga': ['Engenheiro de Software', 'Cientista de Dados'],
        'competencia_tecnicas_e_comportamentais': ['Python, Docker, AWS', 'Python, R, SQL, aima'],
        'cliente': ['Empresa A', 'Empresa B']
    }
    db.df_vagas = pd.DataFrame(vagas_data)

    candidatos_data = {
        'id_vaga': ['v01', 'v01', 'v02'],
        'nome': ['João Silva', 'Maria Souza', 'Carlos Pereira'],
        'codigo': ['c001', 'c002', 'c003'],
        'situacao_candidado': ['Prospect', 'Entrevista Agendada', 'Prospect'],
        'conhecimentos_tecnicos': ['Python, Java', 'Python, Docker', 'SQL, aima']
    }
    db.df_candidatos = pd.DataFrame(candidatos_data)
    
    dossie_data = {
        'titulo_vaga': 'Engenheiro de Software', 'cliente': 'Empresa A',
        'competencia_tecnicas_e_comportamentais': 'Python, Docker, AWS', 'nome': 'Maria Souza',
        'conhecimentos_tecnicos': 'Python, Docker', 'situacao_candidado': 'Entrevista Agendada'
    }
    db.get_dossie_entrevista.return_value = pd.Series(dossie_data)

    def buscar_vaga_side_effect(texto):
        if "Software" in texto: return db.df_vagas[db.df_vagas['id_vaga'] == 'v01']
        return pd.DataFrame()

    def buscar_candidato_side_effect(nome, id_vaga):
        if "Maria" in nome and id_vaga == 'v01': return db.df_candidatos[db.df_candidatos['codigo'] == 'c002'].iloc[0]
        return None
    
    db.buscar_vaga_por_texto.side_effect = buscar_vaga_side_effect
    db.buscar_candidato_em_vaga.side_effect = buscar_candidato_side_effect
    return db

@pytest.fixture
def mock_llm():
    """
    Cria um LLM falso que não faz chamadas de API.
    CORREÇÃO: Agora o mock da mensagem também inclui o atributo 'role'.
    """
    llm = MagicMock()
    
    # Cria um mock da mensagem da IA, imitando a estrutura real do objeto ChatMessage
    mock_ai_message = MagicMock(spec=ChatMessage)
    mock_ai_message.role = "assistant"  # <-- A LINHA QUE CORRIGE O ERRO
    mock_ai_message.content = "Esta é uma resposta simulada do LLM."

    # Cria o mock da resposta do chat, que contém a mensagem da IA
    mock_chat_response = MagicMock()
    mock_chat_response.message = mock_ai_message

    # Configura o método 'chat' do LLM para retornar nossa resposta simulada
    llm.chat.return_value = mock_chat_response
    return llm

# --- Testes Unitários (sem alterações a partir daqui) ---

def test_base_de_dados_busca_vaga(mock_db):
    """Testa se a BaseDeDados consegue encontrar uma vaga pelo título."""
    resultado = mock_db.buscar_vaga_por_texto("Engenheiro Software")
    assert not resultado.empty
    assert resultado.iloc[0]['id_vaga'] == 'v01'
    print("\n✅ Teste 'test_base_de_dados_busca_vaga' passou.")

def test_base_de_dados_busca_candidato_existente(mock_db):
    """Testa se a BaseDeDados encontra um candidato existente associado a uma vaga."""
    resultado = mock_db.buscar_candidato_em_vaga("Maria", "v01")
    assert resultado is not None
    assert resultado['codigo'] == 'c002'
    print("✅ Teste 'test_base_de_dados_busca_candidato_existente' passou.")


def test_agente_screener_cria_prompt_correto(mock_llm):
    """Verifica se o AgenteScreener (para novos candidatos) monta o prompt do sistema corretamente."""
    vaga_info = pd.Series({'titulo_vaga': 'Engenheiro de Software', 'competencia_tecnicas_e_comportamentais': 'Python, Docker'})
    agente = AgenteScreener(vaga_info=vaga_info, nome_candidato="Candidato Novo", llm_instance=mock_llm)
    
    assert "NOVO candidato" in agente.conversation_history[0].content
    assert "Engenheiro de Software" in agente.conversation_history[0].content
    assert "Candidato Novo" in agente.conversation_history[0].content
    print("✅ Teste 'test_agente_screener_cria_prompt_correto' passou.")

def test_agente_entrevistador_cria_prompt_correto(mock_db, mock_llm):
    """Verifica se o AgenteEntrevistador (para candidatos conhecidos) monta o prompt com o dossiê."""
    dossie = mock_db.get_dossie_entrevista("v01", "c002")
    agente = AgenteEntrevistador(dossie=dossie, llm_instance=mock_llm)

    assert "entrevista APROFUNDADA" in agente.conversation_history[0].content
    assert "Maria Souza" in agente.conversation_history[0].content
    assert "Engenheiro de Software" in agente.conversation_history[0].content
    assert "Python, Docker" in agente.conversation_history[0].content
    print("✅ Teste 'test_agente_entrevistador_cria_prompt_correto' passou.")

def test_agente_conversar_chama_llm_e_atualiza_historico(mock_llm):
    """Testa se o método 'conversar' chama a API mockada e atualiza o histórico."""
    vaga_info = pd.Series({'titulo_vaga': 'Analista de BI'})
    agente = AgenteScreener(vaga_info=vaga_info, nome_candidato="Teste", llm_instance=mock_llm)
    
    assert len(agente.conversation_history) == 1
    resposta_agente = agente.conversar("Olá, tenho interesse na vaga.")
    
    assert resposta_agente == "Esta é uma resposta simulada do LLM."
    mock_llm.chat.assert_called_once()
    assert len(agente.conversation_history) == 3
    assert agente.conversation_history[1].role == "user"
    assert agente.conversation_history[2].role == "assistant"
    print("✅ Teste 'test_agente_conversar_chama_llm_e_atualiza_historico' passou.")
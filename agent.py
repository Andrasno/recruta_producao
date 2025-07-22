import pandas as pd
from llama_index.llms.groq import Groq
from llama_index.core.llms import ChatMessage
from functools import lru_cache

def otimizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas do tipo 'object' para 'category' para economizar memória."""
    for col in df.select_dtypes(include=['object']).columns:
        # Apenas converte colunas se o número de categorias for menor que 50% do total de linhas
        # Isso evita converter colunas com muitos valores únicos (como IDs ou nomes completos)
        if df[col].nunique() / len(df) < 0.5:
            df[col] = df[col].astype('category')
    return df

class BaseDeDados:
    """
    Carrega os dados PRÉ-PROCESSADOS (Parquet) e serve como a interface
    de conhecimento para o agente.
    """
    def __init__(self, vagas_path, prospects_path, applicants_path):
        print("Carregando base de dados pré-processada...")
        # Carrega os arquivos Parquet
        df_vagas_raw = pd.read_parquet(vagas_path)
        df_prospects_raw = pd.read_parquet(prospects_path)
        df_applicants_raw = pd.read_parquet(applicants_path)
        
        print("Otimizando uso de memória dos DataFrames...")
        # Otimiza cada DataFrame para economizar RAM
        self.df_vagas = otimizar_dataframe(df_vagas_raw)
        self.df_prospects = otimizar_dataframe(df_prospects_raw)
        self.df_applicants = otimizar_dataframe(df_applicants_raw)
        
        print("Base de Dados pronta para uso.")
        # Loga o uso de memória para diagnóstico (útil para ver o resultado da otimização)
        print(f"Uso de memória - Vagas: {self.df_vagas.memory_usage(deep=True).sum() / 1e6:.2f} MB")
        print(f"Uso de memória - Prospects: {self.df_prospects.memory_usage(deep=True).sum() / 1e6:.2f} MB")
        print(f"Uso de memória - Applicants: {self.df_applicants.memory_usage(deep=True).sum() / 1e6:.2f} MB")

    @lru_cache(maxsize=128)
    def buscar_vaga_por_texto(self, texto_busca):
        stop_words = ['vaga', 'de', 'para', 'a', 'o']
        keywords = [word for word in texto_busca.lower().split() if word not in stop_words]
        if not keywords: return pd.DataFrame()
        mask = pd.Series([True] * len(self.df_vagas))
        for keyword in keywords:
            mask &= self.df_vagas['titulo_vaga'].str.contains(keyword, case=False, na=False)
        return self.df_vagas[mask]

    def buscar_candidato_em_vaga(self, nome_candidato, id_vaga):
        prospects_da_vaga = self.df_prospects[self.df_prospects['id_vaga'] == id_vaga]
        if prospects_da_vaga.empty: return None
        mask = prospects_da_vaga['nome'].str.contains(nome_candidato, case=False, na=False)
        candidato_encontrado = prospects_da_vaga[mask]
        return candidato_encontrado.iloc[0] if not candidato_encontrado.empty else None

    def get_dossie_entrevista(self, id_vaga, id_candidato):
        vaga_info = self.df_vagas[self.df_vagas['id_vaga'] == id_vaga]
        prospect_info = self.df_prospects[(self.df_prospects['id_vaga'] == id_vaga) & (self.df_prospects['codigo'] == id_candidato)]
        applicant_info = self.df_applicants[self.df_applicants['id_candidato'] == id_candidato]
        if vaga_info.empty or applicant_info.empty: return None
        info_completa = {**vaga_info.iloc[0].to_dict(), **applicant_info.iloc[0].to_dict(), **prospect_info.iloc[0].to_dict()}
        return pd.Series(info_completa)

class AgenteAbstrato:
    """Classe base para os agentes, contendo a lógica de chat."""
    def __init__(self, llm_instance: Groq, system_prompt: str):
        self.llm = llm_instance
        self.conversation_history = [ChatMessage(role="system", content=system_prompt)]

    def conversar(self, user_input: str):
        self.conversation_history.append(ChatMessage(role="user", content=user_input))
        response = self.llm.chat(self.conversation_history)
        ai_message = response.message
        self.conversation_history.append(ai_message)
        return ai_message.content

class AgenteScreener(AgenteAbstrato):
    """Agente para entrevistar NOVOS candidatos."""
    def __init__(self, vaga_info: pd.Series, nome_candidato: str, llm_instance: Groq):
        SYSTEM_PROMPT = f"""
        Você é "Alex", um recrutador de IA da Decision. Sua missão é realizar a primeira triagem (screening) de um NOVO candidato.
        **CONTEXTO:**
        - Nome do Candidato: {nome_candidato}
        - Vaga de Interesse: {vaga_info.get('titulo_vaga', 'N/A')}
        **SEU PLANO DE TRIAGEM:**
        1. Pergunte sobre as principais tecnologias que ele(a) domina e os anos de experiência.
        2. Pergunte sobre nível de inglês, pretensão salarial e modalidade de trabalho.
        3. Pergunte por que ele(a) se interessou por esta vaga.
        Ao final, agradeça e gere o resumo JSON com os dados coletados.
        """
        super().__init__(llm_instance, SYSTEM_PROMPT)

class AgenteEntrevistador(AgenteAbstrato):
    """Agente para entrevistas APROFUNDADAS com candidatos JÁ CONHECIDOS."""
    def __init__(self, dossie: pd.Series, llm_instance: Groq):
        SYSTEM_PROMPT = f"""
        Você é "Alex", um entrevistador de IA sênior da Decision. Sua missão é conduzir uma entrevista APROFUNDADA com um candidato já conhecido.
        **SEU DOSSIÊ:**
        - Vaga: {dossie.get('titulo_vaga', 'N/A')}
        - Candidato: {dossie.get('nome', 'N/A')}
        - Conhecimentos já listados: {dossie.get('conhecimentos_tecnicos', 'N/A')}
        **SEU PLANO:**
        Valide a Análise Técnica, o Fit Cultural e o Engajamento. Faça perguntas aprofundadas baseadas no dossiê. Ao final, agradeça e gere o resumo JSON.
        """
        super().__init__(llm_instance, SYSTEM_PROMPT)
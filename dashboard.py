import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(layout="wide", page_title="Dashboard de Monitoramento - Decision AI")

st.title("Painel de Monitoramento do Agente de Recrutamento")
st.markdown("Este painel analisa os logs da API para monitorar o comportamento e detectar drifts de dados.")

LOG_FILE = "app_logs.log"

@st.cache_data(ttl=10) # Reduzi o tempo de cache para atualizações mais rápidas
def load_data(log_file_path):
    """Lê e processa o arquivo de log JSON para um DataFrame."""
    log_entries = []
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue # Ignora linhas que não são JSON válido
        df = pd.DataFrame(log_entries)
        # Converte a coluna de tempo para o formato datetime, se ela existir
        if 'asctime' in df.columns:
            df['timestamp'] = pd.to_datetime(df['asctime'])
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data(LOG_FILE)

if df.empty:
    st.warning("Nenhum dado de log encontrado. Use a API para gerar logs e este painel será atualizado.")
else:
    # --- Métricas Gerais ---
    st.subheader("Métricas Gerais de Uso")
    
    total_reqs = len(df[df['message'] == 'Requisição finalizada'])
    total_erros = len(df[df['levelname'] == 'ERROR'])

    # CORREÇÃO: Lógica defensiva para calcular a duração média
    avg_duration = 0.0
    # 1. Verifica se a coluna 'duration_ms' existe no DataFrame
    if 'duration_ms' in df.columns:
        # 2. Remove valores nulos e calcula a média apenas se houver dados
        duration_data = df['duration_ms'].dropna()
        if not duration_data.empty:
            avg_duration = duration_data.mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Interações", f"{total_reqs}")
    col2.metric("Total de Erros", f"{total_erros}")
    # 3. Exibe o valor calculado de forma segura
    col3.metric("Duração Média (ms)", f"{avg_duration:.2f}")

    st.divider()

    # --- Análise de Drift de Dados ---
    st.subheader("Monitoramento de Drift de Dados")
    
    df_vagas_log = df[df['message'] == 'Vaga Identificada'].copy()

    if not df_vagas_log.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Distribuição de Nível Profissional (Drift)**")
            # Garante que a coluna existe antes de usar
            if 'nivel_profissional' in df_vagas_log.columns:
                drift_chart_data = df_vagas_log['nivel_profissional'].value_counts().reset_index()
                fig = px.bar(drift_chart_data, x='nivel_profissional', y='count', title="Contagem de vagas por nível profissional", text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Acompanhe se a proporção de vagas Jr/Pl/Sr está mudando ao longo do tempo.")
            else:
                st.info("Aguardando logs com 'nivel_profissional' para exibir este gráfico.")

        with col2:
            st.markdown("**Top 5 Clientes com Vagas Buscadas**")
            # Garante que a coluna existe antes de usar
            if 'cliente' in df_vagas_log.columns:
                top_clients_data = df_vagas_log['cliente'].value_counts().nlargest(5).reset_index()
                fig_clients = px.pie(top_clients_data, names='cliente', values='count', title="Distribuição de vagas por cliente (Top 5)")
                st.plotly_chart(fig_clients, use_container_width=True)
            else:
                st.info("Aguardando logs com 'cliente' para exibir este gráfico.")

    else:
        st.info("Ainda não há dados suficientes de vagas para exibir os gráficos de drift.")

    st.divider()
    
    st.subheader("Visualizador de Logs Recentes")
    if st.checkbox("Mostrar logs brutos"):
        st.dataframe(df.tail(100))
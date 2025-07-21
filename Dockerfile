# --- Estágio 1: Base e Instalação de Dependências ---

# 1. Use uma imagem Python oficial e leve como base.
# A tag "slim" é uma versão otimizada e menor.
FROM python:3.12-slim

# 2. Defina o diretório de trabalho dentro do container.
# Todas as operações a seguir acontecerão dentro de /app.
WORKDIR /app

# 3. Copie o arquivo de dependências PRIMEIRO.
# Isso aproveita o cache do Docker. As dependências só serão reinstaladas se o requirements.txt mudar.
COPY requirements.txt .

# 4. Instale as dependências.
# A flag --no-cache-dir mantém a imagem final menor.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copie TODOS os outros arquivos do projeto para o diretório de trabalho (/app).
# Isso inclui main.py, agent.py, logger_config.py e os arquivos .parquet.
COPY . .

# 6. Exponha a porta que a nossa API FastAPI irá usar.
# O Uvicorn, por padrão, roda na porta 8000.
EXPOSE 8000

# 7. O comando para executar a aplicação quando o container iniciar.
# Usamos "--host 0.0.0.0" para tornar a API acessível de fora do container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
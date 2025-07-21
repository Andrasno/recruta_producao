# logger_config.py
import logging
from pythonjsonlogger import jsonlogger
import sys

def setup_logger():
    """Configura um logger para output em formato JSON."""
    logger = logging.getLogger("DecisionAgentLogger")
    logger.setLevel(logging.INFO)
    
    # Evita adicionar handlers duplicados se a função for chamada múltiplas vezes
    if logger.hasHandlers():
        logger.handlers.clear()

    # Log para o console
    logHandler = logging.StreamHandler(sys.stdout)
    
    # Formatter que adiciona campos extras ao log JSON
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s %(process)d %(thread)d'
    )
    
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    
    # Log para um arquivo, para ser lido pelo dashboard
    fileHandler = logging.FileHandler("app_logs.log", mode='a')
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    
    return logger

# Cria uma instância única do logger para ser importada por outros módulos
logger = setup_logger()
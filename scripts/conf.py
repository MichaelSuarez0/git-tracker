import logging
import os

from dotenv import load_dotenv

# Configurar el root logger una vez
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logging.root.setLevel(logging.INFO)

load_dotenv()

TOKEN = os.getenv("GITHUB_API_TOKEN", "")
USERNAME = "MichaelSuarez0"

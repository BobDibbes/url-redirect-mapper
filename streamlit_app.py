import os
import sys
import streamlit

# Voeg het pad van de src directory toe aan de Python pad
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Start de app
os.system(f"{sys.executable} -m streamlit run src/simple_language_redirect_app.py") 
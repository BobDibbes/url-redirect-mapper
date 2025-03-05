import os
import sys

# Voeg de hoofdmap van het project toe aan het Python-pad
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import io
import tempfile
from src.redirect_mapper import RedirectMapper
from src.config import RedirectConfig

# Page config
st.set_page_config(
    page_title="URL Redirect Mapping Tool",
    page_icon="🔄",
    layout="wide"
)

# Initialize session state variables
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'confidence_threshold' not in st.session_state:
    st.session_state.confidence_threshold = 0.5

# Create temporary config directory if needed
temp_config_dir = os.path.join(tempfile.gettempdir(), 'url_redirect_config')
os.makedirs(temp_config_dir, exist_ok=True)

def initialize_config():
    """Initialize default configuration files."""
    config = RedirectConfig(temp_config_dir)
    st.success("Configuratiebestanden zijn geïnitialiseerd!")
    return config

def process_urls(df, source_col, confidence_threshold):
    """Process URLs using the redirect mapper."""
    mapper = RedirectMapper(temp_config_dir)
    result = mapper.process_urls(
        df, 
        source_col=source_col,
        confidence_threshold=confidence_threshold
    )
    return result

# App header
st.title("URL Redirect Mapping Tool")
st.markdown("""
Deze tool helpt bij het maken van URL-redirects voor meertalige websites. 
Upload een CSV-bestand met bron-URLs en genereer doelgerichte redirects.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuratie")
    
    # Initialize config button
    if st.button("Initialiseer standaardconfiguratie"):
        config = initialize_config()
    
    # Confidence threshold slider
    st.session_state.confidence_threshold = st.slider(
        "Betrouwbaarheidsdrempel", 
        min_value=0.0, 
        max_value=1.0, 
        value=st.session_state.confidence_threshold,
        step=0.05,
        help="Minimale betrouwbaarheidsscore voor het opnemen van een redirect"
    )
    
    # Advanced settings expander
    with st.expander("Geavanceerde instellingen"):
        st.write("Configuratiebestanden zijn opgeslagen in:", temp_config_dir)
        
        # Upload domain mapping
        st.subheader("Domein configuratie")
        domain_file = st.file_uploader("Upload domains.json", type=["json"])
        if domain_file:
            with open(os.path.join(temp_config_dir, "domains.json"), "wb") as f:
                f.write(domain_file.getbuffer())
            st.success("Domein configuratie geüpload!")
        
        # Upload language mapping
        st.subheader("Taal configuratie")
        lang_file = st.file_uploader("Upload languages.json", type=["json"])
        if lang_file:
            with open(os.path.join(temp_config_dir, "languages.json"), "wb") as f:
                f.write(lang_file.getbuffer())
            st.success("Taal configuratie geüpload!")
        
        # Upload dictionaries
        st.subheader("Woordenboeken")
        dict_file = st.file_uploader("Upload woordenboek (bijv. fr_en.json)", type=["json"])
        if dict_file:
            dict_name = st.text_input("Bestandsnaam (bijv. fr_en.json)", "fr_en.json")
            dict_dir = os.path.join(temp_config_dir, "dictionaries")
            os.makedirs(dict_dir, exist_ok=True)
            with open(os.path.join(dict_dir, dict_name), "wb") as f:
                f.write(dict_file.getbuffer())
            st.success(f"Woordenboek {dict_name} geüpload!")

# Main content area
st.header("URL Data Verwerking")

# File upload
uploaded_file = st.file_uploader("Upload een CSV-bestand met URLs", type=["csv"])

if uploaded_file is not None:
    # Load data
    try:
        df = pd.read_csv(uploaded_file)
        st.write("Voorbeeld van geüploade data:")
        st.dataframe(df.head())
        
        # Column selection
        columns = list(df.columns)
        source_col = st.selectbox("Selecteer de kolom met bron-URLs", columns, index=0)
        
        # Process button
        if st.button("Verwerk URLs"):
            with st.spinner("URLs verwerken..."):
                # Process the URLs
                st.session_state.processed_data = process_urls(
                    df,
                    source_col,
                    st.session_state.confidence_threshold
                )
                st.success("Verwerking voltooid!")
    
    except Exception as e:
        st.error(f"Fout bij het verwerken van het bestand: {str(e)}")

# Display results
if st.session_state.processed_data is not None:
    st.header("Resultaten")
    
    # Show data statistics
    results_df = st.session_state.processed_data
    total_urls = len(results_df)
    matched_urls = results_df['suggested_target'].notna().sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Totaal aantal URLs", total_urls)
    col2.metric("Gematched URLs", matched_urls)
    col3.metric("Match percentage", f"{(matched_urls/total_urls*100):.1f}%")
    
    # Display results table
    st.subheader("Redirect mappings")
    st.dataframe(results_df)
    
    # Download buttons
    st.subheader("Download resultaten")
    
    csv = results_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download als CSV",
        data=csv,
        file_name='redirect_mappings.csv',
        mime='text/csv',
    )
    
    # Generate .htaccess file
    htaccess_buffer = io.StringIO()
    htaccess_buffer.write("# Redirect mappings generated by URL Redirect Mapper\n")
    htaccess_buffer.write("# Format: RedirectPermanent source_path target_url\n\n")
    htaccess_buffer.write("RewriteEngine On\n\n")
    
    for _, row in results_df.iterrows():
        if pd.notna(row['suggested_target']) and row['confidence_score'] >= st.session_state.confidence_threshold:
            source = row[source_col]
            target = row['suggested_target']
            
            # Extract source path
            if "://" in source:
                source_path = source.split("://", 1)[1]
                if "/" in source_path:
                    source_path = "/" + source_path.split("/", 1)[1]
                else:
                    source_path = "/"
            else:
                source_path = source
            
            htaccess_buffer.write(f"RedirectPermanent {source_path} {target}\n")
    
    st.download_button(
        label="Download als .htaccess",
        data=htaccess_buffer.getvalue(),
        file_name='redirects.htaccess',
        mime='text/plain',
    )
    
    # Display confidence distribution
    st.subheader("Betrouwbaarheidsscore distributie")
    hist_values = results_df['confidence_score'].dropna()
    st.bar_chart(hist_values.value_counts(bins=10, normalize=True).sort_index())

# Footer
st.markdown("---")
st.markdown("URL Redirect Mapping Tool voor meertalige websites © 2023") 
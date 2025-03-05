import streamlit as st
import pandas as pd
import numpy as np
import io
from urllib.parse import urlparse
import string
from difflib import SequenceMatcher
from io import BytesIO
import xlsxwriter
import time
import re
import difflib
import urllib.parse

# Definieer similarity_ratio functie vóór alle andere functies die het gebruiken
def similarity_ratio(s1, s2):
    """Berekent de overeenkomst tussen twee strings (0-1)."""
    return difflib.SequenceMatcher(None, s1, s2).ratio() 

# Voeg deze regel toe aan het begin van je app, net na de imports
help_tooltip = ""  # Lege tooltip als fallback

# Eenvoudige Levenshtein afstandsberekening
def levenshtein_distance(s1, s2):
    """Bereken de Levenshtein afstand tussen twee strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

# Voeg deze functie toe voor bestandsverwerking (ongeveer bovenaan de file, onder de imports)
def process_file(uploaded_file):
    """Verwerkt een geüpload bestand en extraheert URLs."""
    urls = []
    df = None
    
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # CSV bestand verwerken
        if file_extension == 'csv':
            df = pd.read_csv(uploaded_file)
            # Neem de eerste kolom als URL-kolom
            if len(df.columns) > 0:
                urls = df.iloc[:, 0].dropna().tolist()
                
        # Excel bestand verwerken
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file)
            # Neem de eerste kolom als URL-kolom
            if len(df.columns) > 0:
                urls = df.iloc[:, 0].dropna().tolist()
                
        # TXT bestand verwerken (één URL per regel)
        elif file_extension == 'txt':
            content = uploaded_file.getvalue().decode('utf-8')
            urls = [line.strip() for line in content.split('\n') if line.strip()]
            df = pd.DataFrame({"URL": urls})
            
        # Zorg ervoor dat alle URLs strings zijn
        urls = [str(url) for url in urls if url]
        
        # Verwijder eventuele duplicaten
        urls = list(dict.fromkeys(urls))
        
    except Exception as e:
        st.error(f"Fout bij het verwerken van bestand: {str(e)}")
        return [], None
    
    return urls, df

# Voeg deze functies toe of verbeter de bestaande versies
def match_urls(source_urls, target_urls, min_confidence=0.5):
    """Match source URLs met target URLs op basis van verschillende criteria."""
    results = []
    
    for source_url in source_urls:
        best_match = None
        best_confidence = 0
        match_reason = ""
        detailed_reason = ""
        
        # Parse de source URL
        source_parsed = urllib.parse.urlparse(source_url)
        source_path = source_parsed.path.strip('/')
        source_segments = [seg for seg in source_path.split('/') if seg]
        
        for target_url in target_urls:
            # Parse de target URL
            target_parsed = urllib.parse.urlparse(target_url)
            target_path = target_parsed.path.strip('/')
            target_segments = [seg for seg in target_path.split('/') if seg]
            
            confidence = 0
            reason = []
            
            # Controleer op exacte match
            if source_url == target_url:
                confidence = 1.0
                reason = ["Exacte URL match"]
                detailed_reason = "100% exacte match tussen source en target URL"
                best_match = target_url
                best_confidence = confidence
                break
            
            # Controleer op domein match
            if source_parsed.netloc == target_parsed.netloc:
                confidence += 0.3
                reason.append("Identiek domein")
                domain_part = "Identiek domein: " + source_parsed.netloc
            else:
                domain_similarity = similarity_ratio(source_parsed.netloc, target_parsed.netloc)
                if domain_similarity > 0.7:
                    confidence += 0.2 * domain_similarity
                    reason.append(f"Vergelijkbaar domein ({int(domain_similarity*100)}%)")
                    domain_part = f"Vergelijkbaar domein: {source_parsed.netloc} ~ {target_parsed.netloc} ({int(domain_similarity*100)}%)"
                else:
                    domain_part = f"Verschillende domeinen: {source_parsed.netloc} ≠ {target_parsed.netloc}"
            
            # Controleer segmenten
            matching_segments = 0
            segment_details = []
            
            # Als beide URLs segmenten hebben
            if source_segments and target_segments:
                for i, source_seg in enumerate(source_segments):
                    if i < len(target_segments):
                        if source_seg == target_segments[i]:
                            matching_segments += 1
                            segment_details.append(f"Segment {i+1}: Exacte match '{source_seg}'")
                        else:
                            # Controleer op fuzzy match
                            seg_similarity = similarity_ratio(source_seg, target_segments[i])
                            if seg_similarity > 0.7:
                                matching_segments += seg_similarity
                                segment_details.append(f"Segment {i+1}: Fuzzy match '{source_seg}' ~ '{target_segments[i]}' ({int(seg_similarity*100)}%)")
                
                # Bereken segment confidence
                if len(source_segments) > 0:
                    segment_confidence = matching_segments / max(len(source_segments), len(target_segments))
                    confidence += 0.5 * segment_confidence
                    
                    if matching_segments > 0:
                        reason.append(f"{matching_segments} exacte matches, Jaccard similarity: {int(segment_confidence*100)}%")
                
            # Controleer op woordgelijkheid
            source_words = set(re.findall(r'\w+', source_url.lower()))
            target_words = set(re.findall(r'\w+', target_url.lower()))
            
            if source_words and target_words:
                word_similarity = len(source_words.intersection(target_words)) / len(source_words.union(target_words))
                
                if word_similarity > 0.3:
                    confidence += 0.2 * word_similarity
                    reason.append(f"Woordgelijkheid: {int(word_similarity*100)}%")
                    word_part = f"Woordgelijkheid: {int(word_similarity*100)}% ({len(source_words.intersection(target_words))} overeenkomende woorden)"
                else:
                    word_part = "Weinig overeenkomende woorden"
                
            # Update beste match als deze beter is
            if confidence > best_confidence:
                best_match = target_url
                best_confidence = confidence
                match_reason = ", ".join(reason)
                
                # Stel een gedetailleerde reden samen
                if segment_details:
                    segment_part = "\n".join(segment_details)
                else:
                    segment_part = "Geen overeenkomende segmenten"
                
                detailed_reason = f"{domain_part}\n{segment_part}\n{word_part}\nTotale score: {int(confidence*100)}%"
        
        # Bepaal status op basis van confidence
        if best_confidence >= 0.75:
            status = "Betrouwbaar"
        elif best_confidence >= 0.45:
            status = "Controle aanbevolen"
        else:
            status = "Handmatige controle nodig"
            
        # Voeg resultaat toe aan lijst
        results.append({
            'Source URL': source_url,
            'Target URL': best_match if best_match else "",
            'Score': round(best_confidence, 2),
            'Status': status,
            'Reden': match_reason if match_reason else "Geen match gevonden",
            'Match Details': detailed_reason,
            'Match gevonden': best_match is not None
        })
    
    return results

def test_matching_quality(source_urls, target_urls):
    """Test de kwaliteit van het matching algoritme en toon scores."""
    test_sample = min(10, len(source_urls))
    sample_urls = source_urls[:test_sample]
    
    st.subheader("Test van matching algoritme")
    st.write(f"Test van algoritme op {test_sample} URLs om de kwaliteit te beoordelen:")
    
    with st.spinner("Test wordt uitgevoerd..."):
        results = match_urls(sample_urls, target_urls)
        
        for result in results:
            confidence_color = (
                "#28a745" if result['Status'] == "Betrouwbaar"
                else "#ffc107" if result['Status'] == "Controle aanbevolen"
                else "#dc3545"
            )
            
            st.markdown(f"""
            <div style="margin-bottom: 15px; padding: 15px; border-radius: 5px; background-color: rgba(255,255,255,0.05);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-weight: bold;">Match score: <span style="color: {confidence_color};">{result['Score']}</span></span>
                    <span style="color: {confidence_color};">{result['Status']}</span>
                </div>
                <strong>Bron:</strong> <code>{result['Source URL']}</code><br>
                <strong>Doel:</strong> <code>{result['Target URL']}</code><br>
                <strong>Details:</strong> {result.get('Match Details', result['Reden'])}
            </div>
            """, unsafe_allow_html=True)

def generate_export_files(results_df):
    """Genereer export bestanden in verschillende formaten met betere kleuren en sortering."""
    exports = {}
    
    # Maak een kopie en sorteer deze op status (belangrijke eerst)
    sorted_df = results_df.copy()
    status_order = {
        "Handmatige controle nodig": 0, 
        "Controle aanbevolen": 1, 
        "Betrouwbaar": 2
    }
    sorted_df['StatusOrder'] = sorted_df['Status'].map(status_order)
    sorted_df = sorted_df.sort_values(by=['StatusOrder', 'Score'], ascending=[True, False])
    sorted_df = sorted_df.drop(columns=['StatusOrder'])
    
    # Excel export met verbeterde opmaak
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        sorted_df.to_excel(writer, sheet_name='URL Redirects', index=False)
        
        # Haal de workbook en worksheet om opmaak toe te passen
        workbook = writer.book
        worksheet = writer.sheets['URL Redirects']
        
        # Formaat definiëren met zachtere kleuren
        header_format = workbook.add_format({
            'bold': True, 
            'bg_color': '#4A5568', 
            'font_color': 'white',
            'border': 1, 
            'align': 'center'
        })
        
        # Zachtere kleurtinten
        betrouwbaar_format = workbook.add_format({
            'bg_color': '#D1FAE5',  # Zacht groen
            'font_color': '#047857'  # Donkergroen voor tekst
        })
        
        controle_format = workbook.add_format({
            'bg_color': '#FEF3C7',  # Zacht geel
            'font_color': '#92400E'  # Donker amber voor tekst
        })
        
        handmatig_format = workbook.add_format({
            'bg_color': '#FEE2E2',  # Zacht rood
            'font_color': '#B91C1C'  # Donkerrood voor tekst
        })
        
        # Headers opmaken
        for col_num, value in enumerate(sorted_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Rijen opmaken per cel - verbeterde toepassing
        for row_num in range(len(sorted_df)):
            # Haal status uit de dataframe
            status = sorted_df.iloc[row_num]['Status']
            
            # Bepaal format op basis van status
            if status == "Betrouwbaar":
                row_format = betrouwbaar_format
            elif status == "Controle aanbevolen":
                row_format = controle_format
            else:  # Handmatige controle nodig
                row_format = handmatig_format
            
            # Schrijf elke cel met het juiste format
            for col_num in range(len(sorted_df.columns)):
                value = sorted_df.iloc[row_num, col_num]
                worksheet.write(row_num + 1, col_num, value, row_format)
        
        # Kolombreedte aanpassen
        worksheet.set_column(0, 1, 50)  # URL kolommen breder
        worksheet.set_column(2, 2, 10)  # Score kolom
        worksheet.set_column(3, 3, 20)  # Status kolom
        worksheet.set_column(4, 5, 40)  # Reden/Details kolommen
        
        # Auto filter toevoegen
        worksheet.autofilter(0, 0, len(sorted_df), len(sorted_df.columns) - 1)
        
        # Bevries de bovenste rij
        worksheet.freeze_panes(1, 0)
    
    excel_buffer.seek(0)
    exports['excel'] = excel_buffer.getvalue()
    
    # CSV export (gebruik ook gesorteerde DF)
    csv_buffer = BytesIO()
    sorted_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    exports['csv'] = csv_buffer.getvalue()
    
    # JSON export (gebruik ook gesorteerde DF)
    json_buffer = BytesIO()
    json_buffer.write(sorted_df.to_json(orient='records').encode())
    json_buffer.seek(0)
    exports['json'] = json_buffer.getvalue()
    
    return exports

# Page config
st.set_page_config(
    page_title="URL Redirect Mapper",
    page_icon="🔄",
    layout="wide",
)

# Verbeterde CSS met centraal alignement en betere ruimtelijke verdeling
st.markdown("""
<style>
    /* Reset en basis styling */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary: #FF4B4B;
        --primary-light: #ff6b6b;
        --primary-dark: #E03131;
        --bg-dark: #121212;
        --bg-card: #1E1E1E;
        --bg-secondary: #2D2D2D;
        --text-light: #FFFFFF;
        --text-muted: #AAAAAA;
        --success: #28a745;
        --warning: #ffc107;
        --danger: #dc3545;
        --info: #4361ee;
    }
    
    * {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* NIEUWE VERBETERINGEN: Centrale container en betere ruimteverdeling */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px;
    }
    
    /* NIEUWE VERBETERINGEN: Duidelijkere stappen met betere scheiding */
    .step-container {
        background-color: rgba(38, 38, 38, 0.7);
        border-radius: 10px;
        padding: 25px;
        margin-bottom: 35px; /* Meer ruimte tussen stappen */
        border-left: 4px solid var(--primary);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease;
    }
    
    .step-container:hover {
        transform: translateY(-2px);
    }
    
    /* NIEUWE VERBETERINGEN: Verbeterde step indicator */
    .step-indicator {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    
    .step-circle {
        width: 32px; /* Iets groter */
        height: 32px; /* Iets groter */
        border-radius: 50%;
        background-color: var(--primary);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        margin-right: 12px;
        box-shadow: 0 2px 4px rgba(255, 75, 75, 0.3); /* Subtiele schaduw */
    }
    
    .step-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-light);
    }
    
    /* NIEUWE VERBETERINGEN: Betere knop styling */
    button[data-testid="baseButton-primary"] {
        background-color: var(--primary) !important;
        border-radius: 6px !important;
        padding: 4px 10px !important;
        font-weight: 500 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    
    button[data-testid="baseButton-primary"]:hover {
        background-color: var(--primary-light) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* NIEUWE VERBETERINGEN: Verbeterde upload containers */
    .upload-container {
        background-color: rgba(40, 40, 40, 0.5);
        border: 2px dashed rgba(255, 75, 75, 0.3);
        border-radius: 8px;
        padding: 25px;
        text-align: center;
        transition: all 0.3s ease;
        margin-bottom: 15px;
    }
    
    .upload-container:hover {
        border-color: var(--primary);
        background-color: rgba(255, 75, 75, 0.05);
    }
    
    /* NIEUWE VERBETERINGEN: Twee koloms layout verbeteren */
    .columns-container {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
    }
    
    .column {
        flex: 1;
        background-color: rgba(30, 30, 30, 0.7);
        border-radius: 8px;
        padding: 20px;
    }
    
    /* NIEUWE VERBETERINGEN: Verbeterde resultaten sectie */
    .results-container {
        background-color: rgba(38, 38, 38, 0.7);
        border-radius: 10px;
        padding: 25px;
        margin-top: 20px;
    }
    
    .section-divider {
        margin: 30px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* NIEUWE VERBETERINGEN: Verbeterde statuskleuren */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 13px;
        font-weight: 500;
    }
    
    /* NIEUWE VERBETERINGEN: Verbeterde footer */
    .footer {
        text-align: center;
        padding: 25px 0;
        margin-top: 40px;
        color: var(--text-muted);
        font-size: 13px;
        border-top: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Behoud overige bestaande stijlen... */
</style>

<!-- Centrale container toevoegen -->
<div class="main-container">
""", unsafe_allow_html=True)

# Gecentreerde header met logo links, titel in midden en contact rechts
st.markdown("""
<div class="header-container">
    <div class="header-left">
        <div class="logo-container">
            <img src="https://cdn.prod.website-files.com/65f4200d41ce2357f0076987/65f985acc170577cb635c285_dibbes-logo_white.svg" alt="Dibbes Logo">
        </div>
    </div>
    <div class="header-center">
        <h1 class="app-title">URL Redirect Mapper</h1>
    </div>
    <div class="header-right">
        <a href="mailto:hello@dibbes.online" class="contact-button">Contact</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Voeg een duidelijke omschrijving toe
st.markdown("<p style='text-align: center; margin-bottom: 25px; color: #ccc;'>Match source URLs met target URLs en bereken betrouwbaarheidsscores</p>", unsafe_allow_html=True)

# Voeg helper tooltips toe bij de stappen
help_tooltip = """
<div class="tooltip-container">
    <div class="tooltip-icon">?</div>
    <div class="tooltip-content">Hier krijg je extra informatie over deze stap en hoe het werkt.</div>
</div>
"""

# Stap 1: Upload verbeterde layout
st.markdown(f"""
<div class="step-container">
    <div class="step-indicator">
        <div class="step-circle">1</div>
        <div class="step-title">Upload de bronbestanden</div>
    </div>
    <div class="step-content">
""", unsafe_allow_html=True)

# Verbeterde twee kolommen layout voor uploads
st.markdown("""
<div class="columns-container">
    <div class="column">
        <h3 style="font-size: 16px; margin-bottom: 15px;">Bron URLs</h3>
        <div class="upload-container">
            <img src="https://cdn-icons-png.flaticon.com/512/3143/3143464.png" width="40" style="margin-bottom: 10px; opacity: 0.7;">
            <p>Sleep bestand hierheen of klik om te uploaden</p>
            <p style="font-size: 12px; opacity: 0.7;">Limit 200MB • CSV, XLSX, XLS, TXT</p>
        </div>
    </div>
    <div class="column">
        <h3 style="font-size: 16px; margin-bottom: 15px;">Doel URLs</h3>
        <div class="upload-container">
            <img src="https://cdn-icons-png.flaticon.com/512/3143/3143464.png" width="40" style="margin-bottom: 10px; opacity: 0.7;">
            <p>Sleep bestand hierheen of klik om te uploaden</p>
            <p style="font-size: 12px; opacity: 0.7;">Limit 200MB • CSV, XLSX, XLS, TXT</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Verwerk bestanden (bestaande functionaliteit behouden)
if source_file:
    source_urls, source_df = process_file(source_file)
    if source_urls:
        st.success(f"{len(source_urls)} bron URLs geladen")
        
        # Preview van data tonen
        st.markdown("<h4 style='font-size: 16px; margin-top: 15px;'>Voorbeeld van geladen bron URLs:</h4>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Bron URL": source_urls[:5]}), height=150)
        
if target_file:
    target_urls, target_df = process_file(target_file)
    if target_urls:
        st.success(f"{len(target_urls)} doel URLs geladen")
        
        # Preview van data tonen
        st.markdown("<h4 style='font-size: 16px; margin-top: 15px;'>Voorbeeld van geladen doel URLs:</h4>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Doel URL": target_urls[:5]}), height=150)

# Sectiedeler
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# Stap 2: Configureer drempel
st.markdown(f"""
<div class="step-container">
    <div class="step-indicator">
        <div class="step-circle">2</div>
        <div class="step-title">Configureer betrouwbaarheidsdrempel</div>
    </div>
    
    URLs met een score onder deze drempel worden gemarkeerd voor handmatige controle.
""", unsafe_allow_html=True)

# Slider voor betrouwbaarheidsdrempel
min_confidence = st.slider(
    "Minimale betrouwbaarheidsscore (0-1):",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.05,
    label_visibility="collapsed"
)

# Verbeterde statusindicaties met badges
st.markdown("""
<div style="display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap;">
    <div class="status-badge status-reliable">● Betrouwbaar (≥ 0.75)</div>
    <div class="status-badge status-check">● Controle aanbevolen (0.45 - 0.75)</div>
    <div class="status-badge status-manual">● Handmatige controle nodig (< 0.45)</div>
</div>
""", unsafe_allow_html=True)

st.markdown("</div></div>", unsafe_allow_html=True)  # Sluit step-content en step-container

# Compacte instructies
st.markdown("URLs met een score onder deze drempel worden gemarkeerd voor handmatige controle.")

# Sectiedeler
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# Stap 3: Start URL matching
st.markdown(f"""
<div class="step-container">
    <div class="step-indicator">
        <div class="step-circle">3</div>
        <div class="step-title">Start de URL matching</div>
    </div>
""", unsafe_allow_html=True)

# Instructies 
st.markdown("""
<div class="instructions-box">
    <div class="instructions-title">Hoe werkt het matching-proces?</div>
    <div class="instructions-text">
        De tool analyseert URL-structuur, segmenten, domeinen en woordgelijkheid om de beste matches te vinden met een betrouwbaarheidsscore.
    </div>
</div>
""", unsafe_allow_html=True)

# Start de matching als beide bestanden zijn geüpload
can_start = 'source_urls' in locals() and 'target_urls' in locals() and len(source_urls) > 0 and len(target_urls) > 0

if not can_start:
    st.warning("Upload zowel bron als doel URL bestanden om te beginnen")
else:
    col1, col2 = st.columns([3, 1])
    with col1:
        start_mapping = st.button("🔄 Start URL Matching", type="primary", use_container_width=True)
    with col2:
        test_algorithm = st.button("🧪 Test algoritme", use_container_width=True)
    
    if test_algorithm:
        test_matching_quality(source_urls, target_urls)

st.markdown("</div></div>", unsafe_allow_html=True)  # Sluit step-content en step-container

# Resultaten weergeven met verbeterde UI
if 'start_mapping' in locals() and start_mapping:
    with st.spinner("URLs worden gematcht... Dit kan even duren."):
        # Toon progressiebalk (simulatie)
        progress_placeholder = st.empty()
        progress_placeholder.markdown("""
        <div class="progress-container">
            <div class="progress-bar" style="width: 0%"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Simuleer voortgang
        for i in range(1, 101):
            # Voer de matching uit in stappen
            progress_placeholder.markdown(f"""
            <div class="progress-container">
                <div class="progress-bar" style="width: {i}%"></div>
            </div>
            """, unsafe_allow_html=True)
            if i < 90:
                time.sleep(0.01)  # Kleine vertraging voor effect
        
        # Voer de echte mapping uit
        results = match_urls(
            source_urls,
            target_urls,
            min_confidence=min_confidence
        )
        
        # Toon 100% op het eind
        progress_placeholder.markdown("""
        <div class="progress-container">
            <div class="progress-bar" style="width: 100%"></div>
        </div>
        """, unsafe_allow_html=True)
        
        if results:
            # Maak DataFrame van resultaten
            results_df = pd.DataFrame(results)
            
            # Sectiedeler
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            
            # Toon resultaten
            st.markdown("""
            <div class="results-container">
                <div class="step-indicator">
                    <div class="step-circle">4</div>
                    <div class="step-title">Resultaten</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Bereken statistieken
            total_urls = len(results_df)
            matched_urls = len(results_df[results_df['Match gevonden'] == True])
            match_percentage = round((matched_urls / total_urls) * 100, 1) if total_urls > 0 else 0
            
            reliable_matches = len(results_df[results_df['Status'] == "Betrouwbaar"])
            check_recommended = len(results_df[results_df['Status'] == "Controle aanbevolen"])
            manual_check = len(results_df[results_df['Status'] == "Handmatige controle nodig"])
            
            reliable_percentage = round((reliable_matches / total_urls) * 100, 1) if total_urls > 0 else 0
            check_percentage = round((check_recommended / total_urls) * 100, 1) if total_urls > 0 else 0
            manual_percentage = round((manual_check / total_urls) * 100, 1) if total_urls > 0 else 0
            
            # Toon statistieken in moderne kaarten
            st.markdown("<h3 style='font-size: 18px; margin: 15px 0;'>Samenvatting</h3>", unsafe_allow_html=True)
            
            # Gebruik Streamlit kolommen voor de statistiekkaarten
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.markdown(
                    f"""
                    <div style="background-color: #2D2D2D; padding: 15px; border-radius: 8px; border-top: 4px solid #4361ee; text-align: center;">
                        <p style="color: #aaa; font-size: 14px; margin-bottom: 5px;">Totaal URLs</p>
                        <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{total_urls}</p>
                        <p style="color: #00C851; font-size: 14px;">100%</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col2:
                st.markdown(
                    f"""
                    <div style="background-color: #2D2D2D; padding: 15px; border-radius: 8px; border-top: 4px solid #4361ee; text-align: center;">
                        <p style="color: #aaa; font-size: 14px; margin-bottom: 5px;">Gematcht</p>
                        <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{matched_urls}</p>
                        <p style="color: #00C851; font-size: 14px;">{match_percentage}%</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col3:
                st.markdown(
                    f"""
                    <div style="background-color: #2D2D2D; padding: 15px; border-radius: 8px; border-top: 4px solid #28a745; text-align: center;">
                        <p style="color: #aaa; font-size: 14px; margin-bottom: 5px;">Betrouwbaar</p>
                        <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{reliable_matches}</p>
                        <p style="color: #00C851; font-size: 14px;">{reliable_percentage}%</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col4:
                st.markdown(
                    f"""
                    <div style="background-color: #2D2D2D; padding: 15px; border-radius: 8px; border-top: 4px solid #ffc107; text-align: center;">
                        <p style="color: #aaa; font-size: 14px; margin-bottom: 5px;">Controle aanbevolen</p>
                        <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{check_recommended}</p>
                        <p style="color: #ffc107; font-size: 14px;">{check_percentage}%</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col5:
                st.markdown(
                    f"""
                    <div style="background-color: #2D2D2D; padding: 15px; border-radius: 8px; border-top: 4px solid #dc3545; text-align: center;">
                        <p style="color: #aaa; font-size: 14px; margin-bottom: 5px;">Handmatige controle</p>
                        <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{manual_check}</p>
                        <p style="color: #dc3545; font-size: 14px;">{manual_percentage}%</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # URL Mappings
            st.markdown("<h3 style='font-size: 18px; margin: 25px 0 15px 0;'>URL Mappings</h3>", unsafe_allow_html=True)
            
            # Verbeterde zoek- en filterfuncties
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                search_term = st.text_input("Zoek in URLs:", placeholder="Voer zoekterm in...")
            with col2:
                status_filter = st.selectbox(
                    "Filter op status:",
                    options=["Alle", "Betrouwbaar", "Controle aanbevolen", "Handmatige controle nodig"],
                    label_visibility="collapsed"
                )
            with col3:
                sort_by = st.selectbox(
                    "Sorteer op:",
                    options=["Score (hoog-laag)", "Score (laag-hoog)", "Status"],
                    label_visibility="collapsed"
                )
            
            # Pas filters toe (bestaande functionaliteit behouden)
            filtered_df = results_df.copy()
            if search_term:
                mask = (
                    filtered_df['Source URL'].str.contains(search_term, case=False, na=False) | 
                    filtered_df['Target URL'].str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[mask]
            
            if status_filter != "Alle":
                filtered_df = filtered_df[filtered_df['Status'] == status_filter]
            
            # Sorteer resultaten
            if sort_by == "Score (hoog-laag)":
                filtered_df = filtered_df.sort_values(by='Score', ascending=False)
            elif sort_by == "Score (laag-hoog)":
                filtered_df = filtered_df.sort_values(by='Score', ascending=True)
            elif sort_by == "Status":
                # Sorteren op status prioriteit: Handmatige controle eerst, dan Controle aanbevolen, dan Betrouwbaar
                status_order = {
                    "Handmatige controle nodig": 0, 
                    "Controle aanbevolen": 1, 
                    "Betrouwbaar": 2
                }
                filtered_df['StatusOrder'] = filtered_df['Status'].map(status_order)
                filtered_df = filtered_df.sort_values(by='StatusOrder')
                filtered_df = filtered_df.drop(columns=['StatusOrder'])
            
            # Verbeterde weergave met meer details
            st.write("Klik op een rij voor details")
            
            # Interactieve tabel met moderne styling
            selection = st.dataframe(
                filtered_df[['Source URL', 'Target URL', 'Score', 'Status', 'Match Details']].style.apply(
                    lambda x: [
                        'background-color: rgba(40, 167, 69, 0.1); color: #28a745' if x['Status'] == 'Betrouwbaar' 
                        else 'background-color: rgba(255, 193, 7, 0.1); color: #ffc107' if x['Status'] == 'Controle aanbevolen'
                        else 'background-color: rgba(220, 53, 69, 0.1); color: #dc3545'
                        for _ in x
                    ], 
                    axis=1
                ),
                height=400,
                use_container_width=True
            )
            
            # Export opties
            st.markdown("<h3 style='font-size: 18px; margin: 25px 0 15px 0;'>Exporteer resultaten</h3>", unsafe_allow_html=True)
            
            # Genereer exports (bestaande functionaliteit behouden)
            exports = generate_export_files(results_df)
            
            # Toon moderne download knoppen
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    "📊 Excel bestand",
                    data=exports['excel'],
                    file_name="url_redirects.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col2:
                st.download_button(
                    "📄 CSV bestand",
                    data=exports['csv'],
                    file_name="url_redirects.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col3:
                st.download_button(
                    "🔄 JSON bestand",
                    data=exports['json'],
                    file_name="url_redirects.json",
                    mime="application/json",
                    use_container_width=True
                )

            st.markdown("</div></div>", unsafe_allow_html=True)  # Sluit results-container

# Footer Opschoning
st.markdown("""
<div class="footer">
    URL Redirect Mapper<br>
    © 2025 <a href="https://www.dibbes.online/" target="_blank" style="color: #FF4B4B; text-decoration: none;">Dibbes</a>
</div>
""", unsafe_allow_html=True)

# Aan het einde van je app, sluit de main-container
st.markdown("</div>", unsafe_allow_html=True) 
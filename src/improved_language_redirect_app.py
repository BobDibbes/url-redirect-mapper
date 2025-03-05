import streamlit as st
import pandas as pd
import io
import re
from urllib.parse import urlparse
import string
from difflib import SequenceMatcher
from io import BytesIO
import xlsxwriter

# Page config
st.set_page_config(
    page_title="Taalvariant URL Matcher",
    page_icon="🌐",
    layout="wide"
)

# App header
st.title("Taalvariant URL Matcher")
st.markdown("""
### Upload je FR-FR en EN-NL URL bestanden en krijg automatisch redirects
Zo eenvoudig is het! Upload gewoon je CSV-bestanden en wij doen de rest.
""")

# Franse naar Nederlandse woordenlijst voor URL-segmenten
# Dit is een uitgebreide lijst met alle mogelijke vertalingen
FR_NL_SEGMENT_DICTIONARY = {
    # Algemene termen
    "accueil": "home",
    "nouvelles": "nieuws",
    "entreprise": "bedrijf",
    "entreprises": "bedrijven",
    "a-propos": "over-ons",
    "contact": "contact",
    "produits": "producten",
    "services": "diensten",
    
    # Specifieke Temper gerelateerde termen
    "newsroom": "newsroom", 
    "conseils": "advies",
    "profil": "profiel",
    "missions": "opdrachten",
    "fonctionnement": "hoe-het-werkt",
    "pour": "voor",
    "decrocher": "verkrijgen",
    "une": "een",
    "mission": "opdracht",
    "entreprises": "business",
    "decouvrez": "ontdek",
    "pouvoir": "kracht",
    "dune": "van-een",
    "attitude": "houding",
    "positive": "positieve",
    "travail": "werk",
    "acceptes": "geaccepteerd",
    
    # Extra vertalingen
    "notre": "onze",
    "histoire": "geschiedenis",
    "integration": "integratie",
    "download": "download",
    "whitepaper": "whitepaper",
    "zekerheid": "securite",
    "personeelsplanning": "planification-personnel",
    "retail": "detail",
    "thank": "merci",
    "pricing": "tarifs",
    "comparison": "comparaison",
    "how": "comment",
    "works": "fonctionne",
    "discover": "decouvrez",
    "power": "pouvoir",
    "positive": "positive",
    "work": "travail",
    "attitude": "attitude",
    "votre": "your",
    "vous": "you",
    "merci": "thank",
    "fr": "en-nl",
    "api": "api",
    
    # Specifiek voor de URL-paden die we hebben gezien
    "decouvrez-le-pouvoir-dune-attitude-positive-au-travail": "discover-the-power-of-a-positive-work-attitude",
    "conseils-de-profil-missions-acceptes": "profile-advice-accepted-missions",
    "pro-pour-decrocher-une-mission": "pro-tips-to-get-a-job",
    "integration-api": "api-integration"
}

def similarity_ratio(a, b):
    """Bereken hoe vergelijkbaar twee strings zijn."""
    return SequenceMatcher(None, a, b).ratio()

def normalize_segment(segment):
    """Normaliseer een URL-segment door speciale tekens te verwijderen."""
    # Verwijder leestekens en zet om naar kleine letters
    segment = segment.lower()
    segment = segment.translate(str.maketrans('', '', string.punctuation))
    return segment

def translate_segment(segment, dictionary):
    """Vertaal een URL-segment met behulp van het woordenboek."""
    normalized = normalize_segment(segment)
    
    # Directe vertaling
    if normalized in dictionary:
        return dictionary[normalized]
    
    # Probeer fuzzy matching als er geen directe vertaling is
    best_match = None
    best_score = 0.7  # Minimale score om als match te beschouwen
    
    for source, target in dictionary.items():
        score = similarity_ratio(normalized, source)
        if score > best_score:
            best_score = score
            best_match = target
    
    return best_match if best_match else segment

def extract_path_segments(url):
    """Haal padsegementen uit een URL en identificeer de taalcode."""
    if not url or pd.isna(url):
        return [], None
    
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        segments = path.split('/')
        
        # Detecteer taalcode
        lang_code = None
        if segments and (len(segments[0]) == 2 or 
                        (len(segments[0]) == 5 and segments[0][2] == '-')):
            lang_code = segments[0]
            segments = segments[1:]  # Verwijder taalcode uit segmenten
            
        return segments, lang_code
    except:
        return [], None

def extract_domain(url):
    """Haal het domein uit een URL."""
    if not url or pd.isna(url):
        return ""
    
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""

def match_by_segment_translation(source_urls, target_urls, dictionary):
    """Match URLs op basis van segmentvertaling."""
    matches = []
    used_targets = set()  # Bijhouden welke doel-URLs al zijn gebruikt
    
    # Eerste pas: probeer gewone matching met vertaling
    for source_url in source_urls:
        source_segments, source_lang = extract_path_segments(source_url)
        
        best_match = None
        best_score = 0.0
        best_reason = ""
        
        # Als er segmenten zijn, probeer ze te matchen
        if source_segments:
            for target_url in target_urls:
                if target_url in used_targets:
                    continue  # Sla URLs over die al zijn gematcht
                    
                target_segments, target_lang = extract_path_segments(target_url)
                if not target_segments:
                    continue
                    
                # Vertaal elk segment uit de bron-URL
                translated_segments = []
                for segment in source_segments:
                    translated_segments.append(translate_segment(segment, dictionary))
                
                # Bereken hoeveel segmenten overeenkomen
                matching_segments = 0
                total_segments = max(len(translated_segments), len(target_segments))
                
                for i in range(min(len(translated_segments), len(target_segments))):
                    source_translated = translated_segments[i]
                    target = target_segments[i]
                    
                    # Check exacte match of hoge gelijkenis
                    if source_translated == target or similarity_ratio(source_translated, target) > 0.6:
                        matching_segments += 1
                
                # Bereken score
                score = matching_segments / total_segments if total_segments > 0 else 0
                
                # Voeg bonus toe als de basisstructuur overeenkomt
                if matching_segments > 0 and len(translated_segments) == len(target_segments):
                    score += 0.2
                    score = min(score, 1.0)  # Houd score onder 1.0
                
                # Als dit de beste match tot nu toe is, bewaar deze
                if score > best_score:
                    best_score = score
                    best_match = target_url
                    best_reason = f"Segmentvertaling: {matching_segments}/{total_segments} segmenten komen overeen"
        
        # Als we geen segmenten konden vinden of geen goede match
        if not source_segments or best_score < 0.3:
            # Probeer domeinmatching voor hoofddomeinen
            source_domain = extract_domain(source_url)
            if source_domain and source_url.endswith(source_domain) or source_url.endswith(f"{source_domain}/"):
                # Dit is waarschijnlijk een hoofddomein/homepage
                for target_url in target_urls:
                    if target_url in used_targets:
                        continue  # Sla URLs over die al zijn gematcht
                    
                    target_domain = extract_domain(target_url)
                    if target_domain and (target_url.endswith(target_domain) or target_url.endswith(f"{target_domain}/")):
                        best_match = target_url
                        best_score = 0.8  # Hoge score voor hoofddomein match
                        best_reason = "Hoofddomein match"
                        break
        
        # Markeer de gekozen doel-URL als gebruikt
        if best_match:
            used_targets.add(best_match)
        
        # Bewaar de beste match die we hebben gevonden
        matches.append((source_url, best_match, best_reason, best_score))
    
    # Tweede pas: voor URLs zonder match, gebruik positie-matching of best-effort toewijzing
    unmatched_sources = [i for i, (_, match, _, _) in enumerate(matches) if match is None]
    unused_targets = [url for url in target_urls if url not in used_targets]
    
    # Probeer 1-op-1 matching voor overgebleven URLs
    for i, source_index in enumerate(unmatched_sources):
        if i < len(unused_targets):
            target_url = unused_targets[i]
            matches[source_index] = (matches[source_index][0], target_url, "Best-effort toewijzing (handmatige controle vereist)", 0.2)
            used_targets.add(target_url)
    
    # Als er nog steeds ongematchte URLs zijn, gebruik gewoon de eerste beschikbare doel-URL
    for i, (source_url, match, reason, score) in enumerate(matches):
        if match is None:
            for target_url in target_urls:
                if target_url not in used_targets:
                    matches[i] = (source_url, target_urls[0], "Fallback toewijzing (lage betrouwbaarheid)", 0.1)
                    used_targets.add(target_url)
                    break
            
            # Als alle doel-URLs al zijn gebruikt, hergebruik een bestaande
            if matches[i][1] is None:
                matches[i] = (source_url, target_urls[0], "Noodoplossing toewijzing (zeer lage betrouwbaarheid)", 0.05)
    
    return matches

def generate_htaccess(source_urls, target_urls):
    """Genereer .htaccess regels voor de gegeven URLs."""
    htaccess_content = "# Redirect mappings van FR-FR naar EN-NL\n"
    htaccess_content += "# Format: RedirectPermanent source_path target_url\n\n"
    htaccess_content += "RewriteEngine On\n\n"
    
    for source, target in zip(source_urls, target_urls):
        if pd.isna(source) or pd.isna(target):
            continue
            
        # Extract source path
        if "://" in source:
            source_path = source.split("://", 1)[1]
            if "/" in source_path:
                source_path = "/" + source_path.split("/", 1)[1]
            else:
                source_path = "/"
        else:
            source_path = source
        
        htaccess_content += f"RedirectPermanent {source_path} {target}\n"
    
    return htaccess_content

# Sidebar voor instellingen
with st.sidebar:
    st.header("Instellingen")
    
    # Betrouwbaarheidsdrempel voor matches
    matching_threshold = st.slider(
        "Minimale betrouwbaarheidsdrempel",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
        help="URLs met een betrouwbaarheidsscore onder deze drempel worden gemarkeerd voor handmatige controle"
    )
    
    # Optie voor verificatie van matches
    verify_matches = st.checkbox(
        "Markeer onzekere matches voor verificatie",
        value=True,
        help="Markeert matches onder een hogere drempel voor handmatige controle"
    )
    
    # Wanneer verificatie is ingeschakeld, toon de verificatiedrempel
    if verify_matches:
        verification_threshold = st.slider(
            "Verificatiedrempel",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="URLs met een score onder deze drempel maar boven de minimale drempel worden gemarkeerd voor controle"
        )
    else:
        verification_threshold = 1.0  # Standaard geen verificatie nodig
    
    st.markdown("---")
    
    # Geavanceerde instellingen
    with st.expander("Geavanceerde instellingen"):
        st.write("Woordenboek bijwerken:")
        
        new_translations = st.text_area(
            "Voeg nieuwe vertalingen toe (één per regel, formaat: fr_term=nl_term)",
            height=100,
            help="Voeg je eigen vertalingen toe in het formaat: franse_term=nederlandse_term"
        )
        
        if new_translations:
            for line in new_translations.split("\n"):
                if "=" in line:
                    source, target = line.split("=", 1)
                    source = source.strip()
                    target = target.strip()
                    if source and target:
                        FR_NL_SEGMENT_DICTIONARY[source] = target
            
            st.success(f"✅ {len(new_translations.split())} nieuwe vertalingen toegevoegd aan het woordenboek!")

# Hoofdgedeelte voor bestandsuploads
col1, col2 = st.columns(2)

with col1:
    st.info("### 1️⃣ Upload je FR-FR URLs")
    source_file = st.file_uploader("Kies CSV-bestand met Franse URLs", type=["csv"], key="source_file")

with col2:
    st.info("### 2️⃣ Upload je EN-NL URLs")
    target_file = st.file_uploader("Kies CSV-bestand met Nederlandse URLs", type=["csv"], key="target_file")

if source_file is not None and target_file is not None:
    try:
        # Inlezen van CSV-bestanden
        source_df = pd.read_csv(source_file)
        target_df = pd.read_csv(target_file)
        
        # Bepaal automatisch de URL kolommen
        source_col = source_df.columns[0]  # Neem standaard de eerste kolom
        target_col = target_df.columns[0]  # Neem standaard de eerste kolom
        
        # Controleer of er kolommen zijn die 'url' in de naam hebben
        for col in source_df.columns:
            if 'url' in col.lower():
                source_col = col
                break
        
        for col in target_df.columns:
            if 'url' in col.lower():
                target_col = col
                break
        
        # Geef de gebruiker een duidelijke bevestiging
        st.success(f"✅ Bestanden succesvol geladen!")
        
        # Toon een klein voorbeeld van de gegevens
        st.subheader("Voorbeeld van geüploade URLs")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Franse URLs:")
            st.dataframe(source_df[source_col].head(), height=150)
            
        with col2:
            st.write("Nederlandse URLs:")
            st.dataframe(target_df[target_col].head(), height=150)
        
        # Automatische matching starten
        if st.button("▶️ Start URL matching", help="Klik om het matchingproces te starten"):
            with st.spinner('URLs worden gematcht...'):
                # Voer matching uit met verschillende algoritmes
                matches = match_by_segment_translation(
                    source_df[source_col].tolist(),
                    target_df[target_col].tolist(),
                    FR_NL_SEGMENT_DICTIONARY
                )
                
                # Maak resultaten DataFrame
                results = []
                for source_url, target_url, reason, score in matches:
                    # Bepaal de verificatiestatus
                    if score < matching_threshold:
                        verification_status = "Handmatige controle nodig"
                        match_found = False
                    elif score < verification_threshold and verify_matches:
                        verification_status = "Controle aanbevolen"
                        match_found = True
                    else:
                        verification_status = "Betrouwbaar"
                        match_found = True
                    
                    results.append({
                        'FR-FR URL': source_url,
                        'EN-NL URL': target_url,
                        'Reden': reason,
                        'Score': f"{score:.2f}",
                        'Status': verification_status,
                        'Match gevonden': match_found
                    })
                
                results_df = pd.DataFrame(results)
                
                # Toon statistieken
                total_urls = len(results)
                matched_urls = sum(1 for r in results if r['Match gevonden'])
                reliable_matches = sum(1 for r in results if r['Status'] == "Betrouwbaar")
                check_recommended = sum(1 for r in results if r['Status'] == "Controle aanbevolen")
                manual_check = sum(1 for r in results if r['Status'] == "Handmatige controle nodig")
                
                match_percentage = int(matched_urls/total_urls*100) if total_urls > 0 else 0
                
                # Resultaten sectie met verbeterde UX
                st.markdown("""
                <style>
                    .header-container {
                        text-align: center;
                        padding: 1.5rem 0;
                        background-color: #212529;
                        border-radius: 10px;
                        margin-bottom: 2rem;
                    }
                    .header-text {
                        color: white;
                        font-size: 1.8rem;
                        font-weight: bold;
                    }
                    .results-container {
                        background-color: #2e3136;
                        padding: 1.5rem;
                        border-radius: 10px;
                        margin-bottom: 2rem;
                    }
                    .centered-container {
                        display: flex;
                        justify-content: center;
                        margin: 1rem 0;
                    }
                    .download-container {
                        background-color: #2e3136;
                        padding: 2rem;
                        border-radius: 10px;
                        margin-top: 2rem;
                        text-align: center;
                    }
                    .download-header {
                        text-align: center;
                        margin-bottom: 1.5rem;
                        font-size: 1.5rem;
                        font-weight: bold;
                    }
                    .download-buttons {
                        display: flex;
                        justify-content: center;
                        gap: 1rem;
                        flex-wrap: wrap;
                    }
                </style>
                <div class="header-container">
                    <div class="header-text">Resultaten</div>
                </div>
                """, unsafe_allow_html=True)

                # Statistieken in een nettere layout
                with st.container():
                    st.markdown('<div class="results-container">', unsafe_allow_html=True)
                    
                    # Statistieken weergeven
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Totaal aantal URLs", total_urls)
                    col2.metric("Gematcht", matched_urls, f"{match_percentage}%")
                    col3.metric("Betrouwbare matches", reliable_matches, f"{int(reliable_matches/total_urls*100)}%" if total_urls > 0 else "0%")
                    
                    # Extra statistieken voor verificatie
                    if verify_matches:
                        col1, col2 = st.columns(2)
                        col1.metric("Controle aanbevolen", check_recommended, f"{int(check_recommended/total_urls*100)}%" if total_urls > 0 else "0%")
                        col2.metric("Handmatige controle nodig", manual_check, f"{int(manual_check/total_urls*100)}%" if total_urls > 0 else "0%")
                    
                    st.markdown('</div>', unsafe_allow_html=True)

                # Toon gedetailleerde resultaten met kleurcodering
                st.markdown('<div class="centered-container"><h3>Gedetailleerde resultaten</h3></div>', unsafe_allow_html=True)

                # Functie voor kleurcodering op basis van status
                def color_status(val):
                    if val == "Betrouwbaar":
                        return 'background-color: #d4edda; color: #155724'
                    elif val == "Controle aanbevolen":
                        return 'background-color: #fff3cd; color: #856404'
                    else:
                        return 'background-color: #f8d7da; color: #721c24'
                
                # Toon DataFrame met opmaak
                styled_df = results_df.style.applymap(color_status, subset=['Status'])
                st.dataframe(styled_df, use_container_width=True)  # Gebruik volledige breedte

                # Export opties met een mooiere layout
                st.markdown("""
                <div class="download-container">
                    <div class="download-header">📥 Download de resultaten</div>
                </div>
                """, unsafe_allow_html=True)

                # Download sectie - nu centraal geplaatst
                with st.container():
                    # Zorg ervoor dat we de openpyxl import statement toevoegen
                    try:
                        # Excel export met geformatteerde weergave
                        formatted_excel = BytesIO()
                        workbook = xlsxwriter.Workbook(formatted_excel)
                        worksheet = workbook.add_worksheet('URL Redirects')
                        
                        # Definieer opmaakstijlen voor verschillende statussen
                        betrouwbaar_format = workbook.add_format({'bg_color': '#d4edda', 'font_color': '#155724'})
                        controle_format = workbook.add_format({'bg_color': '#fff3cd', 'font_color': '#856404'})
                        handmatig_format = workbook.add_format({'bg_color': '#f8d7da', 'font_color': '#721c24'})
                        header_format = workbook.add_format({'bold': True, 'bg_color': '#343a40', 'font_color': 'white'})
                        
                        # Schrijf headers
                        for col_num, column in enumerate(results_df.columns):
                            worksheet.write(0, col_num, column, header_format)
                            worksheet.set_column(col_num, col_num, 40)  # Stel kolombreedte in
                        
                        # Schrijf data met opmaak
                        for row_num, row in enumerate(results_df.itertuples(index=False)):
                            for col_num, value in enumerate(row):
                                # Kies de juiste opmaak op basis van status
                                if col_num == list(results_df.columns).index('Status'):
                                    if value == "Betrouwbaar":
                                        cell_format = betrouwbaar_format
                                    elif value == "Controle aanbevolen":
                                        cell_format = controle_format
                                    else:
                                        cell_format = handmatig_format
                                else:
                                    if row.Status == "Betrouwbaar":
                                        cell_format = betrouwbaar_format
                                    elif row.Status == "Controle aanbevolen":
                                        cell_format = controle_format
                                    else:
                                        cell_format = handmatig_format
                                    
                                # Schrijf waarde met de juiste opmaak
                                worksheet.write(row_num + 1, col_num, value, cell_format)
                        
                        # Auto-filter toevoegen
                        worksheet.autofilter(0, 0, len(results_df), len(results_df.columns) - 1)
                        
                        # Sla bestand op en sluit
                        workbook.close()
                        formatted_excel.seek(0)
                        
                        # Maak een download knop voor deze geformatteerde Excel
                        st.markdown('<div class="download-buttons">', unsafe_allow_html=True)
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.download_button(
                                label="📊 Excel (met kleuren)",
                                data=formatted_excel.getvalue(),
                                file_name="fr_nl_redirects_formatted.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                help="Download een Excel bestand met dezelfde kleuren en opmaak als in de tabel hierboven"
                            )
                        
                        # CSV export
                        csv = results_df.to_csv(index=False).encode('utf-8')
                        
                        with col2:
                            st.download_button(
                                label="📄 CSV bestand",
                                data=csv,
                                file_name="fr_nl_redirects.csv",
                                mime="text/csv",
                            )
                        
                        # .htaccess export
                        valid_results = results_df[results_df['Match gevonden'] == True]
                        
                        if len(valid_results) > 0:
                            htaccess_content = generate_htaccess(
                                valid_results['FR-FR URL'].tolist(),
                                valid_results['EN-NL URL'].tolist()
                            )
                            
                            with col3:
                                st.download_button(
                                    label="🔄 .htaccess bestand",
                                    data=htaccess_content,
                                    file_name="fr_nl_redirects.htaccess",
                                    mime="text/plain",
                                )
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Fout bij het maken van downloads: {str(e)}")
                        st.info("Installeer de vereiste packages met: pip install openpyxl xlsxwriter")
                
                # Handmatige controle-interface als er matches zijn die gecontroleerd moeten worden
                if check_recommended > 0 or manual_check > 0:
                    st.subheader("Handmatige controle")
                    st.write("De volgende matches moeten mogelijk handmatig gecontroleerd worden:")
                    
                    # Maak een selectbox om door de te controleren matches te bladeren
                    to_check = results_df[(results_df['Status'] == "Controle aanbevolen") | 
                                         (results_df['Status'] == "Handmatige controle nodig")]
                    
                    if len(to_check) > 0:
                        selected_index = st.selectbox(
                            "Selecteer een match om te controleren:",
                            range(len(to_check)),
                            format_func=lambda i: f"{to_check.iloc[i]['FR-FR URL']} → {to_check.iloc[i]['EN-NL URL']} (Score: {to_check.iloc[i]['Score']})"
                        )
                        
                        selected_match = to_check.iloc[selected_index]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Franse URL:**")
                            st.code(selected_match['FR-FR URL'])
                            
                        with col2:
                            st.write("**Voorgestelde Nederlandse URL:**")
                            st.code(selected_match['EN-NL URL'])
                        
                        st.write(f"**Reden:** {selected_match['Reden']}")
                        st.write(f"**Score:** {selected_match['Score']}")
                        
                        st.write("**Alternatieve Nederlandse URLs:**")
                        alternative_targets = target_df[target_col].tolist()
                        selected_alternative = st.selectbox(
                            "Selecteer een alternatieve URL als de voorgestelde match niet correct is:",
                            ["-- Behoud huidige match --"] + alternative_targets
                        )
                        
                        if selected_alternative != "-- Behoud huidige match --":
                            st.success(f"Je hebt de match gewijzigd naar: {selected_alternative}")
                            # Hier zou je de wijziging kunnen opslaan in de resultaten
                
                # Samenvatting en tips
                if match_percentage < 100:
                    st.warning(f"⚠️ Let op: {100 - match_percentage}% van de URLs konden niet betrouwbaar worden gematcht.")
                    
                    st.markdown("""
                    ### Tips voor betere resultaten:
                    
                    1. **Voeg meer vertalingen toe** aan het woordenboek in de geavanceerde instellingen
                    2. **Verlaag de minimale overeenkomstscore** als de URLs soortgelijke structuren hebben
                    3. **Gebruik de handmatige controle-interface** om problematische matches te corrigeren
                    """)
                else:
                    st.success("🎉 Alle URLs zijn gematcht! Controleer de betrouwbaarheidsscores voor eventuele handmatige verificatie.")
                
    except Exception as e:
        st.error(f"Er is een fout opgetreden: {str(e)}")
        st.info("Tip: Zorg ervoor dat je CSV-bestanden geldig zijn en tenminste één kolom met URLs bevatten.")

# Informatieve footer
st.markdown("---")
st.markdown("""
### 🌐 Hoe deze tool werkt:

1. **Segment-gebaseerde matching**: De tool breekt URLs op in segmenten en probeert deze te vertalen
2. **Woordenboekvertaling**: Franstalige URL-segmenten worden vertaald naar hun Nederlandse equivalenten
3. **Fallback-strategieën**: Als segmentmatching niet lukt, worden andere methodes geprobeerd
4. **Betrouwbaarheidsindicatie**: Elke match krijgt een score en verificatiestatus

**Betrouwbaarheidsniveaus:**
- **Betrouwbaar** (groen): Hoge score, waarschijnlijk correcte match
- **Controle aanbevolen** (geel): Redelijke score, maar verificatie aanbevolen
- **Handmatige controle nodig** (rood): Lage score, waarschijnlijk onjuiste match
""")

st.markdown("---")
st.markdown("Taalvariant URL Matcher © 2023") 
import streamlit as st
import pandas as pd
import io
import re
from urllib.parse import urlparse

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

def extract_path_from_url(url):
    """Haal het pad uit een URL, zonder domein of taalcodes."""
    if not url or pd.isna(url):
        return ""
        
    # Parse de URL
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # Verwijder taalcode-segmenten als die bestaan
        if path.startswith('/'):
            parts = path.split('/')
            if len(parts) > 1:
                # Als het eerste segment een mogelijke taalcode is (zoals 'fr', 'en-nl')
                first_segment = parts[1]
                if (len(first_segment) == 2 or 
                    (len(first_segment) == 5 and first_segment[2] == '-')):
                    # Verwijder het taalsegment
                    return '/' + '/'.join(parts[2:])
        
        return path
    except:
        return ""

def detect_language(url):
    """Detecteer de taalcode in een URL."""
    if not url or pd.isna(url):
        return ""
    
    # Zoek naar taalcode in het subdomein (bijv. fr.example.com)
    domain = urlparse(url).netloc
    if domain.count('.') > 1:
        subdomain = domain.split('.')[0]
        if len(subdomain) == 2 or (len(subdomain) == 5 and subdomain[2] == '-'):
            return subdomain
    
    # Zoek naar taalcode in het pad (bijv. example.com/fr/ of example.com/fr-fr/)
    path = urlparse(url).path
    if path.startswith('/'):
        parts = path.split('/')
        if len(parts) > 1 and parts[1]:
            possible_lang = parts[1]
            if len(possible_lang) == 2 or (len(possible_lang) == 5 and possible_lang[2] == '-'):
                return possible_lang
    
    # Zoek naar taalcode in het domein zelf (bijv. fr-fr.example.com)
    if domain.count('.') > 1:
        prefix = domain.split('.')[0]
        if len(prefix) == 5 and prefix[2] == '-':
            return prefix
    
    return ""

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
                # Extract paths and languages
                source_df['path'] = source_df[source_col].apply(extract_path_from_url)
                target_df['path'] = target_df[target_col].apply(extract_path_from_url)
                
                source_df['lang'] = source_df[source_col].apply(detect_language)
                target_df['lang'] = target_df[target_col].apply(detect_language)
                
                # Display detected languages
                fr_langs = source_df['lang'].value_counts().to_dict()
                nl_langs = target_df['lang'].value_counts().to_dict()
                
                if fr_langs and nl_langs:
                    st.info(f"📊 Gedetecteerde taalcodes in Franse URLs: {', '.join(fr_langs.keys())}")
                    st.info(f"📊 Gedetecteerde taalcodes in Nederlandse URLs: {', '.join(nl_langs.keys())}")
                
                # Match based on paths
                matches = []
                for _, source_row in source_df.iterrows():
                    source_url = source_row[source_col]
                    source_path = source_row['path']
                    
                    match_found = False
                    for _, target_row in target_df.iterrows():
                        target_url = target_row[target_col]
                        target_path = target_row['path']
                        
                        # If paths match (ignoring language segment)
                        if source_path == target_path and source_path:
                            matches.append({
                                'FR-FR URL': source_url,
                                'EN-NL URL': target_url,
                                'Pad': source_path,
                                'Match gevonden': True
                            })
                            match_found = True
                            break
                    
                    if not match_found:
                        matches.append({
                            'FR-FR URL': source_url,
                            'EN-NL URL': None,
                            'Pad': source_path,
                            'Match gevonden': False
                        })
                
                # Create results dataframe
                results_df = pd.DataFrame(matches)
                
                # Count successful matches
                successful_matches = results_df['Match gevonden'].sum()
                total_urls = len(results_df)
                
                # Display results summary with eye-catching metrics
                st.subheader("Resultaten")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Totaal aantal URLs", total_urls)
                col2.metric("Succesvolle matches", successful_matches)
                col3.metric("Matchingspercentage", f"{int(successful_matches/total_urls*100)}%")
                
                # Show detailed results
                st.write("### Gedetailleerde resultaten")
                st.dataframe(results_df.drop('Pad', axis=1))
                
                # Export options
                st.subheader("3️⃣ Download de resultaten")
                
                col1, col2, col3 = st.columns(3)
                
                # Filter for successful matches
                valid_results = results_df[results_df['Match gevonden'] == True]
                
                # Excel export
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    results_df.to_excel(writer, index=False, sheet_name='Alle redirects')
                    valid_results.to_excel(writer, index=False, sheet_name='Geldige redirects')
                
                with col1:
                    st.download_button(
                        label="📊 Download Excel bestand",
                        data=excel_buffer.getvalue(),
                        file_name="fr_nl_redirects.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # CSV export
                csv = valid_results.to_csv(index=False).encode('utf-8')
                
                with col2:
                    st.download_button(
                        label="📄 Download CSV bestand",
                        data=csv,
                        file_name="fr_nl_redirects.csv",
                        mime="text/csv",
                    )
                
                # .htaccess export
                if len(valid_results) > 0:
                    htaccess_content = generate_htaccess(
                        valid_results['FR-FR URL'].tolist(),
                        valid_results['EN-NL URL'].tolist()
                    )
                    
                    with col3:
                        st.download_button(
                            label="🔄 Download .htaccess bestand",
                            data=htaccess_content,
                            file_name="fr_nl_redirects.htaccess",
                            mime="text/plain",
                        )
                
                # Tips for better results if not all URLs matched
                if successful_matches < total_urls:
                    st.warning(f"⚠️ Let op: {total_urls - successful_matches} URLs konden niet worden gematcht.")
                    st.markdown("""
                    ### Tips voor betere resultaten:
                    
                    1. **Zorg dat de URL-structuur overeenkomt** tussen de taalvarianten
                    2. **Controleer handmatig** de URLs die niet zijn gematcht 
                    3. **Probeer het CSV formaat** aan te passen zodat elke URL op een eigen regel staat
                    """)
                else:
                    st.success("🎉 Alle URLs zijn succesvol gematcht!")
                
    except Exception as e:
        st.error(f"Er is een fout opgetreden: {str(e)}")
        st.info("Tip: Zorg ervoor dat je CSV-bestanden geldig zijn en tenminste één kolom met URLs bevatten.")

# Informatieve footer
st.markdown("---")
st.markdown("""
### 🌐 Hoe deze tool werkt:

1. De tool zoekt automatisch FR-FR en EN-NL taalvarianten in de URL structuur
2. URLs worden gematcht op basis van hun padstructuur (zonder taalcodes)
3. Als URLs dezelfde padstructuur hebben maar verschillende taalvarianten, worden ze als een match beschouwd

**Ondersteunde taalcodes:** URLs kunnen taalcodes bevatten in verschillende formaten:
- Subdomeinen: `fr.example.com` of `en-nl.example.com`
- Padsegmenten: `example.com/fr/` of `example.com/en-nl/`
- Domeinprefixen: `fr-fr.example.com` of `en-nl.example.com`
""")

st.markdown("---")
st.markdown("Taalvariant URL Matcher © 2023") 
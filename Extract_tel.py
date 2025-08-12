import streamlit as st

# Mot de passe
PASSWORD = "AEDbadr2025@"

# Initialisation de l'état
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

# Affichage du champ de mot de passe uniquement si non validé
if not st.session_state.auth_ok:
    with st.sidebar:
        st.header("🔒 Accès sécurisé")
        password_input = st.text_input("Entrez le mot de passe :", type="password")
        if password_input == PASSWORD:
            st.session_state.auth_ok = True
            st.rerun()  # 🔁 Recharge l'app pour masquer le champ
        elif password_input != "":
            st.warning("Mot de passe incorrect. Veuillez réessayer.")
    st.stop()

# Le reste de ton app ici (sera affiché uniquement après validation)
st.write("✅ Accès autorisé. Bienvenue !")

import pandas as pd
import phonenumbers
import re
import pycountry
from PIL import Image
from collections import Counter

# Configuration de la page
st.set_page_config(page_title="📞 Analyse Téléphonique", layout="wide")

# Chargement du logo personnalisé
logo = Image.open("UploadedImage1.jpg")  # Assure-toi que ce fichier est dans le même dossier que app.py

# Barre latérale avec logo et titre
with st.sidebar:
    st.image(logo, width=120)
    st.title("📞 Analyse Téléphonique")
    st.markdown("Chargez un fichier CSV contenant une colonne **Erreur** avec des numéros à analyser.")
    uploaded_file = st.file_uploader("📂 Charger un fichier CSV", type=["csv"])

# --- Fonctions utilitaires ---
def trop_de_lettres(text):
    if pd.isna(text):
        return False
    text = str(text)
    blocks = re.findall(r'\d{1,}', text)
    blocs_2_chiffres = [b for b in blocks if len(b) == 2]
    blocs_10_chiffres = [b for b in blocks if len(b) == 10]
    for i in range(len(blocs_2_chiffres) - 4):
        if all(len(b) == 2 for b in blocs_2_chiffres[i:i+5]):
            return False
    if blocs_10_chiffres:
        return False
    lettres = sum(c.isalpha() for c in text)
    total = len(text)
    return total > 0 and (lettres / total) >= 0.5

def extract_french_like_numbers(text):
    if pd.isna(text) or text == "Incorrect":
        return []
    cleaned = re.sub(r'[^\d\+]', ' ', str(text))
    blocks = re.findall(r'\d{1,}', cleaned)
    candidates = []
    for i in range(len(blocks) - 4):
        sequence = blocks[i:i+5]
        if all(len(b) == 2 for b in sequence):
            merged = ''.join(sequence)
            candidates.append(merged)
            break
    if len(blocks) == 6:
        mid_blocks = [b for b in blocks if 5 <= len(b) <= 8]
        short_blocks = [b for b in blocks if len(b) == 2]
        if len(mid_blocks) == 1 and len(short_blocks) == 5:
            merged = ''.join(short_blocks)
            candidates.append(merged)
            candidates.append(mid_blocks[0])
            return candidates
    has_mid_sized_block = any(5 <= len(b) <= 8 for b in blocks)
    if len(blocks) >= 2 and has_mid_sized_block:
        for block in blocks:
            phone = re.sub(r'^(\+33|0033)', '0', block.strip())
            if len(phone) == 9:
                phone = '0' + phone
            if re.fullmatch(r'0[1-9]\d{8}', phone):
                candidates.append(phone)
            elif block.startswith('+') or block.startswith('00'):
                candidates.append(block)
            elif re.fullmatch(r'\d{10,15}', block):
                candidates.append(block)
    elif len(blocks) == 5 and all(len(b) == 2 for b in blocks):
        merged = ''.join(blocks)
        candidates.append(merged)
    else:
        i = 0
        while i < len(blocks):
            group = blocks[i]
            j = i + 1
            while len(re.sub(r'\D', '', group)) < 9 and j < len(blocks):
                group += blocks[j]
                j += 1
            digits = re.sub(r'\D', '', group)
            if 9 <= len(digits) <= 15:
                candidates.append(group.strip())
                i = j
            else:
                i += 1
    return candidates

def get_country_name(region_code):
    if region_code == "FR":
        return "France"
    try:
        country = pycountry.countries.get(alpha_2=region_code)
        return country.name if country else region_code
    except:
        return region_code

def analyze_numbers(text, default_region="FR"):
    raw_numbers = extract_french_like_numbers(text)
    valid_numbers = []
    countries = []
    for raw in raw_numbers:
        try:
            parsed = phonenumbers.parse(raw, default_region)
            if phonenumbers.is_valid_number(parsed):
                e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                region_code = phonenumbers.region_code_for_number(parsed)
                country = get_country_name(region_code)
                valid_numbers.append(e164)
                countries.append(country)
        except:
            continue
    if not valid_numbers:
        for raw in raw_numbers:
            raw = raw.strip()
            if raw.startswith("00"):
                raw = "+" + raw[2:]
            elif re.fullmatch(r"\d{10,15}", raw):
                if raw.startswith(("34", "351", "41", "44", "49", "39", "32", "1", "7")):
                    raw = "+" + raw
            try:
                parsed = phonenumbers.parse(raw, None)
                if phonenumbers.is_valid_number(parsed):
                    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                    region_code = phonenumbers.region_code_for_number(parsed)
                    country = get_country_name(region_code)
                    valid_numbers.append(e164)
                    countries.append(country)
            except:
                continue
    if not valid_numbers:
        return [], "Incorrect", ["Incorrect"]
    elif all(c == "France" for c in countries):
        return valid_numbers, "France", countries
    else:
        return valid_numbers, "International", countries

# Traitement du fichier
if uploaded_file:
    df = pd.read_csv(uploaded_file, encoding="utf-8", sep=None, engine="python")
    if "Erreur" not in df.columns:
        st.error("❌ Le fichier doit contenir une colonne nommée 'Erreur'.")
    else:
        with st.spinner("🔍 Analyse en cours..."):
            numeros_extraits, origine, pays = [], [], []
            for text in df['Erreur']:
                if trop_de_lettres(text):
                    numeros_extraits.append([])
                    origine.append("Incorrect")
                    pays.append(["Incorrect"])
                    continue
                nums, origine_label, country_list = analyze_numbers(text)
                seen = set()
                unique_nums = [x for x in nums if not (x in seen or seen.add(x))]
                numeros_extraits.append(unique_nums)
                origine.append(origine_label)
                pays.append(list(dict.fromkeys(country_list)))
            df["numeros_extraits"] = numeros_extraits
            df["origine"] = origine
            df["pays"] = pays

        st.success("✅ Analyse terminée !")

        # Filtrage par pays
        all_countries = sorted(set(c for sublist in df["pays"] for c in sublist))
        selected_country = st.selectbox("🌍 Filtrer par pays", options=["Tous"] + all_countries)
        if selected_country != "Tous":
            df = df[df["pays"].apply(lambda x: selected_country in x)]

        # Affichage en colonnes
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df)
        with col2:
            st.markdown("### 📋 Résumé des pays détectés")
            country_counts = Counter(c for sublist in df["pays"] for c in sublist if c != "Incorrect")
            for country, count in country_counts.items():
                st.markdown(f"- {country}: **{count}**")

        # Téléchargement
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger le fichier analysé",
            data=csv,
            file_name="numeros_telephones_analyses.csv",
            mime="text/csv"
        )
else:
    st.info("📂 Veuillez charger un fichier CSV dans la barre latérale pour commencer l'analyse.")

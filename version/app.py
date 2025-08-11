import pandas as pd
import phonenumbers
import re
import pycountry

# ✅ Règle 70% de lettres sauf si 5 blocs de 2 chiffres ou 1 bloc de 10 chiffres
def trop_de_lettres(text):
    if pd.isna(text):
        return False
    text = str(text)

    blocks = re.findall(r'\d{1,}', text)
    blocs_2_chiffres = [b for b in blocks if len(b) == 2]
    blocs_10_chiffres = [b for b in blocks if len(b) == 10]

    # Si au moins 5 blocs de 2 chiffres consécutifs
    for i in range(len(blocs_2_chiffres) - 4):
        if all(len(b) == 2 for b in blocs_2_chiffres[i:i+5]):
            return False
    # Si au moins un bloc de 10 chiffres
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

    # Cas particulier : au moins 5 blocs de 2 chiffres consécutifs
    for i in range(len(blocks) - 4):
        sequence = blocks[i:i+5]
        if all(len(b) == 2 for b in sequence):
            merged = ''.join(sequence)
            candidates.append(merged)
            break

    # Cas particulier : 6 blocs dont 1 de 5 à 8 chiffres et 5 de 2 chiffres
    if len(blocks) == 6:
        mid_blocks = [b for b in blocks if 5 <= len(b) <= 8]
        short_blocks = [b for b in blocks if len(b) == 2]
        if len(mid_blocks) == 1 and len(short_blocks) == 5:
            merged = ''.join(short_blocks)
            candidates.append(merged)
            candidates.append(mid_blocks[0])
            return candidates

    # Cas général : au moins deux blocs et un bloc de 5 à 8 chiffres → ne pas fusionner
    has_mid_sized_block = any(5 <= len(b) <= 8 for b in blocks)
    if len(blocks) >= 2 and has_mid_sized_block:
        for block in blocks:
            block = block.strip()
            phone = re.sub(r'^(\+33|0033)', '0', block)
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
        # Fusion progressive
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
# Charger le fichier CSV
fichier = r"C:/Users/AED-BBR/AED EXPERTISES/CLOUD - GENERAL/BASE DIGITALE/INFORMATIQUE/00 - ELH-BBR/Extraction_Sofia_numéro_tel/SOFIA - Locataires - Téls non interprétables.csv"
df = pd.read_csv(fichier, encoding="utf-8", sep=None, engine="python")

# Application sur la colonne 'Erreur'
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

# Ajout des colonnes
df["numeros_extraits"] = numeros_extraits
df["origine"] = origine
df["pays"] = pays

# Sauvegarde
df.to_csv("numeros_telephones_analyses.csv", index=False)
print("✅ Résultat enregistré dans 'numeros_telephones_analyses.csv'")

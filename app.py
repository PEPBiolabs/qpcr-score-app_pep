# Este script foi projetado para ser executado localmente com Streamlit
# Ele tentará instalar o pacote 'streamlit' automaticamente se não estiver presente

import subprocess
import sys

try:
    import streamlit as st
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="qPCR Score App", layout="wide")
st.title("qPCR Score App")
st.markdown("Upload seu arquivo .xlsx com dados da aba 'Amplification Data' exportado do QuantStudio")

with st.expander("📋 Ver critérios de avaliação das curvas"):
    st.markdown("""
    **Cada reação agora recebe uma nota contínua de 0 a 10 com base nos seguintes critérios ponderados:**

    - ✅ **ΔRn final** (peso 3): 0 (fraco) → 20000+ (ótimo)
    - ✅ **Ruído na baseline** (peso 3): 1000 (ruim) → 0 (ideal)
    - ✅ **Inclinação máxima da curva** (peso 4): 0 → 4000+ (ótimo)

    A pontuação final é arredondada para 1 casa decimal, e a classificação qualitativa segue a faixa da nota:

    - `10`: excelente
    - `9`: muito boa
    - `8`: boa
    - `7`: aceitável
    - `6`: limítrofe
    - `5`: fraca
    - `4`: muito fraca
    - `3`: falha
    - `2`: ruído
    - `1`: indetectável
    """)

uploaded_file = st.file_uploader("Escolha o arquivo .xlsx", type="xlsx")

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file, sheet_name="Amplification Data", skiprows=40)
        df_raw.columns = ["Run", "Well", "Cycle", "Sample", "Fluorescencia", "DeltaRn"]

        # Filtrar linhas com DeltaRn nulo ou amostras vazias
        df_raw = df_raw[df_raw["DeltaRn"].notna() & df_raw["Sample"].notna() & (df_raw["Sample"].astype(str).str.strip() != "")]

        avaliacoes = []

        for well, grupo in df_raw.groupby("Well"):
            grupo_ordenado = grupo.sort_values("Cycle")
            delta_rn = grupo_ordenado["DeltaRn"].values

            baseline = delta_rn[:10]
            max_delta_rn = np.nanmax(delta_rn)
            std_baseline = np.nanstd(baseline)
            slope_log = np.nanmax(np.gradient(delta_rn))

            # Normalização dos escores (valores típicos baseados em dados empíricos)
            score_rn = min(max((max_delta_rn / 20000), 0), 1)
            score_noise = min(max((1 - std_baseline / 1000), 0), 1)
            score_slope = min(max((slope_log / 4000), 0), 1)

            nota_continua = round((score_rn * 3 + score_noise * 3 + score_slope * 4), 1)  # Total 10 pontos

            if nota_continua >= 9:
                classif = "10 - excelente"
            elif nota_continua >= 8:
                classif = "9 - muito boa"
            elif nota_continua >= 7:
                classif = "8 - boa"
            elif nota_continua >= 6:
                classif = "7 - aceitável"
            elif nota_continua >= 5:
                classif = "6 - limítrofe"
            elif nota_continua >= 4:
                classif = "5 - fraca"
            elif nota_continua >= 3:
                classif = "4 - muito fraca"
            elif nota_continua >= 2:
                classif = "3 - falha"
            elif nota_continua >= 1:
                classif = "2 - ruído"
            else:
                classif = "1 - indetectável"

            avaliacoes.append({
                "Arquivo": uploaded_file.name,
                "Well": well,
                "Sample": grupo_ordenado["Sample"].iloc[0],
                "DeltaRn_final": max_delta_rn,
                "Ruido_baseline": std_baseline,
                "Derivada_max": slope_log,
                "Nota": score,
                "Classificacao": classif
            })

        df_resultado = pd.DataFrame(avaliacoes)

        st.success("Análise concluída! Veja os resultados abaixo:")
        st.dataframe(df_resultado)

        csv = df_resultado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Baixar resultados como CSV",
            data=csv,
            file_name="avaliacao_qpcr.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

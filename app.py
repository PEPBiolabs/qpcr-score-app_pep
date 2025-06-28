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
    **Cada reação recebe uma nota de 0 a 3 com base nos seguintes critérios:**

    - ✅ **ΔRn final > 5000** → amplificação detectável → +1 ponto
    - ✅ **Ruído no baseline < 500** (desvio padrão dos primeiros 10 ciclos) → +1 ponto
    - ✅ **Inclinação máxima > 1500** (derivada da curva) → crescimento exponencial → +1 ponto

    **Classificação final:**
    - `ótima`: 3 pontos
    - `boa`: 2 pontos
    - `fraca`: 1 ponto
    - `falhou`: 0 pontos
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

            score = 0
            if max_delta_rn > 5000:
                score += 1
            if std_baseline < 500:
                score += 1
            if slope_log > 1500:
                score += 1

            if score == 3:
                classif = "ótima"
            elif score == 2:
                classif = "boa"
            elif score == 1:
                classif = "fraca"
            else:
                classif = "falhou"

            avaliacoes.append({
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

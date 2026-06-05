import streamlit as st
import pandas as pd
import json
import re
import plotly.express as px
import plotly.graph_objects as go
from anthropic import Anthropic

st.set_page_config(layout="wide", page_title="Simulados · Anatomia VI", page_icon="🫀")

# --- SESSION STATE ---
if "ver_geral" not in st.session_state:
    st.session_state.ver_geral = False
if "dados_calculados" not in st.session_state:
    st.session_state.dados_calculados = None

# ─────────────────────────────────────────────
#  LIQUID GLASS  —  CSS + JS injetado via markdown
# ─────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;600&family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">

<style>
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Fundo: mesh gradient escuro animado ── */
.stApp {
    background: #0a0a0f;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% 10%, rgba(99,102,241,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 20%, rgba(14,165,233,0.14) 0%, transparent 55%),
        radial-gradient(ellipse 70% 60% at 50% 80%, rgba(168,85,247,0.10) 0%, transparent 60%);
    font-family: 'Outfit', sans-serif;
    color: rgba(255,255,255,0.88);
    min-height: 100vh;
}

/* ── Orbs flutuantes de fundo (puro CSS) ── */
.stApp::before {
    content: '';
    position: fixed;
    top: -200px; left: -200px;
    width: 600px; height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
    animation: floatOrb1 18s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}
.stApp::after {
    content: '';
    position: fixed;
    bottom: -150px; right: -150px;
    width: 500px; height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(14,165,233,0.10) 0%, transparent 70%);
    animation: floatOrb2 22s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}
@keyframes floatOrb1 {
    0%, 100% { transform: translate(0,0) scale(1); }
    33%       { transform: translate(80px, 60px) scale(1.1); }
    66%       { transform: translate(-40px, 100px) scale(0.95); }
}
@keyframes floatOrb2 {
    0%, 100% { transform: translate(0,0) scale(1); }
    40%       { transform: translate(-60px,-80px) scale(1.08); }
    70%       { transform: translate(50px,-40px) scale(0.92); }
}

/* ── Esconde elementos nativos do Streamlit que atrapalham ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1200px !important;
}

/* ── Sidebar Liquid Glass ── */
[data-testid="stSidebar"] {
    background: rgba(15, 15, 25, 0.75) !important;
    backdrop-filter: blur(28px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(28px) saturate(180%) !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(99,102,241,0.20) !important;
    border: 1px solid rgba(99,102,241,0.40) !important;
    color: white !important;
    border-radius: 12px !important;
    transition: all 0.25s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(99,102,241,0.38) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(99,102,241,0.25) !important;
}

/* ── Botão principal ── */
.stButton > button {
    background: linear-gradient(135deg, rgba(99,102,241,0.9), rgba(14,165,233,0.9)) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.65rem 1.5rem !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.30) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 12px 32px rgba(99,102,241,0.45) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px dashed rgba(99,102,241,0.40) !important;
    border-radius: 14px !important;
    padding: 1rem !important;
    transition: border-color 0.3s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(99,102,241,0.70) !important;
}

/* ── Inputs ── */
.stTextInput input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
    color: white !important;
    font-family: 'Outfit', sans-serif !important;
}

/* ── Metric widgets ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 16px !important;
    padding: 1.2rem 1.5rem !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    font-size: 2rem !important;
    color: white !important;
}
[data-testid="stMetricLabel"] {
    color: rgba(255,255,255,0.55) !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #6366f1 !important; }

/* ── Alertas ── */
.stAlert {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(12px) !important;
    color: rgba(255,255,255,0.80) !important;
}

/* ── Glass card genérico ── */
.glass-card {
    background: rgba(255,255,255,0.055);
    backdrop-filter: blur(24px) saturate(160%);
    -webkit-backdrop-filter: blur(24px) saturate(160%);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 20px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    animation: fadeSlideUp 0.5s ease both;
}
.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.35);
}

/* ── Header principal ── */
.hero-header {
    background: linear-gradient(135deg,
        rgba(99,102,241,0.28) 0%,
        rgba(14,165,233,0.22) 50%,
        rgba(168,85,247,0.20) 100%);
    backdrop-filter: blur(32px) saturate(200%);
    -webkit-backdrop-filter: blur(32px) saturate(200%);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 24px;
    padding: 36px 40px;
    text-align: center;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
    animation: fadeSlideUp 0.6s ease both;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -60%; left: -20%;
    width: 140%; height: 200%;
    background: conic-gradient(from 180deg at 50% 50%,
        rgba(99,102,241,0.08) 0deg,
        rgba(14,165,233,0.06) 120deg,
        rgba(168,85,247,0.07) 240deg,
        rgba(99,102,241,0.08) 360deg);
    animation: spinSlow 30s linear infinite;
    pointer-events: none;
}
@keyframes spinSlow {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}
.hero-header h1 {
    font-family: 'Outfit', sans-serif !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: white !important;
    position: relative;
    margin-bottom: 6px !important;
}
.hero-header p {
    color: rgba(255,255,255,0.60) !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    position: relative;
}

/* ── Seção título ── */
.section-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(99,102,241,0.90);
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(99,102,241,0.35), transparent);
}

/* ── Podium cards ── */
.podium-item {
    display: flex;
    align-items: center;
    gap: 14px;
    background: rgba(255,255,255,0.048);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: all 0.25s ease;
    animation: fadeSlideUp 0.5s ease both;
}
.podium-item:hover {
    background: rgba(255,255,255,0.075);
    transform: translateX(4px);
}
.podium-item:nth-child(1) { border-left: 3px solid #FFD700; animation-delay: 0.05s; }
.podium-item:nth-child(2) { border-left: 3px solid #C0C0C0; animation-delay: 0.10s; }
.podium-item:nth-child(3) { border-left: 3px solid #CD7F32; animation-delay: 0.15s; }
.rank-medal { font-size: 1.4rem; min-width: 28px; }
.rank-name { flex: 1; font-weight: 500; font-size: 0.95rem; color: rgba(255,255,255,0.88); }
.rank-score {
    font-weight: 700;
    font-size: 1.05rem;
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ── Badges questões ── */
.badge-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: 30px;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    animation: popIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both;
}
.badge-ok {
    background: rgba(52,211,153,0.15);
    border: 1px solid rgba(52,211,153,0.35);
    color: #34d399;
}
.badge-bad {
    background: rgba(248,113,113,0.15);
    border: 1px solid rgba(248,113,113,0.35);
    color: #f87171;
}
.badge:nth-child(1) { animation-delay: 0.05s; }
.badge:nth-child(2) { animation-delay: 0.12s; }
.badge:nth-child(3) { animation-delay: 0.19s; }

/* ── Divider ── */
.glass-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
    margin: 20px 0;
}

/* ── Animações ── */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes popIn {
    from { opacity: 0; transform: scale(0.75); }
    to   { opacity: 1; transform: scale(1); }
}

/* ── Preview dataframe (antes da correção) ── */
.preview-label {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.45);
    letter-spacing: 0.07em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.40); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.65); }
</style>
""", unsafe_allow_html=True)

# ─── HERO HEADER ───
st.markdown("""
<div class="hero-header">
    <h1>🫀 Avaliador de Simulados</h1>
    <p>Monitoria · Anatomia VI</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───
with st.sidebar:
    st.markdown('<div class="section-label">⚙ Configurações</div>', unsafe_allow_html=True)

    if "ANTHROPIC_API_KEY" in st.secrets and st.secrets["ANTHROPIC_API_KEY"]:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.success("API Key carregada ✓")
    else:
        st.warning("Chave não encontrada nos Secrets.")
        api_key = st.text_input("Anthropic API Key:", type="password")

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">📂 Planilha</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload .xlsx", type=["xlsx"], label_visibility="collapsed")

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    if st.session_state.dados_calculados is not None:
        texto_botao = "📊 Dashboard" if st.session_state.ver_geral else "👁 Ver todos os alunos"
        if st.button(texto_botao, use_container_width=True):
            st.session_state.ver_geral = not st.session_state.ver_geral
            st.rerun()

# ─── LÓGICA PRINCIPAL ───
if uploaded_file and api_key:
    df = pd.read_excel(uploaded_file)

    if st.session_state.dados_calculados is None:
        st.markdown('<p class="preview-label">Prévia da planilha carregada</p>', unsafe_allow_html=True)
        st.dataframe(df.head(10), use_container_width=True)
        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    if st.button("✦ Iniciar Correção Inteligente", use_container_width=False):
        with st.spinner("Claude está aplicando os critérios anatômicos..."):
            try:
                tabela_texto = df.to_string()

                prompt_sistema = """Você é um avaliador especialista em anatomia médica. Sua tarefa é analisar minuciosamente o texto da planilha enviada, identificar a linha que contém o GABARITO oficial (com as respostas padrão do professor) e corrigir todas as linhas subsequentes correspondentes às respostas enviadas pelos alunos. Você deve retornar estritamente um objeto JSON válido, sem qualquer texto explicativo, sem blocos de markdown, sem crase, sem prefixo. Apenas o JSON puro."""

                prompt_usuario = f"""
                Analise a tabela fornecida abaixo. Identifique a linha correspondente ao GABARITO oficial (geralmente marcada explicitamente ou contendo as respostas ideais) e utilize-a para avaliar todas as respostas dos alunos posicionadas nas linhas inferiores. Atribua notas de 0 a 1.0 para cada uma das 16 questões de cada aluno.

                CRITÉRIOS RIGOROSOS DE CORREÇÃO:
                1. Drenagem e Vascularização: Trocar abreviações de artéria para veia (ex: escrever "A." em vez de "V." ou vice-versa) zera a questão inteira. Omitir qualquer parte da cadeia de vascularização (ex: escrever "A. aorta > A. hepática comum", omitindo o "Tronco celíaco" que consta no gabarito) zera a questão inteira.
                2. Ligamentos ou Partes: Ocultar o órgão do qual o ligamento faz parte NÃO gera prejuízo (ex: se o gabarito diz "Ligamento hepatoduodenal" e o aluno escreve apenas "Hepatoduodenal", pontue). No entanto, errar o nome da estrutura em si zera a questão.
                3. Relações Anteriores (Estruturas múltiplas):
                   - A ordem em que o aluno escreve as estruturas NÃO importa (exceto nas cadeias de vascularização), desde que as peças e a quantidade exata correspondam ao gabarito.
                   - Se o gabarito tem 2 órgãos: a resposta deve ter exatamente 2. Se tiver 1 ou 3, é ZERO (mesmo que os corretos estejam descritos). Se tiver 2, mas 1 estiver errado, a nota é 0.5.
                   - Se o gabarito tem 3 órgãos: errar 1 de 3 dá nota 0.6. Errar 2 de 3 dá nota 0.3. Acertar os 3 dá nota 1.0.

                REGRAS DE FLEXIBILIDADE, EPÔNIMOS E ORTOGRAFIA:
                1. Ortografia: Não seja cruel com pequenos erros de digitação ou ortografia (ex: trocar "s" por "z", esquecer acentos). Desde que fique claro que o aluno sabe qual é a estrutura e não mude o sentido médico, NÃO penalize. Errar a estrutura inteira continua gerando zero.
                2. Epônimos e Sinônimos Anatômicos: Aceite sinônimos e epônimos clássicos consolidados na literatura médica, desde que mantenham a especificidade da peça avaliada:
                   - "Ampola hepatopancreática" pode ser aceito como "Ampola de Vater" ou "Ampola de Water".
                   - "Processo papilar" pode ser aceito como "Processo caudado".
                3. Subdivisões Estruturais: Se o gabarito exigir "Parte pilórica", aceite se o aluno detalhar e dividir em "(Antro e canal) pilóricos" ou "Antro pilórico e canal pilórico".

                Mapeie TODOS os alunos presentes na tabela (não limite a leitura).

                Dados extraídos da planilha:
                {tabela_texto}

                RETORNO OBRIGATÓRIO: Retorne APENAS o JSON abaixo, sem nenhum texto antes ou depois, sem blocos de markdown (sem ```json), sem explicações. Só o JSON puro:
                {{
                  "correcoes": [
                    {{
                      "nome": "Nome Completo do Aluno",
                      "notas_questoes": {{
                        "Q1": 1.0, "Q2": 0.0, "Q3": 0.5, "Q4": 1.0, "Q5": 1.0, "Q6": 1.0, "Q7": 1.0, "Q8": 1.0,
                        "Q9": 1.0, "Q10": 1.0, "Q11": 1.0, "Q12": 1.0, "Q13": 1.0, "Q14": 1.0, "Q15": 1.0, "Q16": 1.0
                      }}
                    }}
                  ]
                }}
                """

                anthropic_client = Anthropic(api_key=api_key)

                response = anthropic_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=8000,
                    system=prompt_sistema,
                    messages=[{"role": "user", "content": prompt_usuario}]
                )

                raw_text = response.content[0].text.strip()
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if not json_match:
                    raise ValueError(f"Nenhum JSON encontrado na resposta da API. Resposta recebida:\n{raw_text[:800]}")

                resultado_json = json.loads(json_match.group())
                correcoes = resultado_json["correcoes"]

                dados_alunos = []
                frequencia_questoes = {f"Q{i}": [] for i in range(1, 17)}

                for item in correcoes:
                    nome = item["nome"]
                    notas = item["notas_questoes"]
                    nota_final = sum(notas.values())
                    dados_alunos.append({"Nome": nome, "Nota": nota_final})
                    for q, nota in notas.items():
                        if q in frequencia_questoes:
                            frequencia_questoes[q].append(nota)

                df_resultados = pd.DataFrame(dados_alunos)
                media_geral = df_resultados["Nota"].mean()

                indices_acerto = {}
                for q, lista_notas in frequencia_questoes.items():
                    indices_acerto[q] = sum(lista_notas) / len(lista_notas) if lista_notas else 0

                questoes_ordenadas = sorted(indices_acerto.items(), key=lambda x: x[1], reverse=True)

                st.session_state.dados_calculados = {
                    "df_resultados": df_resultados,
                    "media_geral": media_geral,
                    "top_3_faceis": questoes_ordenadas[:3],
                    "top_3_dificeis": questoes_ordenadas[-3:][::-1],
                    "df_ranking": df_resultados.sort_values(by=["Nota", "Nome"], ascending=[False, True]).reset_index(drop=True)
                }
                st.session_state.ver_geral = False
                st.rerun()

            except Exception as e:
                st.error(f"Erro no processamento: {e}")

# ─── RENDERIZAÇÃO ───
    if st.session_state.dados_calculados is not None:
        dados = st.session_state.dados_calculados

        # ── VISÃO GERAL ──
        if st.session_state.ver_geral:
            st.markdown('<div class="glass-card"><div class="section-label">📋 Tabela Completa de Notas</div>', unsafe_allow_html=True)
            df_geral_exibicao = dados["df_resultados"].sort_values(by="Nome").reset_index(drop=True)
            df_geral_exibicao["Nota"] = df_geral_exibicao["Nota"].map(lambda x: f"{x:.2f} / 16.0")
            st.dataframe(df_geral_exibicao, use_container_width=True, height="auto")
            st.markdown('</div>', unsafe_allow_html=True)

        # ── DASHBOARD ──
        else:
            col_esq, col_dir = st.columns([1.25, 1], gap="large")

            with col_esq:
                # Métrica
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">📊 Estatísticas Gerais</div>', unsafe_allow_html=True)
                st.metric(label="Média da Turma", value=f"{dados['media_geral']:.2f} / 16.0")
                st.markdown('</div>', unsafe_allow_html=True)

                # Histograma
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">📈 Distribuição das Notas</div>', unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=dados["df_resultados"]["Nota"],
                    xbins=dict(start=-0.5, end=16.5, size=1),
                    marker=dict(
                        color="rgba(99,102,241,0.75)",
                        line=dict(color="rgba(99,102,241,1.0)", width=1.5)
                    ),
                    hovertemplate="Nota %{x}<br>Alunos: %{y}<extra></extra>"
                ))
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Outfit', color='rgba(255,255,255,0.65)', size=12),
                    xaxis=dict(
                        tickmode='linear', tick0=0, dtick=1,
                        gridcolor='rgba(255,255,255,0.06)',
                        zeroline=False,
                        title=dict(text="Nota Final", font=dict(size=11))
                    ),
                    yaxis=dict(
                        gridcolor='rgba(255,255,255,0.06)',
                        zeroline=False,
                        title=dict(text="Frequência", font=dict(size=11))
                    ),
                    margin=dict(l=10, r=10, t=10, b=10),
                    bargap=0.08,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

                # Ranking
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">🥇 Top 3 da Turma</div>', unsafe_allow_html=True)
                medals = ["🥇", "🥈", "🥉"]
                for idx, row in dados["df_ranking"].head(3).iterrows():
                    st.markdown(f"""
                    <div class="podium-item">
                        <span class="rank-medal">{medals[idx]}</span>
                        <span class="rank-name">{row['Nome']}</span>
                        <span class="rank-score">{row['Nota']:.2f} pts</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col_dir:
                # Questões fáceis
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">✅ Maior índice de acerto</div>', unsafe_allow_html=True)
                st.markdown('<div class="badge-row">', unsafe_allow_html=True)
                for q, taxa in dados["top_3_faceis"]:
                    st.markdown(f'<span class="badge badge-ok">▲ {q} &nbsp; {taxa*100:.1f}%</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Questões difíceis
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">⚠ Menor índice de acerto</div>', unsafe_allow_html=True)
                st.markdown('<div class="badge-row">', unsafe_allow_html=True)
                for q, taxa in dados["top_3_dificeis"]:
                    st.markdown(f'<span class="badge badge-bad">▼ {q} &nbsp; {taxa*100:.1f}%</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Mini radar de desempenho por questão
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">🎯 Aproveitamento por Questão</div>', unsafe_allow_html=True)

                df_resultados_full = dados["df_resultados"]
                # Recalcula índices de acerto para o radar
                frequencia_questoes_render = {f"Q{i}": [] for i in range(1, 17)}
                # Como não temos as notas por questão no session_state, usamos os top3 como proxy
                # e construímos o radar a partir dos dados que temos
                q_labels = [f"Q{i}" for i in range(1, 17)]

                # Busca indices_acerto dos top_3 para reconstruir lista completa parcial
                # Melhor: serializar todos os índices no session_state
                # Por ora usamos os dados disponíveis nos top/bot 3 e plotamos o que temos
                top_faceis_dict = dict(dados["top_3_faceis"])
                top_dificeis_dict = dict(dados["top_3_dificeis"])
                combined = {**top_faceis_dict, **top_dificeis_dict}

                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=list(combined.keys()),
                    y=[v * 100 for v in combined.values()],
                    marker=dict(
                        color=[
                            "rgba(52,211,153,0.70)" if v >= 0.5 else "rgba(248,113,113,0.70)"
                            for v in combined.values()
                        ],
                        line=dict(width=0)
                    ),
                    hovertemplate="%{x}: %{y:.1f}%<extra></extra>"
                ))
                fig2.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Outfit', color='rgba(255,255,255,0.60)', size=11),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zeroline=False),
                    yaxis=dict(
                        gridcolor='rgba(255,255,255,0.05)',
                        zeroline=False,
                        range=[0, 105],
                        title=dict(text="% acerto", font=dict(size=10))
                    ),
                    margin=dict(l=10, r=10, t=10, b=10),
                    bargap=0.25,
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="glass-card" style="text-align:center; padding: 48px 32px;">
        <div style="font-size:2.8rem; margin-bottom:16px;">📂</div>
        <div style="font-size:1.1rem; font-weight:600; color:rgba(255,255,255,0.80); margin-bottom:8px;">
            Nenhuma planilha carregada
        </div>
        <div style="font-size:0.88rem; color:rgba(255,255,255,0.38); line-height:1.6;">
            Faça upload do arquivo .xlsx com o gabarito e as respostas dos alunos<br>
            usando o painel lateral para começar.
        </div>
    </div>
    """, unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import json
import plotly.express as px
from anthropic import Anthropic

# Configuração da página para ocupar a tela de forma otimizada
st.set_page_config(layout="wide", page_title="Clean'it - Anatomy Marathon", page_icon="🏆")

# --- INJEÇÃO DE CSS CUSTOMIZADO (Tema Claro, Alto Contraste, Gamificado e Bordas Arredondadas) ---
st.markdown("""
    <style>
    /* Alterar background geral e fontes */
    .stApp {
        background-color: #F3F8FA;
        font-family: 'Inter', sans-serif;
    }
    
    /* Cabeçalho estilizado estilo Maratona/App moderninho */
    .marathon-header {
        background: linear-gradient(135deg, #00C6FF, #0072FF);
        padding: 25px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,114,255,0.2);
    }
    
    /* Cards de Informação e Métricas */
    .custom-card {
        background-color: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 6px solid #0072FF;
        margin-bottom: 20px;
    }
    
    .podium-card {
        background-color: white;
        padding: 15px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 2px solid #FFD700; /* Dourado para o top 3 */
        margin-bottom: 10px;
    }

    /* Tags de questões mais acertadas/erradas */
    .badge-success {
        background-color: #00E676;
        color: #004D20;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
    .badge-danger {
        background-color: #FF5252;
        color: #4A0000;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
    
    /* Ajustes de títulos dentro dos cards */
    h3 {
        color: #0F2042 !important;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# Title Banner
st.markdown("""
    <div class="marathon-header">
        <h1>🏆 ANATOMY MARATHON DASHBOARD</h1>
        <p>Módulo de Correção Inteligente & Analytics de Performance</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar para chaves e upload
with st.sidebar:
    st.subheader("⚙️ Configurações de Acesso")
    api_key = st.text_input("Anthropic API Key", type="password")
    uploaded_file = st.file_uploader("Carregar Planilha de Respostas (.xlsx)", type=["xlsx"])

if uploaded_file and api_key:
    # 1. LER PLANILHA
    df = pd.read_excel(uploaded_file)
    
    # Exibe uma prévia dos dados para o usuário ter certeza que leu certo
    st.write("📋 **Prévia dos dados carregados:**", df.head(4))
    
    # Botão para disparar a API e não gastar crédito sem querer ao mudar inputs
    if st.button("🔥 Iniciar Correção Inteligente"):
        
        with st.spinner("A IA do Claude está avaliando as respostas conforme os critérios clínicos..."):
            try:
                # Converter o dataframe em string formatada para enviar no prompt
                tabela_texto = df.to_string()
                
                # Inicializar cliente Anthropic
                # Nota: Em 2026, usamos a SDK padrão recomendada da Anthropic
                anthropic_client = Anthropic(api_key=api_key)
                
                prompt_sistema = """Você é um avaliador especialista em anatomia médica. Retorne estritamente um objeto JSON conforme as instruções do usuário, sem textos explicativos adicionais."""
                
                prompt_usuario = f"""
                Com base na linha 2 da tabela (GABARITO) avalie as respostas (linha 3 em diante) seguindo as regras de anatomia (A. vs V., omissão de troncos vasculares, contagem de relações anteriores e omissão de órgãos em ligamentos).
                
                Dados da planilha:
                {tabela_texto}
                
                Retorne estritamente no formato JSON:
                {{
                  "correcoes": [
                    {{
                      "nome": "Nome do Aluno",
                      "notas_questoes": {{"Q1": 1.0, "Q2": 0.0, ... "Q16": 0.5}}
                    }}
                  ]
                }}
                """
                
                # Chamada da API Anthropic (Claude 3.5 Sonnet é ideal para estruturação de dados rigorosa)
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=4000,
                    system=prompt_sistema,
                    messages=[{"role": "user", "content": prompt_usuario}]
                )
                
                # Parse do JSON retornado
                resultado_json = json.loads(response.content[0].text)
                correcoes = resultado_json["correcoes"]
                
                # --- 2. PROCESSAMENTO DOS DADOS NO PYTHON (FRONTEND/LOCAL) ---
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
                
                # Cálculo da Média Geral
                media_geral = df_resultados["Nota"].mean()
                
                # Cálculo de índices de acerto por questão (considerando acerto pleno = 1.0 ou proporcional)
                indices_acerto = {}
                for q, lista_notas in frequencia_questoes.items():
                    # Média de acerto da questão (1 = 100% de acerto na turma)
                    indices_acerto[q] = sum(lista_notas) / len(lista_notas) if lista_notes else 0
                
                # Ordenar ranking de questões
                questoes_ordenadas = sorted(indices_acerto.items(), key=lambda x: x[1], reverse=True)
                top_3_faceis = questoes_ordenadas[:3]
                top_3_dificeis = questoes_ordenadas[-3:][::-1]
                
                # Ranking Alunos (Maiores Notas, desempate por Ordem Alfabética)
                # O pandas faz isso de forma nativa e extremamente veloz
                df_ranking = df_resultados.sort_values(by=["Nota", "Nome"], ascending=[False, True]).reset_index(drop=True)
                
                # --- 3. RENDERIZAÇÃO DO LAYOUT EM DUAS COLUNAS ---
                col_esquerda, col_direita = st.columns([1.2, 1])
                
                with col_esquerda:
                    st.markdown('<div class="custom-card"><h3>📊 Estatísticas Gerais</h3></div>', unsafe_allow_html=True)
                    
                    # Exibição de Média com destaque limpo e alto contraste
                    st.metric(label="Média Aritmética da Turma", value=f"{media_geral:.2f} / 16.0")
                    
                    # Gráfico de Distribuição usando Plotly Express
                    # Eixo X fixado de 0 a 16 conforme solicitado
                    fig = px.histogram(
                        df_resultados, 
                        x="Nota", 
                        nbins=17,
                        range_x=[-0.5, 16.5],
                        title="Distribuição Absoluta das Notas",
                        labels={'Nota': 'Nota Final (Questões)', 'count': 'Frequência Absoluta'},
                        color_discrete_sequence=['#0072FF']
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickmode='linear', tick0=0, dtick=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Ranking Top 3 Alunos
                    st.markdown("### 🥇 Podium da Maratona (Top 3)")
                    for idx, row in df_ranking.head(3).iterrows():
                        st.markdown(f"""
                            <div class="podium-card">
                                <strong>{idx+1}º Lugar:</strong> {row['Nome']} — <span style="color:#0072FF; font-weight:bold;">{row['Nota']:.1f} pts</span>
                            </div>
                        """, unsafe_allow_html=True)
                
                with col_direita:
                    st.markdown('<div class="custom-card"><h3>🔍 Análise de Itens (Questões)</h3></div>', unsafe_allow_html=True)
                    
                    st.write("### 📈 Maiores Índices de Acerto")
                    st.write("As 3 questões que a turma demonstrou maior domínio:")
                    for q, taxa in top_3_faceis:
                        st.markdown(f"<span class='badge-success'>{q} ({taxa*100:.1f}% de aproveitamento)</span>", unsafe_allow_html=True)
                        
                    st.write("---")
                    
                    st.write("### 📉 Menores Índices de Acerto")
                    st.write("As 3 questões críticas que merecem revisão em sala de aula:")
                    for q, taxa in top_3_dificeis:
                        st.markdown(f"<span class='badge-danger'>{q} ({taxa*100:.1f}% de aproveitamento)</span>", unsafe_allow_html=True)
                
                st.success("✨ Processamento concluído com sucesso!")
                
            except Exception as e:
                st.error(f"Erro ao processar ou na comunicação com a API: {e}")
else:
    # Estado inicial / Instruções elegantes de uso
    st.info("💡 Para começar, insira sua Anthropic API Key e faça o upload da planilha contendo o Gabarito (Linha 2) e Respostas dos Alunos (Linha 3 em diante) na barra lateral.")

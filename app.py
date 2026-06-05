import streamlit as st
import pandas as pd
import json
import plotly.express as px
from anthropic import Anthropic

# Configuração da página para ocupar a tela de forma otimizada
st.set_page_config(layout="wide", page_title="Avaliador de Simulados", page_icon="🏆")

# --- INICIALIZAÇÃO DO ESTADO GLOBAL (SESSION STATE) ---
if "ver_geral" not in st.session_state:
    st.session_state.ver_geral = False
if "dados_calculados" not in st.session_state:
    st.session_state.dados_calculados = None

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

# Banner de Título Atualizado conforme solicitado
st.markdown("""
    <div class="marathon-header">
        <h1>🏆 AVALIADOR DE SIMULADOS</h1>
        <p>Monitoria Anatomia VI</p>
    </div>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DA BARRA LATERAL ---
with st.sidebar:
    st.subheader("⚙️ Configurações de Acesso")
    
    # 1. Verifica se a chave existe e está preenchida no st.secrets
    if "ANTHROPIC_API_KEY" in st.secrets and st.secrets["ANTHROPIC_API_KEY"]:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.success("✅ API Key carregada do sistema!")
    else:
        # 2. Caso contrário, exibe o campo para digitação manual na interface
        st.warning("⚠️ Chave não encontrada nos Secrets.")
        api_key = st.text_input("Digite sua Anthropic API Key manualmente:", type="password")
        
    uploaded_file = st.file_uploader("Carregar Planilha de Respostas (.xlsx)", type=["xlsx"])
    
    st.write("---")
    
    # Botão de alternância de visão (Geral vs Dashboard)
    # Só faz sentido exibir se já houver dados processados na memória
    if st.session_state.dados_calculados is not None:
        texto_botao = "📊 Voltar para o Dashboard" if st.session_state.ver_geral else "👁️ Ver Geral"
        if st.button(texto_botao, use_container_width=True):
            st.session_state.ver_geral = not st.session_state.ver_geral
            st.rerun()

# --- LÓGICA PRINCIPAL DO APP ---
if uploaded_file and api_key:
    # Ler a planilha do Excel (Google Planilhas exportado)
    df = pd.read_excel(uploaded_file)
    
    # Só exibe a prévia da planilha original se ainda não tiver processado os dados para manter o visual limpo
    if st.session_state.dados_calculados is None:
        st.write("📋 **Prévia dos dados carregados (Gabarito na linha 2 do Excel):**", df.head(4))
    
    # Botão para disparar o processo da API
    if st.button("🔥 Iniciar Correção Inteligente"):
        with st.spinner("A IA do Claude está avaliando as respostas com base nos critérios anatômicos detalhados..."):
            try:
                tabela_texto = df.to_string()
                
                prompt_sistema = """Você é um avaliador especialista em anatomy médica. Sua tarefa é corrigir as respostas dissertativas dos alunos comparando-as com o gabarito oficial. Você deve retornar estritamente um objeto JSON válido, sem qualquer texto explicativo antes ou depois."""
                
                prompt_usuario = f"""
                Com base na linha 2 da tabela (GABARITO) avalie as respostas (linha 3 em diante) e atribua notas de 0 a 1.0 para cada uma das 16 questões.

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

                Dados extraídos da planilha:
                {tabela_texto}
                
                RETORNO OBRIGATÓRIO:
                Gere única e estritamente o JSON abaixo preenchido para todos os alunos encontrados a partir da linha 3:
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
                    model="claude-3-5-sonnet-latest",
                    max_tokens=4000,
                    system=prompt_sistema,
                    messages=[{"role": "user", "content": prompt_usuario}]
                )
                
                resultado_json = json.loads(response.content[0].text)
                correcoes = resultado_json["correcoes"]
                
                # --- ESTRUTURAÇÃO DOS DADOS NO LOCAL ---
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
                
                # Guardar tudo no session_state para não perder ao clicar em botões
                st.session_state.dados_calculados = {
                    "df_resultados": df_resultados,
                    "media_geral": media_geral,
                    "top_3_faceis": questoes_ordenadas[:3],
                    "top_3_dificeis": questoes_ordenadas[-3:][::-1],
                    "df_ranking": df_resultados.sort_values(by=["Nota", "Nome"], ascending=[False, True]).reset_index(drop=True)
                }
                st.session_state.ver_geral = False  # Reseta para o dashboard por padrão ao re-corrigir
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao processar as notas ou se comunicar com a API do Claude: {e}")

    # --- RENDERIZAÇÃO CONDICIONAL DA INTERFACE ---
    if st.session_state.dados_calculados is not None:
        dados = st.session_state.dados_calculados
        
        # VISÃO 1: VER GERAL (TABELA COMPLETA)
        if st.session_state.ver_geral:
            st.markdown('<div class="custom-card"><h3>📋 Tabela Geral de Notas e Pontuações</h3></div>', unsafe_allow_html=True)
            
            # Formatação simples para exibir na tabela de forma limpa, ordenada alfabeticamente por padrão
            df_geral_exibicao = dados["df_resultados"].sort_values(by="Nome").reset_index(drop=True)
            df_geral_exibicao["Nota"] = df_geral_exibicao["Nota"].map(lambda x: f"{x:.2f} / 16.0")
            
            st.dataframe(df_geral_exibicao, use_container_width=True, height=500)
            
        # VISÃO 2: DASHBOARD TRADICIONAL AVALIADO
        else:
            col_esquerda, col_direita = st.columns([1.2, 1])
            
            with col_esquerda:
                st.markdown('<div class="custom-card"><h3>📊 Estatísticas do Simulado</h3></div>', unsafe_allow_html=True)
                
                st.metric(label="Média Aritmética da Turma", value=f"{dados['media_geral']:.2f} / 16.0")
                
                fig = px.histogram(
                    dados["df_resultados"], 
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
                
                st.markdown("### 🥇 Ranking da Turma (Top 3)")
                for idx, row in dados["df_ranking"].head(3).iterrows():
                    st.markdown(f"""
                        <div class="podium-card">
                            <strong>{idx+1}º Lugar:</strong> {row['Nome']} — <span style="color:#0072FF; font-weight:bold;">{row['Nota']:.2f} pts</span>
                        </div>
                    """, unsafe_allow_html=True)
            
            with col_direita:
                st.markdown('<div class="custom-card"><h3>🔍 Análise de Questões</h3></div>', unsafe_allow_html=True)
                
                st.write("### 📈 As 3 Questões com Maior Índice de Acerto")
                for q, taxa in dados["top_3_faceis"]:
                    st.markdown(f"<span class='badge-success'>{q} ({taxa*100:.1f}% de aproveitamento)</span>", unsafe_allow_html=True)
                    
                st.write("---")
                
                st.write("### 📉 As 3 Questões com Menor Índice de Acerto")
                for q, taxa in dados["top_3_dificeis"]:
                    st.markdown(f"<span class='badge-danger'>{q} ({taxa*100:.1f}% de aproveitamento)</span>", unsafe_allow_html=True)
else:
    st.info("💡 Pronto para começar! Certifique-se de que sua API Key está configurada nos Secrets do Streamlit ou na barra lateral e faça o upload da sua planilha .xlsx.")

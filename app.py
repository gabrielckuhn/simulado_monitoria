import streamlit as st
import pandas as pd
import json
import re
import plotly.graph_objects as go
import numpy as np
from anthropic import Anthropic

st.set_page_config(layout="wide", page_title="Simulados · Anatomia VI", page_icon="🫀")

if "ver_geral" not in st.session_state:
    st.session_state.ver_geral = False
if "dados_calculados" not in st.session_state:
    st.session_state.dados_calculados = None

# ─────────────────────────────────────────────────────────────────
#  LIQUID GLASS  —  fundo claro + filtro SVG de refração real
#  Técnica extraída de github.com/...liquid-glass-for-the-web
#  O feDisplacementMap distorce o conteúdo por baixo da card,
#  o feImage injeta um displacement map gerado por canvas via JS.
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<!-- SVG filter placeholder — preenchido pelo JS abaixo -->
<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"
     style="position:absolute;overflow:hidden;pointer-events:none"
     color-interpolation-filters="sRGB">
  <defs id="svg-defs"></defs>
</svg>

<style>
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; }

/* ── Fundo claro com orbs pastéis ── */
.stApp {
    background: #f0f2f7;
    font-family: 'Figtree', sans-serif;
    color: #1a1c2e;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
}

/* Orb 1 — azul-lavanda */
.stApp::before {
    content: '';
    position: fixed;
    top: -180px; left: -180px;
    width: 640px; height: 640px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(139,120,255,0.22) 0%, transparent 68%);
    animation: orb1 20s ease-in-out infinite;
    pointer-events: none; z-index: 0;
}
/* Orb 2 — azul-céu */
.stApp::after {
    content: '';
    position: fixed;
    bottom: -120px; right: -120px;
    width: 560px; height: 560px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(56,189,248,0.18) 0%, transparent 68%);
    animation: orb2 25s ease-in-out infinite;
    pointer-events: none; z-index: 0;
}

@keyframes orb1 {
    0%,100% { transform: translate(0,0) scale(1); }
    33%      { transform: translate(90px,70px) scale(1.12); }
    66%      { transform: translate(-50px,110px) scale(0.94); }
}
@keyframes orb2 {
    0%,100% { transform: translate(0,0) scale(1); }
    40%      { transform: translate(-70px,-90px) scale(1.09); }
    70%      { transform: translate(60px,-45px) scale(0.91); }
}

/* Orb 3 extra — rosa-pêssego canto superior direito */
.orb3 {
    position: fixed;
    top: -100px; right: 10%;
    width: 420px; height: 420px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(251,146,60,0.13) 0%, transparent 65%);
    animation: orb3 28s ease-in-out infinite;
    pointer-events: none; z-index: 0;
}
@keyframes orb3 {
    0%,100% { transform: translate(0,0) scale(1); }
    50%      { transform: translate(40px,80px) scale(1.07); }
}

/* ── Layout ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1240px !important;
    position: relative; z-index: 1;
}

/* ── Sidebar — nunca colapsa ── */
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    display: none !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    display: flex !important;
    visibility: visible !important;
    margin-left: 0 !important;
    transform: none !important;
    min-width: 14rem !important;
}
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.52) !important;
    backdrop-filter: blur(32px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(32px) saturate(180%) !important;
    border-right: 1px solid rgba(255,255,255,0.70) !important;
    box-shadow: 4px 0 32px rgba(100,80,200,0.06) !important;
}
[data-testid="stSidebar"] * { color: #1a1c2e !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(139,120,255,0.14) !important;
    border: 1px solid rgba(139,120,255,0.35) !important;
    color: #4a3fbf !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.25s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(139,120,255,0.28) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(139,120,255,0.20) !important;
}

/* ── Botão principal ── */
.stButton > button {
    background: linear-gradient(135deg, #7c6ff7, #38bdf8) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.65rem 1.6rem !important;
    font-family: 'Figtree', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 18px rgba(124,111,247,0.30) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 10px 30px rgba(124,111,247,0.40) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.50) !important;
    border: 1.5px dashed rgba(124,111,247,0.35) !important;
    border-radius: 14px !important;
    padding: 1rem !important;
}

/* ── Text input ── */
.stTextInput input {
    background: rgba(255,255,255,0.65) !important;
    border: 1px solid rgba(124,111,247,0.25) !important;
    border-radius: 12px !important;
    color: #1a1c2e !important;
    font-family: 'Figtree', sans-serif !important;
}

/* ── Metric ── */
[data-testid="stMetric"] {
    background: transparent !important;
    border: none !important;
    padding: 0.2rem 0 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Figtree', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
    color: #1a1c2e !important;
}
[data-testid="stMetricLabel"] {
    color: rgba(26,28,46,0.50) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid rgba(124,111,247,0.12) !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #7c6ff7 !important; }

/* ── Alertas ── */
.stAlert {
    background: rgba(255,255,255,0.60) !important;
    border: 1px solid rgba(124,111,247,0.18) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(12px) !important;
    color: #1a1c2e !important;
}

/* ────────────────────────────────────────────────
   LIQUID GLASS CARD
   A card com duas camadas:
   ::after  — aplica o filtro SVG de refração no que está por baixo
   ::before — sobreposição especular / tint branco
   O conteúdo fica em z-index normal, acima das duas pseudo-layers
   ──────────────────────────────────────────────── */
.glass-card {
    position: relative;
    border-radius: 22px;
    padding: 24px 28px;
    margin-bottom: 18px;
    isolation: isolate;
    /* sombra externa suave */
    box-shadow:
        0 2px 0px rgba(255,255,255,0.90) inset,   /* highlight top */
        0 8px 32px rgba(100,80,200,0.10),
        0 1px 0 rgba(255,255,255,0.80);
    animation: fadeUp 0.5s ease both;
    overflow: hidden;
}

/* Camada de refração — aplica filtro SVG no backdrop */
.glass-card::after {
    content: '';
    position: absolute;
    inset: 0;
    z-index: -2;
    border-radius: inherit;
    /* fallback visual se SVG não disponível */
    backdrop-filter: blur(0.5px);
    -webkit-backdrop-filter: url(#lg-filter) blur(0.5px);
    backdrop-filter: url(#lg-filter) blur(0.5px);
}

/* Tint branco translúcido + borda especular */
.glass-card::before {
    content: '';
    position: absolute;
    inset: 0;
    z-index: -1;
    border-radius: inherit;
    background: rgba(255,255,255,0.46);
    border: 1px solid rgba(255,255,255,0.82);
    /* sombra interna que simula espessura do vidro */
    box-shadow:
        inset 0 0 18px -4px rgba(255,255,255,0.70),
        inset 0 1px 1px rgba(255,255,255,0.95);
}

/* ── Hero header com glass mais intenso ── */
.hero-header {
    position: relative;
    border-radius: 26px;
    padding: 38px 40px;
    text-align: center;
    margin-bottom: 28px;
    isolation: isolate;
    box-shadow:
        0 2px 0 rgba(255,255,255,0.95) inset,
        0 16px 48px rgba(100,80,200,0.13),
        0 1px 0 rgba(255,255,255,0.85);
    animation: fadeUp 0.5s ease both;
    overflow: hidden;
}
.hero-header::after {
    content: '';
    position: absolute;
    inset: 0; z-index: -2;
    border-radius: inherit;
    -webkit-backdrop-filter: url(#lg-filter) blur(1px);
    backdrop-filter: url(#lg-filter) blur(1px);
}
.hero-header::before {
    content: '';
    position: absolute;
    inset: 0; z-index: -1;
    border-radius: inherit;
    background: linear-gradient(
        135deg,
        rgba(255,255,255,0.62) 0%,
        rgba(240,235,255,0.48) 50%,
        rgba(224,242,254,0.50) 100%
    );
    border: 1px solid rgba(255,255,255,0.88);
    box-shadow:
        inset 0 0 24px -6px rgba(124,111,247,0.12),
        inset 0 1px 1px rgba(255,255,255,1.0);
}
/* Faixa de luz especular diagonal */
.hero-header .specular {
    position: absolute;
    top: 0; left: -40%;
    width: 70%; height: 100%;
    background: linear-gradient(105deg,
        rgba(255,255,255,0) 30%,
        rgba(255,255,255,0.28) 50%,
        rgba(255,255,255,0) 70%);
    transform: skewX(-15deg);
    pointer-events: none;
    animation: specularSlide 8s ease-in-out infinite;
    z-index: 1;
}
@keyframes specularSlide {
    0%,100% { left: -40%; opacity: 0.7; }
    50%      { left: 80%;  opacity: 1.0; }
}

.hero-header h1 {
    font-family: 'Figtree', sans-serif !important;
    font-size: 2.1rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    color: #1a1c2e !important;
    position: relative; z-index: 2;
    margin-bottom: 6px !important;
}
.hero-header p {
    color: rgba(26,28,46,0.48) !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
    position: relative; z-index: 2;
}

/* ── Section label ── */
.section-label {
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: rgba(124,111,247,0.85);
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(124,111,247,0.25), transparent);
}

/* ── Podium ── */
.podium-item {
    display: flex;
    align-items: center;
    gap: 12px;
    position: relative;
    border-radius: 14px;
    padding: 13px 16px;
    margin-bottom: 9px;
    isolation: isolate;
    box-shadow:
        0 1px 0 rgba(255,255,255,0.88) inset,
        0 4px 16px rgba(100,80,200,0.07);
    animation: fadeUp 0.45s ease both;
    overflow: hidden;
    transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.podium-item::after {
    content: ''; position: absolute; inset: 0; z-index: -2;
    border-radius: inherit;
    -webkit-backdrop-filter: url(#lg-filter);
    backdrop-filter: url(#lg-filter);
}
.podium-item::before {
    content: ''; position: absolute; inset: 0; z-index: -1;
    border-radius: inherit;
    background: rgba(255,255,255,0.50);
    border: 1px solid rgba(255,255,255,0.80);
}
.podium-item:hover { transform: translateX(5px); box-shadow: 0 6px 22px rgba(100,80,200,0.12); }
.podium-item:nth-child(1) { border-left: 3px solid #f5b400; animation-delay:0.05s; }
.podium-item:nth-child(2) { border-left: 3px solid #9ca3af; animation-delay:0.10s; }
.podium-item:nth-child(3) { border-left: 3px solid #cd7f32; animation-delay:0.15s; }
.rank-medal { font-size: 1.35rem; min-width: 26px; }
.rank-name  { flex:1; font-weight:500; font-size:0.92rem; color:#1a1c2e; }
.rank-score {
    font-weight:700; font-size:1rem;
    background: linear-gradient(135deg, #7c6ff7, #38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ── Badges ── */
.badge-row { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 8px; }
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 6px 13px; border-radius: 30px;
    font-size: 0.80rem; font-weight: 600; letter-spacing: 0.02em;
    animation: popIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both;
}
.badge-ok  { background: rgba(52,199,89,0.14);  border:1px solid rgba(52,199,89,0.35);  color:#15803d; }
.badge-bad { background: rgba(239,68,68,0.12);  border:1px solid rgba(239,68,68,0.28);  color:#b91c1c; }
.badge:nth-child(1){animation-delay:.04s}
.badge:nth-child(2){animation-delay:.10s}
.badge:nth-child(3){animation-delay:.16s}

/* ── Divider ── */
.glass-divider {
    height:1px;
    background: linear-gradient(90deg, transparent, rgba(124,111,247,0.18), transparent);
    margin: 18px 0;
}

/* ── Animações ── */
@keyframes fadeUp {
    from { opacity:0; transform:translateY(16px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes popIn {
    from { opacity:0; transform:scale(0.78); }
    to   { opacity:1; transform:scale(1); }
}

/* ── Preview label ── */
.preview-label {
    font-size:0.74rem; color:rgba(26,28,46,0.42);
    letter-spacing:0.07em; text-transform:uppercase; margin-bottom:8px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(124,111,247,0.28); border-radius:5px; }
::-webkit-scrollbar-thumb:hover { background:rgba(124,111,247,0.50); }
</style>

<!-- Orb3 extra injetado como div (::before e ::after já usados) -->
<div class="orb3"></div>

<!-- ════════════════════════════════════════════════════
     LIQUID GLASS ENGINE
     Porta fiel das funções do projeto liquid-glass-for-the-web
     Gera displacement map por canvas e injeta no SVG filter.
     O filtro é aplicado via backdrop-filter: url(#lg-filter)
     nas classes .glass-card, .hero-header e .podium-item.
     ════════════════════════════════════════════════════ -->
<script>
(function(){
  "use strict";

  // ── Parâmetros do glass (calibrados para fundo claro) ──
  var GLASS_THICKNESS  = 60;
  var BEZEL_WIDTH      = 48;
  var IOR              = 2.4;
  var SCALE_RATIO      = 0.85;
  var BLUR_AMT         = 0.4;
  var SPEC_OPACITY     = 0.38;
  var SPEC_SAT         = 3;
  var RADIUS           = 22; // px — deve casar com border-radius do CSS

  // ── Funções de superfície ──
  function convex_squircle(x){ return Math.pow(1 - Math.pow(1-x,4), 0.25); }

  // ── Perfil de refração ──
  function calcProfile(glassThick, bezelW, heightFn, ior, S){
    S = S||128;
    var eta = 1/ior;
    var profile = new Float64Array(S);
    for(var i=0;i<S;i++){
      var x  = i/S;
      var y  = heightFn(x);
      var dx = x<1 ? 0.0001 : -0.0001;
      var y2 = heightFn(x+dx);
      var deriv = (y2-y)/dx;
      var mag   = Math.sqrt(deriv*deriv+1);
      var nx=-deriv/mag, ny=-1/mag;
      var dot=ny, k=1-eta*eta*(1-dot*dot);
      if(k<0){ profile[i]=0; continue; }
      var sq=Math.sqrt(k);
      var rx=-(eta*dot+sq)*nx;
      var ry=eta-(eta*dot+sq)*ny;
      profile[i] = rx*((y*bezelW+glassThick)/ry);
    }
    return profile;
  }

  // ── Displacement map ──
  function buildDispMap(w,h,radius,bezelW,profile,maxDisp){
    var c=document.createElement('canvas');
    c.width=w; c.height=h;
    var ctx=c.getContext('2d');
    var img=ctx.createImageData(w,h);
    var d=img.data;
    for(var i=0;i<d.length;i+=4){ d[i]=128;d[i+1]=128;d[i+2]=0;d[i+3]=255; }

    var r=radius, rSq=r*r, r1Sq=(r+1)*(r+1);
    var rBSq=Math.max(r-bezelW,0); rBSq=rBSq*rBSq;
    var wB=w-r*2, hB=h-r*2, S=profile.length;

    for(var y1=0;y1<h;y1++){
      for(var x1=0;x1<w;x1++){
        var x = x1<r ? x1-r : (x1>=w-r ? x1-r-wB : 0);
        var y = y1<r ? y1-r : (y1>=h-r ? y1-r-hB : 0);
        var dSq=x*x+y*y;
        if(dSq>r1Sq||dSq<rBSq) continue;
        var dist=Math.sqrt(dSq);
        var fromSide=r-dist;
        var op=dSq<rSq?1:1-(dist-Math.sqrt(rSq))/(Math.sqrt(r1Sq)-Math.sqrt(rSq));
        if(op<=0||dist===0) continue;
        var cos=x/dist, sin=y/dist;
        var bi=Math.min(((fromSide/bezelW)*S)|0, S-1);
        var disp=profile[bi]||0;
        var dX=(-cos*disp)/maxDisp;
        var dY=(-sin*disp)/maxDisp;
        var idx=(y1*w+x1)*4;
        d[idx  ]=(128+dX*127*op+0.5)|0;
        d[idx+1]=(128+dY*127*op+0.5)|0;
      }
    }
    ctx.putImageData(img,0,0);
    return c.toDataURL();
  }

  // ── Specular map ──
  function buildSpecMap(w,h,radius,bezelW,angle){
    angle=angle!=null?angle:Math.PI/3;
    var c=document.createElement('canvas');
    c.width=w; c.height=h;
    var ctx=c.getContext('2d');
    var img=ctx.createImageData(w,h);
    var d=img.data; d.fill(0);

    var r=radius, rSq=r*r, r1Sq=(r+1)*(r+1);
    var rBSq=Math.max(r-bezelW,0); rBSq=rBSq*rBSq;
    var wB=w-r*2, hB=h-r*2;
    var sv=[Math.cos(angle),Math.sin(angle)];

    for(var y1=0;y1<h;y1++){
      for(var x1=0;x1<w;x1++){
        var x=x1<r?x1-r:(x1>=w-r?x1-r-wB:0);
        var y=y1<r?y1-r:(y1>=h-r?y1-r-hB:0);
        var dSq=x*x+y*y;
        if(dSq>r1Sq||dSq<rBSq) continue;
        var dist=Math.sqrt(dSq);
        var fromSide=r-dist;
        var op=dSq<rSq?1:1-(dist-Math.sqrt(rSq))/(Math.sqrt(r1Sq)-Math.sqrt(rSq));
        if(op<=0||dist===0) continue;
        var cos=x/dist, sin=-y/dist;
        var dot=Math.abs(cos*sv[0]+sin*sv[1]);
        var edge=Math.sqrt(Math.max(0,1-(1-fromSide)*(1-fromSide)));
        var coeff=dot*edge;
        var col=(255*coeff)|0;
        var alpha=(col*coeff*op)|0;
        var idx=(y1*w+x1)*4;
        d[idx]=col; d[idx+1]=col; d[idx+2]=col; d[idx+3]=alpha;
      }
    }
    ctx.putImageData(img,0,0);
    return c.toDataURL();
  }

  // ── Medida representativa de uma card ──
  // Usamos 560×180 como tamanho "médio" de uma card de dashboard
  var W=560, H=180;

  function build(){
    var defs = document.getElementById('svg-defs');
    if(!defs) return;

    var clampedBezel = Math.min(BEZEL_WIDTH, RADIUS-1, Math.min(W,H)/2-1);
    var profile = calcProfile(GLASS_THICKNESS, clampedBezel, convex_squircle, IOR, 128);
    var maxDisp = 0;
    for(var i=0;i<profile.length;i++) if(Math.abs(profile[i])>maxDisp) maxDisp=Math.abs(profile[i]);
    if(!maxDisp) maxDisp=1;

    var dispUrl = buildDispMap(W,H,RADIUS,clampedBezel,profile,maxDisp);
    var specUrl = buildSpecMap(W,H,RADIUS,clampedBezel*2.2);
    var scale   = maxDisp * SCALE_RATIO;

    defs.innerHTML = `
      <filter id="lg-filter" x="0%" y="0%" width="100%" height="100%"
              color-interpolation-filters="sRGB">
        <feGaussianBlur in="SourceGraphic" stdDeviation="${BLUR_AMT}" result="blurred"/>
        <feImage href="${dispUrl}" x="0" y="0" width="${W}" height="${H}" result="dmap"
                 preserveAspectRatio="none"/>
        <feDisplacementMap in="blurred" in2="dmap"
            scale="${scale}" xChannelSelector="R" yChannelSelector="G"
            result="displaced"/>
        <feColorMatrix in="displaced" type="saturate" values="${SPEC_SAT}" result="dsat"/>
        <feImage href="${specUrl}" x="0" y="0" width="${W}" height="${H}" result="spec"
                 preserveAspectRatio="none"/>
        <feComposite in="dsat" in2="spec" operator="in" result="spec_masked"/>
        <feComponentTransfer in="spec" result="spec_faded">
          <feFuncA type="linear" slope="${SPEC_OPACITY}"/>
        </feComponentTransfer>
        <feBlend in="spec_masked" in2="displaced" mode="normal" result="with_sat"/>
        <feBlend in="spec_faded"  in2="with_sat"  mode="normal"/>
      </filter>
    `;
  }

  // Garante que o DOM esteja pronto
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', build);
  } else {
    requestAnimationFrame(function(){ requestAnimationFrame(build); });
  }
})();
</script>
""", unsafe_allow_html=True)

# ─── HERO HEADER ───
st.markdown("""
<div class="hero-header">
    <div class="specular"></div>
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
                1. Drenagem e Vascularização: Trocar abreviações de artéria para veia (ex: escrever "A." in vez de "V." ou vice-versa) zera a questão inteira. Omitir qualquer parte da cadeia de vascularização (ex: escrever "A. aorta > A. hepática comum", omitindo o "Tronco celíaco" que consta no gabarito) zera a questão inteira.
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
                    raise ValueError(f"Nenhum JSON encontrado na resposta da API.\n{raw_text[:800]}")
                resultado_json = json.loads(json_match.group())
                correcoes = resultado_json["correcoes"]

                dados_alunos = []
                frequencia_questoes = {f"Q{i}": [] for i in range(1, 17)}
                for item in correcoes:
                    nome  = item["nome"]
                    notas = item["notas_questoes"]
                    nota_final = sum(notas.values())
                    dados_alunos.append({"Nome": nome, "Nota": nota_final})
                    for q, nota in notas.items():
                        if q in frequencia_questoes:
                            frequencia_questoes[q].append(nota)

                df_resultados = pd.DataFrame(dados_alunos)
                media_geral   = df_resultados["Nota"].mean()
                
                mediana_questoes = np.median(df_resultados["Nota"])
                desvio_padrao_questoes = np.std(df_resultados["Nota"])
                
                indices_acerto = {
                    q: (sum(v)/len(v) if v else 0)
                    for q, v in frequencia_questoes.items()
                }
                questoes_ordenadas = sorted(indices_acerto.items(), key=lambda x: x[1], reverse=True)

                st.session_state.dados_calculados = {
                    "df_resultados": df_resultados,
                    "media_geral":   media_geral,
                    "mediana_questoes": mediana_questoes,
                    "desvio_padrao": desvio_padrao_questoes,
                    "top_3_faceis":  questoes_ordenadas[:3],
                    "top_3_dificeis":questoes_ordenadas[-3:][::-1],
                    "df_ranking":    df_resultados.sort_values(by=["Nota","Nome"], ascending=[False,True]).reset_index(drop=True),
                    "indices_acerto": indices_acerto,
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
            df_geral = dados["df_resultados"].sort_values(by="Nome").reset_index(drop=True).copy()
            df_geral["Nota"] = df_geral["Nota"].map(lambda x: f"{x:.2f} / 16.0")
            st.dataframe(df_geral, use_container_width=True, height="auto")
            st.markdown('</div>', unsafe_allow_html=True)

        # ── DASHBOARD ──
        else:
            col_esq, col_dir = st.columns([1.25, 1], gap="large")

            with col_esq:
                # Métrica + histograma
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">📊 Estatísticas Gerais</div>', unsafe_allow_html=True)
                
                # Conversão e formatação compacta para evitar quebra de contêiner
                nota_escala_10 = (dados['media_geral'] * 10) / 16
                mediana_escala_10 = (dados['mediana_questoes'] * 10) / 16
                desvio_escala_10 = (dados['desvio_padrao'] * 10) / 16
                
                # Exibição: Média sem decimais nos acertos, o resto reduzido em cinza e entre parênteses
                texto_metrica = (
                    f"{dados['media_geral']:.0f}/16 acertos "
                    f"<span style='color: #707280; font-size: 0.52em; font-weight: 500; letter-spacing: 0px; text-transform: none;'>"
                    f"(Nota: {nota_escala_10:.1f} · Mediana: {dados['mediana_questoes']:.1f}/16 [{desvio_escala_10:.1f} DP])"
                    f"</span>"
                )
                
                st.markdown(f"""
                <div data-testid="stMetric">
                    <label data-testid="stMetricLabel">Média da Turma</label>
                    <div data-testid="stMetricValue" style="font-size: 1.45rem; line-height: 1.2;">
                        {texto_metrica}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=dados["df_resultados"]["Nota"],
                    xbins=dict(start=-0.5, end=16.5, size=1),
                    marker=dict(
                        color="rgba(124,111,247,0.60)",
                        line=dict(color="rgba(124,111,247,0.90)", width=1.5)
                    ),
                    hovertemplate="Nota %{x}<br>Alunos: %{y}<extra></extra>"
                ))
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Figtree', color='rgba(26,28,46,0.55)', size=12),
                    xaxis=dict(
                        tickmode='linear', tick0=0, dtick=1,
                        gridcolor='rgba(26,28,46,0.07)', zeroline=False,
                        title=dict(text="Nota Final", font=dict(size=11))
                    ),
                    yaxis=dict(
                        gridcolor='rgba(26,28,46,0.07)', zeroline=False,
                        title=dict(text="Frequência", font=dict(size=11))
                    ),
                    margin=dict(l=10,r=10,t=10,b=10),
                    bargap=0.08,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

                # Ranking
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">🥇 Top 3 da Turma</div>', unsafe_allow_html=True)
                medels = ["🥇","🥈","🥉"]
                for idx, row in dados["df_ranking"].head(3).iterrows():
                    st.markdown(f"""
                    <div class="podium-item">
                        <span class="rank-medal">{medels[idx]}</span>
                        <span class="rank-name">{row['Nome']}</span>
                        <span class="rank-score">{row['Nota']:.2f} pts</span>
                    </div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col_dir:
                # Badges fáceis
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">✅ Maior índice de acerto</div>', unsafe_allow_html=True)
                st.markdown('<div class="badge-row">', unsafe_allow_html=True)
                for q, taxa in dados["top_3_faceis"]:
                    st.markdown(f'<span class="badge badge-ok">▲ {q} &nbsp; {taxa*100:.1f}%</span>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)

                # Badges difíceis
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">⚠ Menor índice de acerto</div>', unsafe_allow_html=True)
                st.markdown('<div class="badge-row">', unsafe_allow_html=True)
                for q, taxa in dados["top_3_dificeis"]:
                    st.markdown(f'<span class="badge badge-bad">▼ {q} &nbsp; {taxa*100:.1f}%</span>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)

                # Gráfico de aproveitamento por questão (todos os 16)
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">🎯 Aproveitamento por Questão</div>', unsafe_allow_html=True)
                ia = dados["indices_acerto"]
                q_keys = [f"Q{i}" for i in range(1,17)]
                q_vals = [ia.get(k,0)*100 for k in q_keys]
                colors = ["rgba(52,199,89,0.65)" if v>=50 else "rgba(239,68,68,0.60)" for v in q_vals]
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=q_keys, y=q_vals,
                    marker=dict(color=colors, line=dict(width=0)),
                    hovertemplate="%{x}: %{y:.1f}%<extra></extra>"
                ))
                fig2.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Figtree', color='rgba(26,28,46,0.50)', size=11),
                    xaxis=dict(gridcolor='rgba(26,28,46,0.06)', zeroline=False),
                    yaxis=dict(
                        gridcolor='rgba(26,28,46,0.06)', zeroline=False,
                        range=[0,108],
                        title=dict(text="% acerto", font=dict(size=10))
                    ),
                    margin=dict(l=10,r=10,t=10,b=10),
                    bargap=0.28,
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="glass-card" style="text-align:center; padding:52px 36px;">
        <div style="font-size:2.6rem; margin-bottom:14px;">📂</div>
        <div style="font-size:1.05rem; font-weight:600; color:#1a1c2e; margin-bottom:8px;">
            Nenhuma planilha carregada
        </div>
        <div style="font-size:0.85rem; color:rgba(26,28,46,0.42); line-height:1.65;">
            Faça upload do arquivo <strong>.xlsx</strong> com o gabarito e as respostas dos alunos<br>
            usando o painel lateral para começar.
        </div>
    </div>
    """, unsafe_allow_html=True)

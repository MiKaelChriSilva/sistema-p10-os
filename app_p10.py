import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import streamlit.components.v1 as components
import hashlib
from typing import Dict, List, Optional
import re
from github import Github
import base64
import random

# --- CONSTANTES ---
DB_FILE = 'estoque_os_web.json'
CATEGORIAS = ["Som", "Luz", "Painel de LED", "Sistema de AC", "Cabos", "Estruturas", "Materiais Diversos"]

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="P10 Soluções - Gestão OS",
    page_icon="logo.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CLASSES PRINCIPAIS ---

class DatabaseManager:
    """Gerencia todas as operações de banco de dados usando GitHub"""
    
    @staticmethod
    def _get_github():
        """Conecta ao GitHub usando token dos secrets"""
        try:
            token = st.secrets["GITHUB_TOKEN"]
            return Github(token)
        except:
            return None
    
    @staticmethod
    def carregar_dados() -> Dict:
        """Carrega dados do GitHub - NUNCA perde dados existentes"""
        try:
            g = DatabaseManager._get_github()
            if g is None:
                return DatabaseManager._get_default_data()
            
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            
            try:
                contents = repo.get_contents("estoque_os_web.json")
                dados_json = base64.b64decode(contents.content).decode('utf-8')
                dados_existentes = json.loads(dados_json)
                
                # Garantir que todos os campos necessários existem
                if "usuarios" not in dados_existentes:
                    dados_existentes["usuarios"] = DatabaseManager._get_default_data()["usuarios"]
                if "recuperacao_senha" not in dados_existentes:
                    dados_existentes["recuperacao_senha"] = {}
                if "materiais" not in dados_existentes or not dados_existentes["materiais"]:
                    dados_existentes["materiais"] = DatabaseManager._get_example_materiais()
                if "ordens_servico" not in dados_existentes:
                    dados_existentes["ordens_servico"] = []
                if "contador_os" not in dados_existentes:
                    dados_existentes["contador_os"] = 1
                    
                return dados_existentes
            except:
                # Arquivo não existe, criar padrão
                dados = DatabaseManager._get_default_data()
                DatabaseManager.salvar_dados(dados)
                return dados
        except Exception as e:
            return DatabaseManager._get_default_data()
    
    @staticmethod
    def salvar_dados(data: Dict) -> bool:
        """Salva dados no GitHub preservando tudo"""
        try:
            g = DatabaseManager._get_github()
            if g is None:
                return False
            
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            dados_json = json.dumps(data, indent=4, ensure_ascii=False)
            
            try:
                contents = repo.get_contents("estoque_os_web.json")
                repo.update_file(
                    "estoque_os_web.json",
                    f"Atualização automática - {datetime.now()}",
                    dados_json,
                    contents.sha
                )
            except:
                repo.create_file(
                    "estoque_os_web.json",
                    "Criação inicial do banco de dados",
                    dados_json
                )
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def _get_default_data() -> Dict:
        """Retorna estrutura de dados padrão - NÃO SOBRESCREVE dados existentes"""
        return {
            "usuarios": {
                "admin": DatabaseManager._hash_senha("admin123"),
                "p10operacao": DatabaseManager._hash_senha("dudu1234")
            },
            "recuperacao_senha": {},
            "materiais": DatabaseManager._get_example_materiais(),
            "ordens_servico": [],
            "contador_os": 1,
            "backup_restaurado": False
        }
    
    @staticmethod
    def _get_example_materiais() -> Dict:
        """Retorna materiais de exemplo com ESTOQUE ILIMITADO"""
        return {
            "Som": {"caixa jbl": 999999, "mesa de som yamaha": 999999, "microfone shure": 999999, "cabo xlr": 999999, "amplificador": 999999},
            "Luz": {"refletor led": 999999, "moving head": 999999, "maquina de fumaça": 999999, "dimmer": 999999},
            "Painel de LED": {"painel indoor p3": 999999, "painel outdoor p5": 999999, "fonte de alimentação": 999999, "cabo de dados": 999999},
            "Sistema de AC": {"ar condicionado 12000": 999999, "exaustor": 999999, "duto flexível": 999999},
            "Cabos": {"cabo powercon": 999999, "cabo rj45": 999999, "cabo fibra ótica": 999999, "cabo p10": 999999},
            "Estruturas": {"treliça 1m": 999999, "base para led": 999999, "claw": 999999, "spigot": 999999},
            "Materiais Diversos": {"fita adesiva": 999999, "enforca gato": 999999, "conector": 999999, "luva de proteção": 999999}
        }
    
    @staticmethod
    def _hash_senha(senha: str) -> str:
        return hashlib.sha256(senha.encode()).hexdigest()
    
    @staticmethod
    def restaurar_backup() -> bool:
        return DatabaseManager.carregar_dados() is not None


class AuthSystem:
    """Sistema de autenticação e gerenciamento de usuários"""
    
    @staticmethod
    def verificar_login(usuario: str, senha: str, dados: Dict) -> bool:
        if usuario in dados["usuarios"]:
            senha_hash = hashlib.sha256(senha.encode()).hexdigest()
            return dados["usuarios"][usuario] == senha_hash
        return False
    
    @staticmethod
    def gerar_codigo_recuperacao(usuario: str, dados: Dict) -> str:
        """Gera código de recuperação de 6 dígitos"""
        codigo = str(random.randint(100000, 999999))
        
        if "recuperacao_senha" not in dados:
            dados["recuperacao_senha"] = {}
        
        if usuario not in dados["recuperacao_senha"]:
            dados["recuperacao_senha"][usuario] = {"codigo": None, "resposta": None}
        
        dados["recuperacao_senha"][usuario]["codigo"] = codigo
        DatabaseManager.salvar_dados(dados)
        
        return codigo
    
    @staticmethod
    def verificar_codigo(usuario: str, codigo: str, dados: Dict) -> bool:
        if "recuperacao_senha" not in dados:
            return False
        if usuario not in dados["recuperacao_senha"]:
            return False
        return dados["recuperacao_senha"][usuario].get("codigo") == codigo
    
    @staticmethod
    def verificar_resposta_seguranca(usuario: str, resposta: str, dados: Dict) -> bool:
        if "recuperacao_senha" not in dados:
            return False
        if usuario not in dados["recuperacao_senha"]:
            return False
        resposta_correta = dados["recuperacao_senha"][usuario].get("resposta")
        return resposta_correta is not None and resposta_correta.lower() == resposta.lower()
    
    @staticmethod
    def definir_resposta_seguranca(usuario: str, resposta: str, dados: Dict) -> None:
        if "recuperacao_senha" not in dados:
            dados["recuperacao_senha"] = {}
        if usuario not in dados["recuperacao_senha"]:
            dados["recuperacao_senha"][usuario] = {}
        dados["recuperacao_senha"][usuario]["resposta"] = resposta
        DatabaseManager.salvar_dados(dados)
    
    @staticmethod
    def tem_resposta_seguranca(usuario: str, dados: Dict) -> bool:
        if "recuperacao_senha" not in dados:
            return False
        if usuario not in dados["recuperacao_senha"]:
            return False
        return dados["recuperacao_senha"][usuario].get("resposta") is not None
    
    @staticmethod
    def redefinir_senha(usuario: str, nova_senha: str, dados: Dict) -> tuple[bool, str]:
        if len(nova_senha) < 6:
            return False, "Nova senha deve ter pelo menos 6 caracteres"
        
        dados["usuarios"][usuario] = DatabaseManager._hash_senha(nova_senha)
        
        if "recuperacao_senha" in dados and usuario in dados["recuperacao_senha"]:
            dados["recuperacao_senha"][usuario]["codigo"] = None
        
        return True, "Senha redefinida com sucesso!"


class OSManager:
    """Gerencia operações de Ordem de Serviço"""
    
    @staticmethod
    def gerar_os(itens: List[Dict], destino: str, responsavel: str, data_retorno: str, dados: Dict) -> Optional[Dict]:
        """Gera nova Ordem de Serviço com múltiplos itens"""
        
        for item in itens:
            categoria = item["categoria"]
            material = item["material"]
            quantidade = item["quantidade"]
            
            if categoria not in dados["materiais"]:
                return None
            if material not in dados["materiais"][categoria]:
                return None
            if quantidade > dados["materiais"][categoria][material]:
                return None
        
        nova_os = {
            "id": dados["contador_os"],
            "itens": itens,
            "destino": destino.upper(),
            "responsavel": responsavel.upper(),
            "data_retorno": data_retorno,
            "status": "Pendente",
            "data_emissao": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        
        for item in itens:
            categoria = item["categoria"]
            material = item["material"]
            quantidade = item["quantidade"]
            
            dados["materiais"][categoria][material] -= quantidade
            
            if dados["materiais"][categoria][material] == 0:
                del dados["materiais"][categoria][material]
                if not dados["materiais"][categoria]:
                    del dados["materiais"][categoria]
        
        dados["ordens_servico"].append(nova_os)
        dados["contador_os"] += 1
        
        return nova_os
    
    @staticmethod
    def dar_baixa(id_os: int, dados: Dict) -> tuple[bool, str]:
        """Registra retorno de material"""
        for os_item in dados["ordens_servico"]:
            if os_item["id"] == id_os and os_item["status"] == "Pendente":
                
                for item in os_item["itens"]:
                    categoria = item["categoria"]
                    material = item["material"]
                    quantidade = item["quantidade"]
                    
                    if categoria not in dados["materiais"]:
                        dados["materiais"][categoria] = {}
                    
                    dados["materiais"][categoria][material] = \
                        dados["materiais"][categoria].get(material, 0) + quantidade
                
                os_item["status"] = "Finalizada"
                os_item["data_baixa"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                return True, f"Baixa da OS #{id_os} realizada com sucesso!"
        
        return False, "OS não encontrada ou já finalizada"


# --- CSS PERSONALIZADO ---
def aplicar_css():
    p10_styles = """
    <style>
    @media only screen and (max-width: 768px) {
        .stApp { padding: 10px; }
        .stColumns { flex-direction: column; }
        div[data-testid="column"] { width: 100% !important; margin-bottom: 10px; }
        .stButton button { width: 100%; }
        h1 { font-size: 24px !important; }
        [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    }
    
    @media print {
        header, .stSidebar, .stButton, .stInfo, .stSuccess, 
        .stWarning, .stError, [data-testid="stHeader"] { display: none !important; }
        .main .block-container { padding: 0 !important; margin: 0 !important; }
    }
    
    .stMarkdown, .stMarkdown p { color: #555555 !important; }
    [data-testid="stMetricValue"] { color: #2c3e50 !important; font-size: 2rem !important; font-weight: 600 !important; }
    [data-testid="stMetricLabel"] { color: #7f8c8d !important; font-size: 0.9rem !important; }
    
    h1, h2, h3 {
        background: linear-gradient(90deg, #FF4500 0%, #32CD32 50%, #00BFFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #dee2e6; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h2 {
        color: #495057 !important;
        -webkit-text-fill-color: #495057 !important;
    }
    
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #FF4500 0%, #32CD32 50%, #00BFFF 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
    </style>
    """
    st.markdown(p10_styles, unsafe_allow_html=True)


# --- FUNÇÕES DE UI ---
def exibir_recibo(os_info: Dict):
    """Exibe recibo simplificado com marca d'água"""
    
    # Calcular tamanho da fonte baseado no número de itens
    num_itens = len(os_info["itens"])
    if num_itens <= 5:
        fonte_tabela = "11px"
        fonte_header = "24px"
        fonte_subheader = "18px"
    elif num_itens <= 10:
        fonte_tabela = "9px"
        fonte_header = "20px"
        fonte_subheader = "16px"
    elif num_itens <= 15:
        fonte_tabela = "8px"
        fonte_header = "18px"
        fonte_subheader = "14px"
    else:
        fonte_tabela = "7px"
        fonte_header = "16px"
        fonte_subheader = "12px"
    
    html_recibo = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>P10 Soluções - Ordem de Serviço #{os_info['id']:04d}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            @media print {{
                body {{
                    margin: 0;
                    padding: 0;
                    background: white;
                    position: relative;
                }}
                .recibo-paper {{
                    width: 210mm;
                    min-height: 297mm;
                    margin: 0;
                    padding: 8mm;
                    box-shadow: none;
                    position: relative;
                }}
                @page {{
                    size: A4;
                    margin: 0;
                }}
                .no-print {{
                    display: none;
                }}
                /* Marca d'água na impressão */
                .watermark {{
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    opacity: 0.1;
                    z-index: 999;
                    pointer-events: none;
                }}
                .watermark img {{
                    width: 300px;
                    height: auto;
                }}
            }}
            
            /* Marca d'água na tela (visível apenas na impressão) */
            .watermark {{
                display: none;
            }}
            
            @media print {{
                .watermark {{
                    display: block;
                }}
            }}
            
            body {{
                background-color: #e0e0e0;
                padding: 20px;
                font-family: 'Arial', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                position: relative;
            }}
            
            .recibo-paper {{
                width: 210mm;
                background: white;
                padding: 8mm;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
                font-family: 'Arial', sans-serif;
                position: relative;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 10px;
            }}
            
            .header h1 {{
                font-size: {fonte_header};
                font-weight: bold;
                letter-spacing: 2px;
            }}
            
            .header h2 {{
                font-size: {fonte_subheader};
                font-weight: bold;
                margin-top: 3px;
            }}
            
            .os-number {{
                text-align: right;
                font-size: 10px;
                margin: 8px 0;
                font-weight: bold;
            }}
            
            .event-info {{
                margin: 10px 0;
                font-size: 10px;
                border: 1px solid #333;
                padding: 8px;
                background: #f9f9f9;
            }}
            
            .event-info p {{
                margin: 2px 0;
            }}
            
            .equipment-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
                font-size: {fonte_tabela};
            }}
            
            .equipment-table th {{
                border: 1px solid #000;
                padding: 6px;
                background: #f0f0f0;
                text-align: center;
                font-weight: bold;
            }}
            
            .equipment-table td {{
                border: 1px solid #000;
                padding: 4px;
                vertical-align: top;
            }}
            
            .signatures {{
                display: flex;
                justify-content: space-between;
                margin: 25px 0 15px 0;
            }}
            
            .signature-box {{
                width: 45%;
                text-align: center;
            }}
            
            .signature-line {{
                border-top: 1px solid #000;
                margin-top: 30px;
                padding-top: 5px;
                font-size: 9px;
            }}
            
            .footer {{
                text-align: center;
                font-size: 8px;
                color: #666;
                margin-top: 15px;
            }}
            
            .print-button {{
                text-align: center;
                margin-bottom: 15px;
            }}
            
            .print-button button {{
                background: linear-gradient(90deg, #FF4500 0%, #32CD32 50%, #00BFFF 100%);
                color: white;
                border: none;
                padding: 8px 25px;
                font-size: 12px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="watermark">
            <svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
                <text x="50%" y="50%" text-anchor="middle" font-size="40" fill="gray" opacity="0.3" transform="rotate(-45, 150, 150)">P10 SOLUÇÕES</text>
            </svg>
        </div>
        
        <div class="print-button no-print">
            <button onclick="window.print()">🖨️ Imprimir OS</button>
        </div>
        
        <div class="recibo-paper">
            <div class="header">
                <h1>P10 SOLUÇÕES EM EVENTOS</h1>
                <h2>ORDEM DE SERVIÇO (OS)</h2>
            </div>
            
            <div class="os-number">
                <strong>Nº OS:</strong> {os_info['id']:04d} &nbsp;&nbsp; <strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y')}
            </div>
            
            <div class="event-info">
                <p><strong>DADOS DO EVENTO</strong></p>
                <p><strong>Evento/Cliente:</strong> {os_info['destino']}</p>
                <p><strong>Responsável Técnico:</strong> {os_info['responsavel']}</p>
                <p><strong>Previsão de Retorno:</strong> {os_info['data_retorno']}</p>
            </div>
            
            <table class="equipment-table">
                <thead>
                    <tr>
                        <th style="width: 8%;">ITEM</th>
                        <th style="width: 30%;">CATEGORIA</th>
                        <th style="width: 47%;">DESCRIÇÃO DO EQUIPAMENTO</th>
                        <th style="width: 15%;">QTD</th>
                    </tr>
                </thead>
                <tbody>
        """
    
    # Adicionar cada item da OS
    for i, item in enumerate(os_info["itens"], 1):
        html_recibo += f"""
                    <tr>
                        <td style="text-align: center;">{i}</td>
                        <td>{item['categoria'].upper()}</td>
                        <td>{item['material'].upper()}</td>
                        <td style="text-align: center;">{item['quantidade']}</td>
                    </tr>
        """
    
    html_recibo += f"""
                </tbody>
            </table>
            
            <div class="signatures">
                <div class="signature-box">
                    <div class="signature-line">
                        ___________________________________<br>
                        Assinatura do Responsável
                    </div>
                    <div style="font-size: 9px; margin-top: 5px;">
                        <strong>Nome:</strong> {os_info['responsavel']}
                    </div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">
                        ___________________________________<br>
                        Assinatura P10 Soluções
                    </div>
                    <div style="font-size: 9px; margin-top: 5px;">
                        <strong>Autorizado por:</strong> Administração
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>P10 Soluções em Eventos - Porto Alegre/RS</p>
                <p>Documento gerado eletronicamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(html_recibo, height=700, scrolling=True)


def tela_login():
    """Interface de login com recuperação de senha"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='text-align: center; padding: 20px; border-radius: 15px; 
                 background: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>
                <h1 style='background: linear-gradient(90deg, #FF4500 0%, #32CD32 50%, #00BFFF 100%); 
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                    P10 SOLUÇÕES
                </h1>
                <p style='color: #666;'>Gestão Profissional de OS</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        tabs = st.tabs(["🔒 Entrar", "🆘 Recuperar Senha", "🔐 Configurar Segurança"])
        
        with tabs[0]:
            with st.form("login_form"):
                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Acessar Painel", use_container_width=True):
                    if AuthSystem.verificar_login(usuario, senha, st.session_state.dados):
                        st.session_state.logado = True
                        st.session_state.usuario_atual = usuario
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos")
        
        with tabs[1]:
            st.info("🆘 Recuperação de Senha")
            
            with st.form("recuperar_senha_form"):
                usuario_rec = st.text_input("Usuário")
                
                if st.form_submit_button("Enviar Código de Recuperação", use_container_width=True):
                    if usuario_rec in st.session_state.dados["usuarios"]:
                        codigo = AuthSystem.gerar_codigo_recuperacao(usuario_rec, st.session_state.dados)
                        st.success(f"✅ Código de recuperação gerado: **{codigo}**")
                        st.info("💡 Anote este código e use no próximo passo!")
                    else:
                        st.error("❌ Usuário não encontrado")
            
            with st.form("redefinir_senha_form"):
                st.markdown("---")
                usuario_red = st.text_input("Usuário")
                codigo_red = st.text_input("Código de Recuperação")
                nova_senha_red = st.text_input("Nova Senha", type="password")
                confirmar_senha_red = st.text_input("Confirmar Nova Senha", type="password")
                
                if st.form_submit_button("Redefinir Senha", use_container_width=True):
                    if nova_senha_red != confirmar_senha_red:
                        st.error("❌ As senhas não coincidem")
                    elif AuthSystem.verificar_codigo(usuario_red, codigo_red, st.session_state.dados):
                        sucesso, mensagem = AuthSystem.redefinir_senha(usuario_red, nova_senha_red, st.session_state.dados)
                        if sucesso:
                            DatabaseManager.salvar_dados(st.session_state.dados)
                            st.success(f"✅ {mensagem}")
                        else:
                            st.error(f"❌ {mensagem}")
                    else:
                        st.error("❌ Código inválido")
        
        with tabs[2]:
            st.info("🔐 Configure sua resposta de segurança (opcional - ajuda na recuperação de senha)")
            
            with st.form("configurar_seguranca_form"):
                usuario_conf = st.text_input("Usuário")
                senha_conf = st.text_input("Senha para confirmar identidade", type="password")
                resposta_conf = st.text_input("Resposta de segurança (Ex: 01/01/1990 ou nome do responsável)", type="password")
                confirmar_resposta = st.text_input("Confirmar resposta de segurança", type="password")
                
                if st.form_submit_button("Configurar Resposta de Segurança", use_container_width=True):
                    if not AuthSystem.verificar_login(usuario_conf, senha_conf, st.session_state.dados):
                        st.error("❌ Usuário ou senha incorretos")
                    elif resposta_conf != confirmar_resposta:
                        st.error("❌ As respostas de segurança não coincidem")
                    elif len(resposta_conf) < 3:
                        st.error("❌ Resposta de segurança deve ter pelo menos 3 caracteres")
                    else:
                        AuthSystem.definir_resposta_seguranca(usuario_conf, resposta_conf, st.session_state.dados)
                        DatabaseManager.salvar_dados(st.session_state.dados)
                        st.success("✅ Resposta de segurança configurada com sucesso!")


def painel_geral(dados: Dict):
    """Painel principal com resumos"""
    st.markdown("""
        <h1 style='text-align: center; background: linear-gradient(90deg, #FF4500 0%, 
            #32CD32 50%, #00BFFF 100%); -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent;'>
            Resumo do Depósito P10
        </h1>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_itens = sum(sum(itens.values()) for itens in dados["materiais"].values())
        st.metric("📦 Total em Estoque", f"{total_itens:,}")
    
    with col2:
        os_ativas = len([os for os in dados["ordens_servico"] if os["status"] == "Pendente"])
        st.metric("🚚 OS em Andamento", os_ativas)
    
    with col3:
        os_finalizadas = len([os for os in dados["ordens_servico"] if os["status"] == "Finalizada"])
        st.metric("✅ OS Finalizadas", os_finalizadas)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Estoque por Categoria")
        if dados["materiais"]:
            estoque_categorias = {cat: sum(itens.values()) for cat, itens in dados["materiais"].items()}
            df_estoque = pd.DataFrame(estoque_categorias.items(), columns=["Categoria", "Quantidade"])
            st.bar_chart(df_estoque.set_index("Categoria"))
        else:
            st.info("Nenhum item em estoque")
    
    with col2:
        st.subheader("📈 Últimas OS")
        if dados["ordens_servico"]:
            ultimas_os = dados["ordens_servico"][-5:][::-1]
            df_os = pd.DataFrame(ultimas_os)
            st.dataframe(df_os[["id", "destino", "status", "data_emissao"]], 
                        use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma OS registrada")
    
    st.subheader("📋 Detalhamento do Estoque")
    if dados["materiais"]:
        lista_itens = []
        for cat, itens in dados["materiais"].items():
            for nome, qtd in itens.items():
                lista_itens.append({"Categoria": cat, "Item": nome.upper(), "Quantidade": f"{qtd:,}"})
        df_detalhado = pd.DataFrame(lista_itens)
        st.dataframe(df_detalhado, use_container_width=True, hide_index=True)
    else:
        st.info("Depósito vazio")
    
    st.subheader("⚠️ Materiais em Eventos")
    pendentes = [os for os in dados["ordens_servico"] if os["status"] == "Pendente"]
    if pendentes:
        dados_pendentes = []
        for os_item in pendentes:
            for item in os_item["itens"]:
                dados_pendentes.append({
                    "OS": os_item["id"],
                    "Evento": os_item["destino"],
                    "Material": item["material"].upper(),
                    "Quantidade": item["quantidade"],
                    "Retorno": os_item["data_retorno"]
                })
        df_pendentes = pd.DataFrame(dados_pendentes)
        st.dataframe(df_pendentes, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Todos os materiais estão em estoque!")


def tela_estoque(dados: Dict):
    """Gerenciamento de estoque"""
    st.header("📦 Gerenciamento de Estoque")
    
    busca = st.text_input("🔍 Buscar equipamento", placeholder="Digite o nome do equipamento...")
    
    with st.form("estoque_form"):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        categoria = col1.selectbox("Categoria", CATEGORIAS)
        nome = col2.text_input("Equipamento").strip()
        quantidade = col3.number_input("Quantidade", min_value=1, step=1, value=1)
        
        if st.form_submit_button("➕ Adicionar ao Estoque", use_container_width=True):
            if nome:
                nome_lower = nome.lower()
                if categoria not in dados["materiais"]:
                    dados["materiais"][categoria] = {}
                
                if nome_lower in dados["materiais"][categoria]:
                    dados["materiais"][categoria][nome_lower] += quantidade
                else:
                    dados["materiais"][categoria][nome_lower] = quantidade
                
                if DatabaseManager.salvar_dados(dados):
                    st.success(f"✅ {quantidade}x {nome.upper()} adicionado à categoria {categoria}")
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar")
            else:
                st.warning("⚠️ Digite o nome do equipamento")
    
    st.subheader("📋 Estoque Atual")
    
    if dados["materiais"]:
        for categoria, itens in dados["materiais"].items():
            itens_filtrados = {item: qtd for item, qtd in itens.items() 
                              if not busca or busca.lower() in item}
            
            if itens_filtrados:
                with st.expander(f"📁 {categoria} ({sum(itens_filtrados.values()):,} itens)"):
                    for item, qtd in itens_filtrados.items():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.write(f"**{item.upper()}**")
                        col2.write(f"Quantidade: {qtd:,}")
                        
                        if col3.button("🗑️", key=f"del_{categoria}_{item}"):
                            if st.session_state.get(f"confirm_del_{categoria}_{item}", False):
                                del dados["materiais"][categoria][item]
                                if not dados["materiais"][categoria]:
                                    del dados["materiais"][categoria]
                                DatabaseManager.salvar_dados(dados)
                                st.success(f"✅ {item.upper()} removido do estoque")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_del_{categoria}_{item}"] = True
                                st.warning(f"⚠️ Clique novamente para confirmar exclusão de {item.upper()}")
    else:
        st.info("📭 Nenhum item cadastrado no estoque")
        st.markdown("---")
        st.subheader("💡 Como começar?")
        st.markdown("""
        1. Selecione uma **categoria** (Som, Luz, Painel de LED, etc.)
        2. Digite o nome do **equipamento** (ex: Caixa JBL, Cabo XLR, etc.)
        3. Informe a **quantidade**
        4. Clique em **Adicionar ao Estoque**
        """)


def tela_nova_os(dados: Dict):
    """Gerar nova Ordem de Serviço com múltiplos itens e observação"""
    st.header("📝 Gerar Nova Ordem de Serviço")
    
    with st.expander("🔍 Ver estoque completo"):
        for cat, itens in dados["materiais"].items():
            if itens:
                st.write(f"**{cat}:**")
                for item, qtd in itens.items():
                    st.write(f"  - {item}: {qtd:,} unidades")
    
    if not dados["materiais"] or all(len(itens) == 0 for itens in dados["materiais"].values()):
        st.error("⚠️ NENHUM EQUIPAMENTO CADASTRADO!")
        if st.button("🔄 Carregar Exemplos"):
            dados["materiais"] = DatabaseManager._get_example_materiais()
            DatabaseManager.salvar_dados(dados)
            st.rerun()
        return
    
    if 'lista_itens_os' not in st.session_state:
        st.session_state.lista_itens_os = []
    
    st.subheader("➕ Adicionar Itens à OS")
    
    col1, col2 = st.columns(2)
    
    with col1:
        categorias_com_estoque = [cat for cat, itens in dados["materiais"].items() if itens]
        categoria = st.selectbox("Categoria", categorias_com_estoque, key="cat_selector")
        
        if categoria in dados["materiais"]:
            itens_disponiveis = list(dados["materiais"][categoria].keys())
            if itens_disponiveis:
                material = st.selectbox("Equipamento", itens_disponiveis, key="mat_selector")
                if material:
                    qtd_max = dados["materiais"][categoria][material]
                    quantidade = st.number_input("Quantidade", min_value=1, max_value=qtd_max, value=1, key="qtd_selector")
    
    with col2:
        observacao = st.text_area("Observação (opcional)", placeholder="Digite uma observação para este item...", key="obs_selector", height=100)
        
        if st.button("➕ Adicionar Item à Lista", use_container_width=True):
            if material and quantidade > 0:
                st.session_state.lista_itens_os.append({
                    "categoria": categoria,
                    "material": material,
                    "quantidade": quantidade,
                    "observacao": observacao if observacao else ""
                })
                st.success(f"✅ Item adicionado: {material.upper()} - {quantidade}x")
                st.rerun()
    
    if st.session_state.lista_itens_os:
        st.subheader("📋 Itens da OS")
        df_itens = pd.DataFrame(st.session_state.lista_itens_os)
        df_itens.columns = ["Categoria", "Material", "Quantidade", "Observação"]
        st.dataframe(df_itens, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Limpar Lista", use_container_width=True):
            st.session_state.lista_itens_os = []
            st.rerun()
    
    st.subheader("📋 Dados da OS")
    
    with st.form("dados_os_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            data_retorno = st.date_input("Previsão de Retorno")
        
        with col2:
            evento = st.text_input("Evento / Cliente")
            responsavel = st.text_input("Técnico Responsável")
        
        botao_disabled = len(st.session_state.lista_itens_os) == 0
        
        submitted = st.form_submit_button("✅ Gerar OS", use_container_width=True, disabled=botao_disabled)
        
        if submitted:
            if not all([evento, responsavel]):
                st.error("❌ Preencha todos os campos")
            else:
                data_br = data_retorno.strftime("%d/%m/%Y")
                nova_os = OSManager.gerar_os(
                    st.session_state.lista_itens_os.copy(), evento, responsavel, data_br, dados
                )
                if nova_os and DatabaseManager.salvar_dados(dados):
                    st.success(f"✅ OS #{nova_os['id']} gerada com sucesso!")
                    st.session_state.ultima_os = nova_os
                    st.session_state.lista_itens_os = []
                    st.rerun()
                else:
                    st.error("❌ Erro ao gerar OS - Estoque insuficiente")
    
    if 'ultima_os' in st.session_state:
        st.markdown("---")
        st.subheader("📄 Visualização da OS")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🖨️ Imprimir Recibo"):
                exibir_recibo(st.session_state.ultima_os)
        with col2:
            if st.button("🗑️ Limpar Visualização"):
                del st.session_state.ultima_os
                st.rerun()


def tela_baixa(dados: Dict):
    """Dar baixa em OS"""
    st.header("🔄 Baixa de Ordem de Serviço")
    
    os_ativas = [os for os in dados["ordens_servico"] if os["status"] == "Pendente"]
    
    if not os_ativas:
        st.success("✅ Não há OS pendentes de baixa!")
        return
    
    st.subheader("Selecionar OS para baixa")
    
    opcoes_os = {}
    for os_item in os_ativas:
        itens_resumo = ", ".join([f"{item['material']}({item['quantidade']})" for item in os_item["itens"]])
        opcoes_os[f"OS #{os_item['id']} - {os_item['destino']} - {itens_resumo}"] = os_item['id']
    
    os_selecionada = st.selectbox("Ordem de Serviço", list(opcoes_os.keys()))
    id_os = opcoes_os[os_selecionada]
    
    os_info = next(os for os in os_ativas if os['id'] == id_os)
    
    with st.expander("📋 Detalhes da OS"):
        st.write(f"**Evento:** {os_info['destino']}")
        st.write(f"**Responsável:** {os_info['responsavel']}")
        st.write(f"**Retorno previsto:** {os_info['data_retorno']}")
        st.write("**Itens retirados:**")
        for item in os_info["itens"]:
            obs = f" - Obs: {item['observacao']}" if item.get("observacao") else ""
            st.write(f"  - {item['categoria']} / {item['material'].upper()}: {item['quantidade']}x{obs}")
    
    if st.button("✅ Confirmar Retorno do Material", type="primary", use_container_width=True):
        sucesso, mensagem = OSManager.dar_baixa(id_os, dados)
        
        if sucesso and DatabaseManager.salvar_dados(dados):
            st.success(f"✅ {mensagem}")
            st.balloons()
            st.rerun()
        else:
            st.error(f"❌ {mensagem}")


def tela_historico_os(dados: Dict):
    """Tela de histórico de OS"""
    st.header("📋 Histórico de Ordens de Serviço")
    
    os_abertas = [os for os in dados["ordens_servico"] if os["status"] == "Pendente"]
    os_fechadas = [os for os in dados["ordens_servico"] if os["status"] == "Finalizada"]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Total de OS", len(dados["ordens_servico"]))
    with col2:
        st.metric("🟢 OS Abertas", len(os_abertas))
    with col3:
        st.metric("🔴 OS Fechadas", len(os_fechadas))
    
    tab1, tab2 = st.tabs(["📌 OS ABERTAS", "✅ OS FINALIZADAS"])
    
    with tab1:
        if os_abertas:
            for i, os_item in enumerate(os_abertas):
                # Verificar se existe a chave "itens" (formato novo) ou é formato antigo
                if "itens" in os_item:
                    itens_resumo = ", ".join([f"{item['material']}({item['quantidade']})" for item in os_item["itens"]])
                else:
                    # Formato antigo (um único item)
                    itens_resumo = f"{os_item.get('material', 'N/A')}({os_item.get('quantidade', 0)})"
                
                with st.expander(f"OS #{os_item['id']:04d} - {os_item['destino']} - {itens_resumo}"):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**Responsável:** {os_item['responsavel']}")
                        st.write(f"**Retorno:** {os_item['data_retorno']}")
                    with col_info2:
                        st.write(f"**Emissão:** {os_item['data_emissao']}")
                    
                    st.write("**Itens:**")
                    if "itens" in os_item:
                        for item in os_item["itens"]:
                            obs = f" - Obs: {item['observacao']}" if item.get("observacao") else ""
                            st.write(f"  - {item['categoria']} / {item['material'].upper()}: {item['quantidade']}x{obs}")
                    else:
                        # Formato antigo
                        st.write(f"  - {os_item.get('categoria', 'N/A')} / {os_item.get('material', 'N/A').upper()}: {os_item.get('quantidade', 0)}x")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("🖨️ Imprimir", key=f"print_{i}_{os_item['id']}"):
                            # Converter formato antigo para novo se necessário
                            if "itens" not in os_item:
                                os_item["itens"] = [{
                                    "categoria": os_item["categoria"],
                                    "material": os_item["material"],
                                    "quantidade": os_item["quantidade"],
                                    "observacao": os_item.get("observacao", "")
                                }]
                            exibir_recibo(os_item)
                    with c2:
                        if st.button("✅ Dar Baixa", key=f"baixa_{i}_{os_item['id']}"):
                            sucesso, msg = OSManager.dar_baixa(os_item['id'], dados)
                            if sucesso and DatabaseManager.salvar_dados(dados):
                                st.success(msg)
                                st.rerun()
                    with c3:
                        if st.button("🗑️ Cancelar", key=f"cancel_{i}_{os_item['id']}"):
                            # Devolver todos os itens ao estoque
                            if "itens" in os_item:
                                for item in os_item["itens"]:
                                    cat = item["categoria"]
                                    mat = item["material"]
                                    qtd = item["quantidade"]
                                    if cat not in dados["materiais"]:
                                        dados["materiais"][cat] = {}
                                    dados["materiais"][cat][mat] = dados["materiais"][cat].get(mat, 0) + qtd
                            else:
                                # Formato antigo
                                cat = os_item["categoria"]
                                mat = os_item["material"]
                                qtd = os_item["quantidade"]
                                if cat not in dados["materiais"]:
                                    dados["materiais"][cat] = {}
                                dados["materiais"][cat][mat] = dados["materiais"][cat].get(mat, 0) + qtd
                            
                            dados["ordens_servico"].remove(os_item)
                            DatabaseManager.salvar_dados(dados)
                            st.success(f"OS #{os_item['id']} cancelada!")
                            st.rerun()
        else:
            st.info("Nenhuma OS aberta")
    
    with tab2:
        if os_fechadas:
            for i, os_item in enumerate(os_fechadas):
                if "itens" in os_item:
                    itens_resumo = ", ".join([f"{item['material']}({item['quantidade']})" for item in os_item["itens"]])
                else:
                    itens_resumo = f"{os_item.get('material', 'N/A')}({os_item.get('quantidade', 0)})"
                
                with st.expander(f"OS #{os_item['id']:04d} - {os_item['destino']} - {itens_resumo}"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        st.write(f"**Responsável:** {os_item['responsavel']}")
                    with col_f2:
                        st.write(f"**Finalizada em:** {os_item.get('data_baixa', 'N/A')}")
                    
                    if st.button("🖨️ Reimprimir", key=f"reprint_{i}_{os_item['id']}", use_container_width=True):
                        if "itens" not in os_item:
                            os_item["itens"] = [{
                                "categoria": os_item["categoria"],
                                "material": os_item["material"],
                                "quantidade": os_item["quantidade"],
                                "observacao": os_item.get("observacao", "")
                            }]
                        exibir_recibo(os_item)
        else:
            st.info("Nenhuma OS finalizada")


def barra_lateral():
    """Configuração da barra lateral"""
    st.sidebar.markdown(f"""
        <div style='text-align: center; padding: 10px;'>
            <h2 style='color: #FF4500;'>👤 {st.session_state.usuario_atual}</h2>
            <p style='font-size: 0.9em; color: #666;'>Operador</p>
        </div>
        <hr>
    """, unsafe_allow_html=True)
    
    menu = st.sidebar.radio(
        "📌 Navegação",
        ["📋 Painel Geral", "📦 Estoque", "📝 Gerar Nova OS", "🔄 Baixa/Retorno", "📜 Histórico de OS"]
    )
    
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("📊 Resumo Rápido")
    os_abertas = len([os for os in st.session_state.dados["ordens_servico"] if os["status"] == "Pendente"])
    st.sidebar.info(f"🟢 OS Abertas: {os_abertas}")
    
    with st.sidebar.expander("🔧 Manutenção"):
        if st.button("💾 Criar Backup Manual"):
            if DatabaseManager.salvar_dados(st.session_state.dados):
                st.success("Backup criado!")
        
        if st.button("🔄 Restaurar Backup"):
            if DatabaseManager.restaurar_backup():
                st.session_state.dados = DatabaseManager.carregar_dados()
                st.success("Backup restaurado!")
                st.rerun()
            else:
                st.error("Nenhum backup encontrado")
        
        if st.button("📊 Exportar Dados (CSV)"):
            df_os = pd.DataFrame(st.session_state.dados["ordens_servico"])
            csv = df_os.to_csv(index=False)
            st.download_button("Download CSV", csv, "os_export.csv", "text/csv")
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.logado = False
        st.rerun()
    
    return menu


def main():
    """Função principal"""
    aplicar_css()
    
    if 'dados' not in st.session_state:
        st.session_state.dados = DatabaseManager.carregar_dados()
    if 'logado' not in st.session_state:
        st.session_state.logado = False
    
    if not st.session_state.logado:
        tela_login()
        return
    
    menu = barra_lateral()
    
    if menu == "📋 Painel Geral":
        painel_geral(st.session_state.dados)
    elif menu == "📦 Estoque":
        tela_estoque(st.session_state.dados)
    elif menu == "📝 Gerar Nova OS":
        tela_nova_os(st.session_state.dados)
    elif menu == "🔄 Baixa/Retorno":
        tela_baixa(st.session_state.dados)
    elif menu == "📜 Histórico de OS":
        tela_historico_os(st.session_state.dados)


if __name__ == "__main__":
    main()
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

# --- CONSTANTES ---
DB_FILE = 'estoque_os_web.json'
CATEGORIAS = ["Som", "Luz", "Painel de LED", "Sistema de AC", "Cabos", "Estruturas", "Materiais Diversos"]

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="P10 Soluções - Gestão OS",
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
        """Carrega dados do GitHub"""
        try:
            g = DatabaseManager._get_github()
            if g is None:
                return DatabaseManager._get_default_data()
            
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            
            try:
                contents = repo.get_contents("estoque_os_web.json")
                dados_json = base64.b64decode(contents.content).decode('utf-8')
                return json.loads(dados_json)
            except:
                dados = DatabaseManager._get_default_data()
                DatabaseManager.salvar_dados(dados)
                return dados
        except Exception as e:
            return DatabaseManager._get_default_data()
    
    @staticmethod
    def salvar_dados(data: Dict) -> bool:
        """Salva dados no GitHub"""
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
        """Retorna estrutura de dados padrão com exemplos"""
        return {
            "usuarios": {
                "admin": DatabaseManager._hash_senha("admin123")
            },
            "materiais": DatabaseManager._get_example_materiais(),
            "ordens_servico": [],
            "contador_os": 1,
            "backup_restaurado": False
        }
    
    @staticmethod
    def _get_example_materiais() -> Dict:
        """Retorna materiais de exemplo"""
        return {
            "Som": {"caixa jbl": 10, "mesa de som yamaha": 3, "microfone shure": 8, "cabo xlr": 20, "amplificador": 4},
            "Luz": {"refletor led": 15, "moving head": 6, "maquina de fumaça": 3, "dimmer": 5},
            "Painel de LED": {"painel indoor p3": 20, "painel outdoor p5": 10, "fonte de alimentação": 8, "cabo de dados": 15},
            "Sistema de AC": {"ar condicionado 12000": 2, "exaustor": 4, "duto flexível": 50},
            "Cabos": {"cabo powercon": 15, "cabo rj45": 30, "cabo fibra ótica": 5, "cabo p10": 25},
            "Estruturas": {"treliça 1m": 20, "base para led": 8, "claw": 30, "spigot": 15},
            "Materiais Diversos": {"fita adesiva": 10, "enforca gato": 100, "conector": 50, "luva de proteção": 20}
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
    def criar_usuario(usuario: str, senha: str, dados: Dict) -> tuple[bool, str]:
        if not usuario or not senha:
            return False, "Preencha todos os campos"
        
        if len(usuario) < 3:
            return False, "Usuário deve ter pelo menos 3 caracteres"
        
        if len(senha) < 6:
            return False, "Senha deve ter pelo menos 6 caracteres"
        
        if usuario in dados["usuarios"]:
            return False, "Usuário já existe"
        
        dados["usuarios"][usuario] = DatabaseManager._hash_senha(senha)
        return True, f"Usuário '{usuario}' criado com sucesso!"
    
    @staticmethod
    def alterar_senha(usuario: str, senha_antiga: str, senha_nova: str, dados: Dict) -> tuple[bool, str]:
        if not AuthSystem.verificar_login(usuario, senha_antiga, dados):
            return False, "Senha atual incorreta"
        
        if len(senha_nova) < 6:
            return False, "Nova senha deve ter pelo menos 6 caracteres"
        
        dados["usuarios"][usuario] = DatabaseManager._hash_senha(senha_nova)
        return True, "Senha alterada com sucesso!"


class OSManager:
    """Gerencia operações de Ordem de Serviço"""
    
    @staticmethod
    def gerar_os(categoria: str, material: str, quantidade: int, destino: str, 
                  responsavel: str, data_retorno: str, dados: Dict) -> Optional[Dict]:
        if categoria not in dados["materiais"]:
            return None
        
        if material not in dados["materiais"][categoria]:
            return None
        
        estoque_atual = dados["materiais"][categoria][material]
        if quantidade > estoque_atual:
            return None
        
        nova_os = {
            "id": dados["contador_os"],
            "categoria": categoria,
            "material": material,
            "quantidade": quantidade,
            "destino": destino.upper(),
            "responsavel": responsavel.upper(),
            "data_retorno": data_retorno,
            "status": "Pendente",
            "data_emissao": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        
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
        for os_item in dados["ordens_servico"]:
            if os_item["id"] == id_os and os_item["status"] == "Pendente":
                categoria = os_item["categoria"]
                material = os_item["material"]
                
                if categoria not in dados["materiais"]:
                    dados["materiais"][categoria] = {}
                
                dados["materiais"][categoria][material] = \
                    dados["materiais"][categoria].get(material, 0) + os_item["quantidade"]
                
                os_item["status"] = "Finalizada"
                os_item["data_baixa"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                return True, f"Baixa da OS #{id_os} realizada com sucesso!"
        
        return False, "OS não encontrada ou já finalizada"


# --- CSS PERSONALIZADO ---
def aplicar_css():
    """Aplica estilos CSS personalizados"""
    p10_styles = """
    <style>
    @media print {
        header, .stSidebar, .stButton, .stInfo, .stSuccess, 
        .stWarning, .stError, [data-testid="stHeader"] {
            display: none !important;
        }
        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
        }
    }
    
    .stMarkdown, .stMarkdown p, div[data-testid="stMarkdownContainer"] p {
        color: #555555 !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #2c3e50 !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #7f8c8d !important;
        font-size: 0.9rem !important;
    }
    
    h1, h2, h3 {
        background: linear-gradient(90deg, #FF4500 0%, #32CD32 50%, #00BFFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #dee2e6;
    }
    
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h2 {
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
    
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    </style>
    """
    st.markdown(p10_styles, unsafe_allow_html=True)


# --- FUNÇÕES DE UI ---
def exibir_recibo(os_info: Dict):
    """Exibe recibo formatado"""
    html_recibo = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>P10 Soluções - OS #{os_info['id']:04d}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            @media print {{
                body {{ margin: 0; padding: 0; background: white; }}
                .recibo-paper {{ padding: 10mm; box-shadow: none; }}
                @page {{ size: A4; margin: 0; }}
                .no-print {{ display: none; }}
            }}
            body {{
                background: #e0e0e0;
                padding: 20px;
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
            }}
            .recibo-paper {{
                width: 210mm;
                background: white;
                padding: 10mm;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
            }}
            .header {{ text-align: center; margin-bottom: 15px; }}
            .header h1 {{ font-size: 24px; }}
            .header h2 {{ font-size: 18px; }}
            .os-info {{ margin: 15px 0; padding: 10px; border: 1px solid #333; }}
            .equipment-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            .equipment-table th, .equipment-table td {{
                border: 1px solid #000;
                padding: 8px;
                text-align: left;
            }}
            .equipment-table th {{ background: #f0f0f0; }}
            .signatures {{
                display: flex;
                justify-content: space-between;
                margin: 30px 0;
            }}
            .signature-box {{ width: 45%; text-align: center; }}
            .signature-line {{
                border-top: 1px solid #000;
                margin-top: 40px;
                padding-top: 5px;
            }}
            .footer {{
                text-align: center;
                font-size: 10px;
                color: #666;
                margin-top: 20px;
            }}
            .print-button {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .print-button button {{
                background: linear-gradient(90deg, #FF4500 0%, #32CD32 50%, #00BFFF 100%);
                color: white;
                border: none;
                padding: 10px 30px;
                font-size: 14px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="print-button no-print">
            <button onclick="window.print()">🖨️ Imprimir OS</button>
        </div>
        <div class="recibo-paper">
            <div class="header">
                <h1>P10 SOLUÇÕES EM EVENTOS</h1>
                <h2>ORDEM DE SERVIÇO (OS)</h2>
            </div>
            <div class="os-info">
                <p><strong>Nº OS:</strong> {os_info['id']:04d}</p>
                <p><strong>Data de Emissão:</strong> {datetime.now().strftime('%d/%m/%Y')}</p>
                <p><strong>Evento/Cliente:</strong> {os_info['destino']}</p>
                <p><strong>Responsável:</strong> {os_info['responsavel']}</p>
                <p><strong>Previsão de Retorno:</strong> {os_info['data_retorno']}</p>
            </div>
            <table class="equipment-table">
                <thead><tr><th>CATEGORIA</th><th>DESCRIÇÃO</th><th>QTD</th><th>OBS</th></tr></thead>
                <tbody><tr><td style="font-weight:bold">{os_info['categoria'].upper()}</td><td style="font-weight:bold">{os_info['material'].upper()}</td><td style="text-align:center; font-weight:bold">{os_info['quantidade']}</td><td style="text-align:center">-</td></tr>
                </tbody>
            </table>
            <div class="signatures">
                <div class="signature-box"><div class="signature-line">Assinatura do Responsável</div><div><strong>Nome:</strong> {os_info['responsavel']}</div></div>
                <div class="signature-box"><div class="signature-line">Assinatura P10 Soluções</div><div><strong>Autorizado por:</strong> Administração</div></div>
            </div>
            <div class="footer"><p>Documento gerado eletronicamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p></div>
        </div>
    </body>
    </html>
    """
    components.html(html_recibo, height=600, scrolling=True)


def tela_login():
    """Interface de login"""
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
        
        tabs = st.tabs(["🔒 Entrar", "👤 Criar Usuário", "🔑 Alterar Senha"])
        
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
            with st.form("cadastro_form"):
                st.info("📝 Cadastre um novo operador")
                novo_usuario = st.text_input("Nome de Usuário (mínimo 3 caracteres)")
                nova_senha = st.text_input("Senha (mínimo 6 caracteres)", type="password")
                
                if st.form_submit_button("Criar Conta", use_container_width=True):
                    sucesso, mensagem = AuthSystem.criar_usuario(
                        novo_usuario, nova_senha, st.session_state.dados
                    )
                    if sucesso:
                        DatabaseManager.salvar_dados(st.session_state.dados)
                        st.success(f"✅ {mensagem}")
                    else:
                        st.error(f"❌ {mensagem}")
        
        with tabs[2]:
            with st.form("alterar_senha_form"):
                st.info("🔐 Altere sua senha")
                usuario_alt = st.text_input("Usuário")
                senha_atual = st.text_input("Senha Atual", type="password")
                nova_senha1 = st.text_input("Nova Senha", type="password")
                nova_senha2 = st.text_input("Confirmar Nova Senha", type="password")
                
                if st.form_submit_button("Alterar Senha", use_container_width=True):
                    if nova_senha1 != nova_senha2:
                        st.error("❌ As senhas não coincidem")
                    else:
                        sucesso, mensagem = AuthSystem.alterar_senha(
                            usuario_alt, senha_atual, nova_senha1, st.session_state.dados
                        )
                        if sucesso:
                            DatabaseManager.salvar_dados(st.session_state.dados)
                            st.success(f"✅ {mensagem}")
                        else:
                            st.error(f"❌ {mensagem}")


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
        st.metric("📦 Total em Estoque", total_itens)
    
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
                lista_itens.append({"Categoria": cat, "Item": nome.upper(), "Quantidade": qtd})
        df_detalhado = pd.DataFrame(lista_itens)
        st.dataframe(df_detalhado, use_container_width=True, hide_index=True)
    else:
        st.info("Depósito vazio")
    
    st.subheader("⚠️ Materiais em Eventos")
    pendentes = [os for os in dados["ordens_servico"] if os["status"] == "Pendente"]
    if pendentes:
        df_pendentes = pd.DataFrame(pendentes)
        st.dataframe(df_pendentes[["id", "destino", "material", "quantidade", "data_retorno"]], 
                    use_container_width=True, hide_index=True)
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
                with st.expander(f"📁 {categoria} ({sum(itens_filtrados.values())} itens)"):
                    for item, qtd in itens_filtrados.items():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.write(f"**{item.upper()}**")
                        col2.write(f"Quantidade: {qtd}")
                        
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
    """Gerar nova Ordem de Serviço"""
    st.header("📝 Gerar Nova Ordem de Serviço")
    
    with st.expander("🔍 Ver estoque completo"):
        for cat, itens in dados["materiais"].items():
            if itens:
                st.write(f"**{cat}:**")
                for item, qtd in itens.items():
                    st.write(f"  - {item}: {qtd} unidades")
    
    if not dados["materiais"] or all(len(itens) == 0 for itens in dados["materiais"].values()):
        st.error("⚠️ NENHUM EQUIPAMENTO CADASTRADO!")
        if st.button("🔄 Carregar Exemplos"):
            dados["materiais"] = DatabaseManager._get_example_materiais()
            DatabaseManager.salvar_dados(dados)
            st.rerun()
        return
    
    if 'categoria_atual' not in st.session_state:
        categorias_com_estoque = [cat for cat, itens in dados["materiais"].items() if itens]
        st.session_state.categoria_atual = categorias_com_estoque[0] if categorias_com_estoque else None
    if 'equipamento_key' not in st.session_state:
        st.session_state.equipamento_key = 0
    
    categorias_com_estoque = [cat for cat, itens in dados["materiais"].items() if itens]
    
    categoria = st.selectbox(
        "Selecione a Categoria", 
        categorias_com_estoque,
        index=categorias_com_estoque.index(st.session_state.categoria_atual) if st.session_state.categoria_atual in categorias_com_estoque else 0,
        key="categoria_selector"
    )
    
    if categoria != st.session_state.categoria_atual:
        st.session_state.categoria_atual = categoria
        st.session_state.equipamento_key += 1
        st.rerun()
    
    if categoria in dados["materiais"]:
        itens_disponiveis = list(dados["materiais"][categoria].keys())
        
        if itens_disponiveis:
            opcoes_equipamentos = ["(Selecione um equipamento)"] + [item.upper() for item in itens_disponiveis]
            
            equipamento_display = st.selectbox(
                "Selecione o Equipamento",
                opcoes_equipamentos,
                key=f"equipamento_selector_{st.session_state.equipamento_key}",
                index=0
            )
            
            if equipamento_display != "(Selecione um equipamento)":
                material = None
                for item in itens_disponiveis:
                    if item.upper() == equipamento_display:
                        material = item
                        break
                
                if material:
                    qtd_max = dados["materiais"][categoria][material]
                    quantidade = st.number_input(
                        f"Quantidade (Disponível: {qtd_max})",
                        min_value=1,
                        max_value=qtd_max,
                        value=1,
                        key="quantidade_selector"
                    )
                else:
                    material = None
                    quantidade = 0
            else:
                material = None
                quantidade = 0
                st.info("👆 Selecione um equipamento para continuar")
        else:
            st.warning(f"⚠️ Nenhum equipamento na categoria {categoria}")
            material = None
            quantidade = 0
    else:
        material = None
        quantidade = 0
    
    with st.form("dados_os_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            data_retorno = st.date_input("Previsão de Retorno")
        
        with col2:
            evento = st.text_input("Evento / Cliente")
            responsavel = st.text_input("Técnico Responsável")
        
        botao_disabled = material is None
        
        submitted = st.form_submit_button("✅ Gerar OS", use_container_width=True, disabled=botao_disabled)
        
        if submitted:
            if not all([evento, responsavel, material]):
                st.error("❌ Preencha todos os campos")
            elif quantidade <= 0:
                st.error("❌ Quantidade inválida")
            else:
                data_br = data_retorno.strftime("%d/%m/%Y")
                nova_os = OSManager.gerar_os(
                    categoria, material, quantidade, evento, responsavel, data_br, dados
                )
                if nova_os and DatabaseManager.salvar_dados(dados):
                    st.success(f"✅ OS #{nova_os['id']} gerada com sucesso!")
                    st.session_state.ultima_os = nova_os
                    st.session_state.equipamento_key += 1
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
    
    opcoes_os = {f"OS #{os['id']} - {os['destino']} - {os['material']}": os['id'] 
                 for os in os_ativas}
    
    os_selecionada = st.selectbox("Ordem de Serviço", list(opcoes_os.keys()))
    id_os = opcoes_os[os_selecionada]
    
    os_info = next(os for os in os_ativas if os['id'] == id_os)
    
    with st.expander("📋 Detalhes da OS"):
        col1, col2 = st.columns(2)
        col1.write(f"**Material:** {os_info['material'].upper()}")
        col1.write(f"**Quantidade:** {os_info['quantidade']}")
        col2.write(f"**Evento:** {os_info['destino']}")
        col2.write(f"**Responsável:** {os_info['responsavel']}")
        col2.write(f"**Retorno previsto:** {os_info['data_retorno']}")
    
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
                with st.expander(f"OS #{os_item['id']:04d} - {os_item['destino']}"):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**Material:** {os_item['material'].upper()}")
                        st.write(f"**Quantidade:** {os_item['quantidade']}")
                        st.write(f"**Categoria:** {os_item['categoria']}")
                    with col_info2:
                        st.write(f"**Responsável:** {os_item['responsavel']}")
                        st.write(f"**Retorno:** {os_item['data_retorno']}")
                        st.write(f"**Emissão:** {os_item['data_emissao']}")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("🖨️ Imprimir", key=f"print_{i}_{os_item['id']}"):
                            exibir_recibo(os_item)
                    with c2:
                        if st.button("✅ Dar Baixa", key=f"baixa_{i}_{os_item['id']}"):
                            sucesso, msg = OSManager.dar_baixa(os_item['id'], dados)
                            if sucesso and DatabaseManager.salvar_dados(dados):
                                st.success(msg)
                                st.rerun()
                    with c3:
                        if st.button("🗑️ Cancelar", key=f"cancel_{i}_{os_item['id']}"):
                            cat = os_item["categoria"]
                            mat = os_item["material"]
                            if cat not in dados["materiais"]:
                                dados["materiais"][cat] = {}
                            dados["materiais"][cat][mat] = dados["materiais"][cat].get(mat, 0) + os_item["quantidade"]
                            dados["ordens_servico"].remove(os_item)
                            DatabaseManager.salvar_dados(dados)
                            st.success(f"OS #{os_item['id']} cancelada!")
                            st.rerun()
        else:
            st.info("Nenhuma OS aberta")
    
    with tab2:
        if os_fechadas:
            for i, os_item in enumerate(os_fechadas):
                with st.expander(f"OS #{os_item['id']:04d} - {os_item['destino']}"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        st.write(f"**Material:** {os_item['material'].upper()}")
                        st.write(f"**Quantidade:** {os_item['quantidade']}")
                    with col_f2:
                        st.write(f"**Responsável:** {os_item['responsavel']}")
                        st.write(f"**Finalizada em:** {os_item.get('data_baixa', 'N/A')}")
                    
                    if st.button("🖨️ Reimprimir", key=f"reprint_{i}_{os_item['id']}", use_container_width=True):
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
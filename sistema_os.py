import json
import os
from datetime import datetime

# Identidade da Empresa
EMPRESA_NOME = "P10 SOLUÇÕES EM EVENTOS"
DB_FILE = 'estoque_os.json'

def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"materiais": {}, "ordens_servico": [], "contador_os": 1}
    return {"materiais": {}, "ordens_servico": [], "contador_os": 1}

def salvar_dados(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def gerar_recibo_txt(os_info):
    # Gera um nome de arquivo único para cada recibo
    data_arquivo = datetime.now().strftime('%d-%m-%Y_%H-%M')
    nome_arquivo = f"Recibo_OS_{os_info['id']}_{data_arquivo}.txt"
    
    try:
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write("="*60 + "\n")
            f.write(f"{EMPRESA_NOME:^60}\n")
            f.write(f"{'COMPROVANTE DE MOVIMENTAÇÃO DE MATERIAIS':^60}\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"NÚMERO DA OS:  {os_info['id']:04d}\n")
            f.write(f"DATA/HORA:     {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"DESTINO/EVENTO: {os_info['destino'].upper()}\n")
            f.write(f"RESPONSÁVEL:   {os_info['responsavel'].upper()}\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'MATERIAL':<45} {'QUANTIDADE':>12}\n")
            f.write(f"{os_info['material'].upper():<45} {os_info['quantidade']:>12}\n")
            f.write("-" * 60 + "\n")
            f.write(f"PREVISÃO DE RETORNO AO ESTOQUE: {datetime.strptime(os_info['data_retorno'], '%Y-%m-%d').strftime('%d/%m/%Y')}\n\n\n")
            
            f.write(f"{'________________________________________':^60}\n")
            f.write(f"{os_info['responsavel'].upper():^60}\n")
            f.write(f"{'Assinatura do Técnico':^60}\n\n")
            f.write("="*60 + "\n")
            f.write(f"{'Documento gerado pelo Gestor Interno P10':^60}\n")
            
        print(f"\n✔️ RECIBO GERADO COM SUCESSO: {nome_arquivo}")
        # Comando para abrir o arquivo automaticamente no Windows para o cliente imprimir
        os.startfile(nome_arquivo) 
    except Exception as e:
        print(f"❌ Erro ao gerar o recibo para impressão: {e}")

def cadastrar_material(data):
    print(f"\n--- {EMPRESA_NOME} | CADASTRO ---")
    nome = input("Nome do material: ").strip().lower()
    try:
        qtd = int(input(f"Quantidade a ser adicionada: "))
        data["materiais"][nome] = data["materiais"].get(nome, 0) + qtd
        print(f"✔️ {nome.upper()} atualizado no estoque.")
    except: print("❌ Erro: Digite apenas números inteiros.")

def criar_ordem_servico(data):
    print(f"\n--- {EMPRESA_NOME} | NOVA SAÍDA (O.S) ---")
    nome = input("Material para retirada: ").strip().lower()
    if nome not in data["materiais"]:
        print("❌ Material não encontrado no estoque.")
        return
    
    try:
        disponivel = data["materiais"][nome]
        qtd = int(input(f"Quantidade (Disponível: {disponivel}): "))
        if qtd > disponivel:
            print("❌ Erro: Saldo insuficiente!")
            return
            
        destino = input("Nome do Evento ou Empresa de Destino: ").strip()
        responsavel = input("Nome do Técnico Responsável: ").strip()
        data_input = input("Data prevista de retorno (DD/MM/AAAA): ")
        
        # Validação de data
        dt_retorno = datetime.strptime(data_input, "%d/%m/%Y")
        
        # Atualização do saldo
        data["materiais"][nome] -= qtd
        
        nova_os = {
            "id": data["contador_os"],
            "material": nome,
            "quantidade": qtd,
            "destino": destino,
            "responsavel": responsavel,
            "data_retorno": dt_retorno.strftime("%Y-%m-%d"),
            "status": "Pendente"
        }
        
        data["ordens_servico"].append(nova_os)
        data["contador_os"] += 1
        
        # Chama a função de impressão
        gerar_recibo_txt(nova_os)
        print(f"✔️ OS #{nova_os['id']} registrada e pronta para impressão!")
        
    except ValueError:
        print("❌ Erro: Verifique se a data ou quantidade foram digitadas corretamente.")

def baixar_os(data):
    print(f"\n--- {EMPRESA_NOME} | RETORNO DE MATERIAL ---")
    try:
        id_os = int(input("Informe o ID da Ordem de Serviço: "))
        for os_ref in data["ordens_servico"]:
            if os_ref["id"] == id_os and os_ref["status"] == "Pendente":
                if input(f"Confirmar retorno de {os_ref['material']}? (s/n): ").lower() == 's':
                    data["materiais"][os_ref["material"]] += os_ref["quantidade"]
                    os_ref["status"] = "Devolvido"
                    print("✔️ Material retornou ao estoque com sucesso!")
                    return
        print("❌ Ordem de Serviço não encontrada ou já finalizada.")
    except: print("❌ ID inválido.")

def exibir_relatorio(data):
    print("\n" + "="*50)
    print(f"{EMPRESA_NOME:^50}")
    print(f"{'RELATÓRIO DE ESTOQUE E PENDÊNCIAS':^50}")
    print("="*50)
    
    print("\n[ MATERIAIS NO DEPÓSITO ]")
    if not data["materiais"]: print("Vazio.")
    else:
        for mat, qtd in data["materiais"].items():
            print(f" {mat.upper():.<40} {qtd}")
            
    print("\n[ MATERIAIS EM CAMPO / EVENTOS ]")
    tem_pendente = False
    for os_ref in data["ordens_servico"]:
        if os_ref["status"] == "Pendente":
            tem_pendente = True
            prazo = datetime.strptime(os_ref["data_retorno"], "%Y-%m-%d")
            print(f"ID:{os_ref['id']} | {os_ref['destino']} | {os_ref['material']} (x{os_ref['quantidade']}) | Retorno: {prazo.strftime('%d/%m/%Y')}")
    if not tem_pendente: print("Nenhum material fora do estoque.")

def gerenciar_dados(data):
    print("\n1. Apagar Material | 2. Limpar Tudo (Reset) | 3. Voltar")
    op = input("Opção: ")
    if op == '1':
        item = input("Material para excluir: ").lower()
        if item in data["materiais"]:
            if input(f"Apagar {item} permanentemente? (s/n): ").lower() == 's':
                del data["materiais"][item]
                print("Item removido.")
    elif op == '2':
        if input("Deseja apagar TODO o banco de dados? (s/n): ").lower() == 's':
            if input("Digite 'CONFIRMAR' para resetar: ") == 'CONFIRMAR':
                data["materiais"], data["ordens_servico"], data["contador_os"] = {}, [], 1
                print("Sistema resetado.")

def main():
    dados = carregar_dados()
    while True:
        print(f"\n{'='*40}\n   SISTEMA DE GESTÃO - P10 EVENTOS\n{'='*40}")
        print("1. Cadastrar/Repor Material")
        print("2. Saída para Evento (Gerar OS e Recibo)")
        print("3. Retorno de Material (Baixa)")
        print("4. Ver Estoque e Pendências")
        print("5. Gerenciar Banco de Dados")
        print("6. Sair e Salvar")
        
        opcao = input("\nEscolha: ")
        
        if opcao == '1': cadastrar_material(dados)
        elif opcao == '2': criar_ordem_servico(dados)
        elif opcao == '3': baixar_os(dados)
        elif opcao == '4': exibir_relatorio(dados)
        elif opcao == '5': gerenciar_dados(dados)
        elif opcao == '6':
            salvar_dados(dados)
            print("Saindo e salvando dados...")
            break

if __name__ == "__main__":
    main()
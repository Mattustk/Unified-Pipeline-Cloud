import pandas as pd
from faker import Faker
import random
from datetime import datetime

fake = Faker('pt_BR')

# Configurações Iniciais
ids_vips = [random.randint(100, 999) for _ in range(50)]
vendedores_tech = [f"VEND-TECH-{i:02d}" for i in range(1, 11)]
vendedores_retail = [f"VEND-RETL-{i:02d}" for i in range(1, 21)]
metodos_pagamento = ['PIX', 'CARTAO_CREDITO', 'CARTAO_DEBITO', 'BOLETO']

# Catálogo de Produtos/Serviços (Para consistência de Preço e Custo)
catalogo = {
    'NEXUS TECH': {
        # Software & Assinaturas
        'Assinatura SaaS Standard': {'valor': 1200.0, 'custo': 300.0, 'id': 'SOFT-SAAS-ST'},
        'Assinatura SaaS Premium': {'valor': 2500.0, 'custo': 500.0, 'id': 'SOFT-SAAS-PR'},
        'Licença ERP Enterprise': {'valor': 12500.0, 'custo': 3000.0, 'id': 'SOFT-ERP-ENT'},
        # Serviços & Consultoria
        'Consultoria TI (Hora)': {'valor': 250.0, 'custo': 100.0, 'id': 'SERV-CONS-H'},
        'Suporte Técnico Remoto': {'valor': 450.0, 'custo': 150.0, 'id': 'SERV-SUP-REM'},
        'Projeto de Infraestrutura': {'valor': 15000.0, 'custo': 7000.0, 'id': 'SERV-INFRA'},
        'Migração para Nuvem (AWS)': {'valor': 8000.0, 'custo': 2500.0, 'id': 'SERV-CLOUD'},
        # Segurança
        'Pentest de Segurança': {'valor': 9500.0, 'custo': 4000.0, 'id': 'SEC-PENTEST'}
    },
    'NEXUS RETAIL': {
        # Periféricos & Hardware
        'Cadeira Gamer Pro': {'valor': 1850.0, 'custo': 900.0, 'id': 'HW-CHAIR-PR'},
        'Monitor 4K 27 pol': {'valor': 2800.0, 'custo': 1400.0, 'id': 'HW-MONIT-4K'},
        'Teclado Mecânico RGB': {'valor': 650.0, 'custo': 200.0, 'id': 'HW-KEYBD-RGB'},
        'Mouse Gamer Sem Fio': {'valor': 450.0, 'custo': 180.0, 'id': 'HW-MOUSE-WL'},
        'Headset Surround 7.1': {'valor': 890.0, 'custo': 350.0, 'id': 'HW-HSET-71'},
        # Computadores & Consoles
        'Notebook Ultra Slim': {'valor': 5500.0, 'custo': 3200.0, 'id': 'HW-NOTE-ULT'},
        'PC Gamer Nexus 1.0': {'valor': 7200.0, 'custo': 4500.0, 'id': 'HW-PC-GMR'},
        'PlayStation 5 Slim': {'valor': 3800.0, 'custo': 2900.0, 'id': 'GME-PS5-SL'},
        # Cabos e Acessórios (Baixo Valor)
        'Cabo HDMI 2.1 2m': {'valor': 120.0, 'custo': 30.0, 'id': 'ACC-HDMI-21'},
        'Mousepad Control XL': {'valor': 150.0, 'custo': 45.0, 'id': 'ACC-MPAD-XL'}
    }
}

def gerar_dados(nome_holding, num_registros, vendedores, arquivo_nome):
    data_list = []
    for _ in range(num_registros):
        # Lógica de Cliente (VIP ou Novo)
        id_cliente = random.choice(ids_vips) if random.random() > 0.4 else random.randint(1000, 9000)

        # Seleção de Produto e Lógica Financeira
        item = random.choice(list(catalogo[nome_holding].keys()))
        info_prod = catalogo[nome_holding][item]

        qtd = random.randint(1, 5)
        valor_unitario = info_prod['valor']
        custo_unitario = info_prod['custo']
        valor_total = round(valor_unitario * qtd, 2)
        custo_total = round(custo_unitario * qtd, 2)

        data_list.append({
            'holding': nome_holding,
            'id_transacao': fake.uuid4(),
            'timestamp': fake.date_time_between(start_date='-1y', end_date='now').strftime('%Y-%m-%d %H:%M:%S'),
            'id_cliente': id_cliente,
            'cpf_cliente': fake.cpf(),
            'nome_cliente': fake.name(),
            'email': fake.email(),
            'id_vendedor': random.choice(vendedores),
            'id_produto': info_prod['id'],
            'item_vendido': item,
            'quantidade': qtd,
            'valor_unitario': valor_unitario,
            'custo_unitario': custo_unitario,
            'valor_total_transacao': valor_total, # Valor total da venda
            'metodo_pagamento': random.choice(metodos_pagamento),
            'data': fake.date_between(start_date='-1y', end_date='today') # Mantido para seu script atual
        })

    df = pd.DataFrame(data_list)
    df.to_csv(arquivo_nome, index=False)
    print(f"✅ {nome_holding} gerado com {num_registros} linhas.")

# Execução
gerar_dados('NEXUS TECH', 500, vendedores_tech, 'tech_nexus.csv')
gerar_dados('NEXUS RETAIL', 1000, vendedores_retail, 'retail_nexus.csv')

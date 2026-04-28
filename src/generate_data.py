import pandas as pd
from faker import Faker
import random
import numpy as np
import os

# --- ITEM 1: REPRODUTIBILIDADE ---
# Fixa a semente para o resultado ser sempre igual na máquina do Leonardo
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker('pt_BR')
Faker.seed(SEED)

# --- ITEM 8: VARIÁVEIS DE AMBIENTE ---
# Se não houver variável definida, usa os nomes padrão
FILE_TECH = os.getenv('FILENAME_TECH', 'tech_nexus.csv')
FILE_RETAIL = os.getenv('FILENAME_RETAIL', 'retail_nexus.csv')

# Configurações Iniciais
ids_vips = [random.randint(100, 999) for _ in range(50)]
vendedores_tech = [f"VEND-TECH-{i:02d}" for i in range(1, 11)]
vendedores_retail = [f"VEND-RETL-{i:02d}" for i in range(1, 21)]
metodos_pagamento = ['PIX', 'CARTAO_CREDITO', 'CARTAO_DEBITO', 'BOLETO']

catalogo = {
    'NEXUS TECH': {
        'Assinatura SaaS Standard': {'valor': 1200.0, 'custo': 300.0, 'id': 'SOFT-SAAS-ST'},
        'Assinatura SaaS Premium': {'valor': 2500.0, 'custo': 500.0, 'id': 'SOFT-SAAS-PR'},
        'Licença ERP Enterprise': {'valor': 12500.0, 'custo': 3000.0, 'id': 'SOFT-ERP-ENT'},
        'Consultoria TI (Hora)': {'valor': 250.0, 'custo': 100.0, 'id': 'SERV-CONS-H'},
        'Suporte Técnico Remoto': {'valor': 450.0, 'custo': 150.0, 'id': 'SERV-SUP-REM'},
        'Projeto de Infraestrutura': {'valor': 15000.0, 'custo': 7000.0, 'id': 'SERV-INFRA'},
        'Migração para Nuvem (AWS)': {'valor': 8000.0, 'custo': 2500.0, 'id': 'SERV-CLOUD'},
        'Pentest de Segurança': {'valor': 9500.0, 'custo': 4000.0, 'id': 'SEC-PENTEST'}
    },
    'NEXUS RETAIL': {
        'Cadeira Gamer Pro': {'valor': 1850.0, 'custo': 900.0, 'id': 'HW-CHAIR-PR'},
        'Monitor 4K 27 pol': {'valor': 2800.0, 'custo': 1400.0, 'id': 'HW-MONIT-4K'},
        'Teclado Mecânico RGB': {'valor': 650.0, 'custo': 200.0, 'id': 'HW-KEYBD-RGB'},
        'Mouse Gamer Sem Fio': {'valor': 450.0, 'custo': 180.0, 'id': 'HW-MOUSE-WL'},
        'Headset Surround 7.1': {'valor': 890.0, 'custo': 350.0, 'id': 'HW-HSET-71'},
        'Notebook Ultra Slim': {'valor': 5500.0, 'custo': 3200.0, 'id': 'HW-NOTE-ULT'},
        'PC Gamer Nexus 1.0': {'valor': 7200.0, 'custo': 4500.0, 'id': 'HW-PC-GMR'},
        'PlayStation 5 Slim': {'valor': 3800.0, 'custo': 2900.0, 'id': 'GME-PS5-SL'},
        'Cabo HDMI 2.1 2m': {'valor': 120.0, 'custo': 30.0, 'id': 'ACC-HDMI-21'},
        'Mousepad Control XL': {'valor': 150.0, 'custo': 45.0, 'id': 'ACC-MPAD-XL'}
    }
}

def gerar_dados(nome_holding, num_registros, vendedores, arquivo_nome):
    data_list = []
    # --- ITEM 1: DATA FIXA ---
    FIXED_END_DATE = '2025-12-31'

    for i in range(num_registros):
        id_cliente = random.choice(ids_vips) if random.random() > 0.4 else random.randint(1000, 9000)
        item = random.choice(list(catalogo[nome_holding].keys()))
        info_prod = catalogo[nome_holding][item]

        qtd = random.randint(1, 5)
        valor_unitario = info_prod['valor']
        custo_unitario = info_prod['custo']
        
        # Variável para controlar a lógica de erro
        prob = random.random()

        # --- ITEM 5: INJEÇÃO DE RUÍDO CONTROLADO ---
        
        # A. Erro de Cálculo (2% de chance) - Valor total não bate com Unitario * Qtd
        if prob < 0.02:
            valor_total_transacao = round((valor_unitario * qtd) * 1.5, 2)
        else:
            valor_total_transacao = round(valor_unitario * qtd, 2)

        # B. Nulos (1% de chance) - Custo unitário vira None
        if 0.02 <= prob < 0.03:
            custo_unitario = None
        
        # C. Negativos (0,5% de chance) - Valor unitário fica negativo
        if 0.03 <= prob < 0.035:
            valor_unitario = valor_unitario * -1
            valor_total_transacao = valor_total_transacao * -1

        data_list.append({
            'holding': nome_holding,
            'id_transacao': fake.uuid4(),
            'timestamp': fake.date_time_between(start_date='-1y', end_date=FIXED_END_DATE).strftime('%Y-%m-%d %H:%M:%S'),
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
            'valor_total_transacao': valor_total_transacao,
            'metodo_pagamento': random.choice(metodos_pagamento),
            'data': fake.date_between(start_date='-1y', end_date=FIXED_END_DATE)
        })

    df = pd.DataFrame(data_list)
    df.to_csv(arquivo_nome, index=False)
    # Cálculo para o print bater com a realidade
    print(f"✅ {nome_holding}: {num_registros} linhas geradas.")
    print(f"   -> Ruído injetado: ~3.5% de registros inconsistentes para teste de robustez.")

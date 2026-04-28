Unified Data Pipeline (AWS Edition)

## Aviso de Privacidade e Origem dos Dados
**Nota Importante: Todos os dados utilizados neste projeto (nomes, CPFs, e-mails e transações) foram gerados de forma artificial utilizando a biblioteca Faker do python. Qualquer semelhança com nomes, pessoas ou dados da vida real é mera coincidência. Este ambiente foi construído estritamente para fins de demonstração técnica e estudo de engenharia de dados.**


![Status do Workflow](Screenshots/Workflow.png)



## Sobre o Projeto:

Unified Pipeline Cloud v2.0 — Medallion Architecture
Este projeto implementa um pipeline de dados unificado na AWS para processamento de múltiplas holdings (Nexus Tech e Nexus Retail), seguindo rigorosamente a Arquitetura Medalhão (Bronze, Silver e Gold) e os princípios de Data Lakehouse da Databricks.

Evolução v2.0 (The "Audit" Update)
Após feedback técnico, o projeto foi refatorado para transcender o ETL básico, focando em Governança e Resiliência:

Qualidade de Dados (Quality Gates): Implementação de validação cruzada (Preço * Qtd == Total). Registros inconsistentes são desviados para uma Quarentena, garantindo que a camada Gold seja 100% íntegra.

Observabilidade: Substituição de prints por Logging Estruturado. Todo o fluxo é rastreável, facilitando o debug em produção.

Modularização: Código estruturado em funções reutilizáveis, reduzindo a repetição e facilitando a manutenção (Padrão Don't Repeat Yourself - DRY).

Schema Enforcement: Proteção contra quebra de tipos na ingestão Bronze, tratando dados brutos como strings antes da tipagem rigorosa na Silver.

## Fluxo de Dados (Arquitetura)

```mermaid
graph LR
    A[S3 Bronze: Raw CSVs] --> B(Script Python: Ingestão)
    B --> C{Quality Gate}
    C -->|Falha| D[S3 Quarentena: Erros CSV]
    C -->|Sucesso| E(S3 Silver: Limpeza Parquet)
    E --> F(S3 Gold: Business Logic)
    F --> G[Gold RH: Comissões]
    F --> H[Gold Financeiro: DRE]
    F --> I[Gold Master: Consolidado]



ecnologias Utilizadas
Python 3.11

AWS S3 (Armazenamento Distribuído)

AWS DataWrangler (Integração otimizada com S3)

Pandas (Motor de transformação)

Logging (Monitoramento de pipeline)

omo Executar (Quick Start)
Instale as dependências:

pip install pandas awswrangler boto3

Configure suas credenciais AWS:

Certifique-se de que seu ambiente está autenticado via AWS CLI (aws configure).

Estrutura do S3:
O script espera um bucket chamado guilherme-holding com as pastas nexus-tech/raw/ e nexus-retail/raw/.

Execute o Pipeline:

python main.py

## Autor
Guilherme

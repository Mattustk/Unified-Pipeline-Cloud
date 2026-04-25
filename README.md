## Guilherme Group: Unified Data Pipeline (AWS Edition)

## Aviso de Privacidade e Origem dos Dados
**Nota Importante: Todos os dados utilizados neste projeto (nomes, CPFs, e-mails e transações) foram gerados de forma artificial utilizando a biblioteca Faker. Qualquer semelhança com nomes, pessoas ou dados da vida real é mera coincidência. Este ambiente foi construído estritamente para fins de demonstração técnica e estudo de engenharia de dados.


(Workflow.png)



## Descrição do Projeto
Este projeto estabelece a base da infraestrutura de dados do Guilherme Group. Trata-se de uma **pipeline de ETL (Extração, Transformação e Carga) robusta, desenvolvida para unificar fluxos de dados de diferentes verticais de negócio (atualmente Tech e Retail) em uma camada consolidada para análise estratégica.**
A solução utiliza uma arquitetura moderna baseada em Nuvem (AWS), garantindo que os dados da holding sejam processados com integridade total, performance colunar e automação completa.

## Arquitetura Técnica
O projeto foi construído utilizando as melhores práticas de Engenharia de Dados:

**Cloud Storage:** AWS S3 (Raw e Processed).

**Processamento:** AWS Glue (Python Shell/Pandas).

**Data Handling:** awswrangler para integração nativa e pandas para manipulação.

**Formato de Saída:** Apache Parquet (Otimização de custo e performance de consulta).

**Orquestração:** AWS Glue Workflows (Triggers automatizados).

## Diferenciais do Projeto
**1. Blindagem de Dados (Data Quality)**
O script não é apenas um transportador de dados. Ele possui uma camada de Data Validation rigorosa utilizando assertions. Se um dado crítico (CPF, Valor, IDs) vier nulo ou corrompido, a pipeline trava automaticamente, garantindo que "lixo" nunca chegue à camada final.

**2. Eficiência de Storage e Custo**
Ao converter os arquivos originais em Parquet e utilizar a lógica de Overwrite, o sistema reduz o espaço em disco e acelera em até 10x a velocidade de leitura para ferramentas de BI, economizando custos operacionais de nuvem.

**3. Orquestração Autônoma**
A pipeline não depende de intervenção manual. Através de triggers orquestrados, o fluxo de dados é contínuo e resiliente, tratando erros de concorrência e permissões de forma elegante.

## Tecnologias Utilizadas

**Python 3.9**

**Pandas (Tratamento de dados)**

**AWS SDK (Boto3) (Comunicação com a nuvem)**

**AWS Data Wrangler (ETL de alta performance)**

**AWS Glue (Serverless Spark/Python environment)**

## Roadmap & Futuro (Expansion Plan)

O Guilherme Group foi desenhado para ser escalável. Os próximos passos já mapeados para o projeto são:

**Novas Holdings:** Integração modular de novas empresas do grupo apenas adicionando novos caminhos de entrada.

**Real-Time Data:** Processamento de vendas em tempo real (Streaming).

**Data Lakehouse:** Implementação de tabelas AWS Glue Catalog para consultas via Amazon Athena.

Dashboards de Alta Gestão: Integração direta da camada final com Amazon QuickSight ou PowerBI.

## Autor
Guilherme - Lead Data Engineer no Guilherme Group

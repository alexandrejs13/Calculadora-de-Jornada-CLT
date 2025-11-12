Calculadora de Jornada CLT (Streamlit)

Este é um aplicativo web simples para calcular a jornada de trabalho semanal e mensal, observando as regras da Consolidação das Leis do Trabalho (CLT) no Brasil, incluindo a regra da Hora Noturna Reduzida.

Recursos

Cálculo Dinâmico de Saída: Calcula o horário de saída necessário para cumprir a jornada diária, ajustando automaticamente para o período noturno (22:00h às 05:00h).

Regime de Compensação: Suporte para jornada de 5 dias (8h48m diários) e 6 dias (7h20m diários) para totalizar 44 horas semanais.

Intervalo: Permite configurar o tempo de refeição/descanso (mínimo 1 hora para jornadas superiores a 6 horas).

Resumo Semanal e Mensal: Apresenta a jornada completa em formato de tabela.

Como Executar Localmente

Pré-requisitos: Certifique-se de ter o Python instalado.

Instalar dependências:

pip install -r requirements.txt


Executar o Aplicativo:

streamlit run app.py


O Streamlit abrirá o aplicativo automaticamente no seu navegador, geralmente em http://localhost:8501.

Como Fazer Deploy no Streamlit Community Cloud

Crie um novo repositório no GitHub com os arquivos app.py e requirements.txt.

Acesse o Streamlit Community Cloud.

Conecte seu GitHub e selecione o repositório.

O Streamlit fará o deploy do seu aplicativo automaticamente.

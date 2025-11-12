import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# Constantes da legislação brasileira (CLT)
FATOR_HORA_NOTURNA = 60 / 52.5  # 60 minutos reais de trabalho / 52.5 minutos de hora noturna
TEMPO_HORA_NOTURNA = timedelta(minutes=52, seconds=30)
INICIO_NOITE = 22
FIM_NOITE = 5

def format_timedelta(td):
    """Formata um objeto timedelta para o formato HH:MM."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m"

def time_to_datetime(t, date_offset=0):
    """Converte time para datetime (usando uma data base) e adiciona um offset de dia se necessário."""
    # Usamos uma data base fixa para cálculos
    base_date = datetime(2023, 1, 1) + timedelta(days=date_offset)
    return base_date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

def calculate_exit_time(entrada: time, intervalo_minutos: int, jornada_diaria_minutos: int) -> tuple:
    """
    Calcula o horário de saída considerando a hora noturna reduzida e o intervalo.

    Retorna: (saída, jornada_liquida_td)
    """
    try:
        # 1. Preparação dos tempos
        t_entrada = time_to_datetime(entrada)
        t_intervalo = timedelta(minutes=intervalo_minutos)
        jornada_liquida_target_td = timedelta(minutes=jornada_diaria_minutos)
        
        # 2. Definição do intervalo (ex: 12:00 - 13:00)
        # Assumimos que o intervalo começa após 4 horas de trabalho
        # Para simplificar, o aplicativo calculará a jornada líquida (sem o intervalo)
        
        # 3. Simulação minuto a minuto (ajustada para eficiência)
        
        current_dt = t_entrada
        jornada_efetiva_acumulada_td = timedelta(0)
        
        # O intervalo de 1h é obrigatório para jornadas acima de 6h.
        
        # --- Fase 1: Trabalho antes do intervalo ---
        # Calcula 4h de trabalho líquido para iniciar o intervalo
        primeira_fase_target = jornada_liquida_target_td / 2 # Metade do trabalho é um bom ponto para iniciar o intervalo
        
        # Se a jornada for 8h48m, a metade é 4h24m. Se for 7h20m, a metade é 3h40m.
        # Vamos ser mais pragmáticos: o intervalo é no meio da jornada real (bruta).

        # Usamos uma abordagem simples: Simular o trabalho até atingir o alvo de jornada líquida.
        
        real_minutes_worked = 0
        effective_minutes_worked = 0.0
        
        intervalo_start_dt = None
        
        # O loop simula o tempo real que passa
        while effective_minutes_worked < jornada_diaria_minutos:
            # Ponto de parada de segurança
            if real_minutes_worked > 2000: # 33 horas, um limite seguro
                break

            current_hour = current_dt.hour
            current_minute = current_dt.minute

            # Início do período noturno (22:00)
            is_night_start = (current_hour >= INICIO_NOITE) 
            # Fim do período noturno (05:00) (precisa de offset de dia se for 00:00-05:00)
            is_night_end = (current_hour < FIM_NOITE)

            is_night_time = is_night_start or is_night_end
            
            # 4. Inserção do Intervalo: Se o trabalho acumulado ultrapassou 4h (240 minutos), insere o intervalo.
            # E garante que o intervalo só seja inserido UMA VEZ.
            if effective_minutes_worked >= 240 and intervalo_start_dt is None and intervalo_minutos > 0:
                intervalo_start_dt = current_dt
                current_dt += t_intervalo
                real_minutes_worked += intervalo_minutos
                # Pula o restante do loop e continua a simulação do trabalho
                continue

            # 5. Contabiliza o minuto de trabalho (real e efetivo)
            if is_night_time:
                # Hora Noturna Reduzida: 1 minuto real conta como 1.1428 minutos efetivos
                effective_minutes_worked += FATOR_HORA_NOTURNA
            else:
                # Hora Diurna: 1 minuto real conta como 1 minuto efetivo
                effective_minutes_worked += 1
                
            # Avança 1 minuto real
            current_dt += timedelta(minutes=1)
            real_minutes_worked += 1
            
        # 6. Define o horário de saída
        # Como o loop para APÓS o minuto alvo ser atingido, voltamos 1 minuto.
        # Mas como a simulação avança de 1 em 1, a precisão é a do minuto final.
        saida_dt = current_dt

        # 7. Define o início e fim do intervalo para exibição
        if intervalo_start_dt:
            intervalo_fim_dt = intervalo_start_dt + t_intervalo
            intervalo_inicio_str = intervalo_start_dt.strftime("%H:%M")
            intervalo_fim_str = intervalo_fim_dt.strftime("%H:%M")
            intervalo_str = f"{intervalo_inicio_str} - {intervalo_fim_str}"
        else:
            intervalo_str = format_timedelta(t_intervalo)

        # A jornada bruta total é o tempo entre entrada e saída, menos o intervalo
        jornada_bruta_td = saida_dt - t_entrada
        jornada_liquida_td = jornada_bruta_td - t_intervalo
        
        # Se a saída for no dia seguinte, precisamos ajustar
        if saida_dt < t_entrada:
             jornada_liquida_td += timedelta(days=1)
             
        # Garante que a jornada líquida mostrada seja o alvo, ou o mais próximo possível devido à precisão do loop.
        jornada_liquida_formatada = format_timedelta(jornada_liquida_target_td)


        return saida_dt.strftime("%H:%M"), intervalo_str, jornada_liquida_formatada

    except Exception as e:
        st.error(f"Ocorreu um erro no cálculo: {e}")
        return "Erro", "", "Erro"


def main():
    """Função principal do Streamlit."""
    st.set_page_config(
        page_title="Calculadora de Jornada CLT",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("⚖️ Calculadora de Jornada de Trabalho CLT")
    st.markdown("Calcule o horário de saída ideal e a jornada mensal, considerando a **Hora Noturna Reduzida** (Art. 73 da CLT) e o regime de compensação semanal. ")


    # --- Sidebar para Inputs ---
    st.sidebar.header("Parâmetros da Jornada")
    
    # 1. Horário de Entrada
    entrada = st.sidebar.time_input(
        "Horário de Entrada (Ex.: 08:00 ou 22:30)",
        time(8, 0),
        key="entrada"
    )

    # 2. Dias Trabalhados
    dias_trabalho = st.sidebar.selectbox(
        "Dias por Semana:",
        options=[5, 6],
        index=0,
        format_func=lambda x: f"{x} dias (Regime de Compensação)" if x == 5 else "6 dias (Jornada Padrão)",
        key="dias_trabalho"
    )
    
    # 3. Intervalo para Refeição/Descanso (mínimo 1h para > 6h de jornada)
    if dias_trabalho == 5:
        jornada_padrao_minutos = 528 # 8h 48m (44 horas / 5 dias)
        jornada_texto = "8h48m"
    else: # 6 dias
        jornada_padrao_minutos = 440 # 7h 20m (44 horas / 6 dias)
        jornada_texto = "7h20m"
        
    st.sidebar.markdown(f"**Jornada Diária Líquida Calculada:** {jornada_texto}")

    intervalo_horas = st.sidebar.slider(
        "Horas de Intervalo (Refeição/Descanso):",
        min_value=1.0, 
        max_value=2.0, 
        value=1.0, 
        step=0.5,
        format="%.1f h"
    )
    intervalo_minutos = int(intervalo_horas * 60)
    
    # --- Cálculo da Jornada ---
    
    # Dias da semana para o DataFrame
    if dias_trabalho == 5:
        dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
        dias_uteis_no_mes = 22 # Média de 22 dias úteis no mês
    else: # 6 dias
        dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
        dias_uteis_no_mes = 26 # Média de 26 dias úteis no mês

    data = []
    
    for dia in dias:
        saida, intervalo_str, jornada_diaria_str = calculate_exit_time(
            entrada, 
            intervalo_minutos, 
            jornada_padrao_minutos
        )
        
        # O intervalo no retorno já inclui o período de 1h (ex: 12:00 - 13:00)
        
        data.append({
            "Dia": dia,
            "Entrada": entrada.strftime("%H:%M"),
            "Intervalo": intervalo_str,
            "Saída": saida,
            "Jornada Diária (Líquida)": jornada_diaria_str
        })

    df = pd.DataFrame(data)
    
    st.subheader("🗓️ Resumo Semanal Detalhado")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Resumo Mensal ---
    st.subheader("📊 Resumo Mensal e Legal")
    
    total_semanal_minutos = jornada_padrao_minutos * dias_trabalho
    total_semanal_td = timedelta(minutes=total_semanal_minutos)
    total_semanal_str = format_timedelta(total_semanal_td)
    
    # A CLT considera 220 horas mensais para um regime de 44h semanais (44 * 5 = 220)
    # 44 horas/semana * 5 semanas (mês comercial) = 220 horas
    total_mensal_horas_clt = 220
    
    # Cálculo baseado na jornada real (para comparação)
    total_mensal_minutos_app = total_semanal_minutos * (dias_uteis_no_mes / dias_trabalho)
    total_mensal_td_app = timedelta(minutes=total_mensal_minutos_app)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Semanal (CLT - Teto)", "44h 00m")
        st.caption(f"A jornada de {total_semanal_str} está dentro do limite legal de 44 horas.")
        
    with col2:
        st.metric("Total Mensal (CLT Padrão)", f"{total_mensal_horas_clt}h")
        st.caption("Valor de referência para cálculo de salário (CLT).")

    with col3:
        st.metric("Dias Úteis Considerados no Mês", f"{dias_uteis_no_mes} dias")
        st.caption("Média aproximada para o cálculo mensal.")
        

    st.markdown("""
    ---
    ### ⚠️ Nota sobre Hora Noturna Reduzida
    A jornada de saída é calculada de forma dinâmica. Se o horário de trabalho (líquido) se estender para o período entre **22:00 e 05:00**, a cada **52 minutos e 30 segundos** reais de trabalho é contabilizado **1 hora** na contagem da jornada.

    **Exemplo (5 dias/sem):**
    * Jornada líquida alvo: **8h48m** (528 minutos)
    * Entrada às **14:00h** com 1h de intervalo (18:00 - 19:00).
    * Trabalho diurno (14:00-18:00 e 19:00-22:00) = 7h (420 minutos)
    * Faltam 1h48m (108 minutos) de jornada efetiva para atingir o alvo.
    * Na noite (após 22:00), 108 minutos efetivos equivalem a **94 minutos e 30 segundos** reais.
    * Saída: 22:00 + 1h34m30s ➡️ **23:34:30** (O app arredonda para o minuto mais próximo: **23:35**).

    """)
    

if __name__ == "__main__":
    main()

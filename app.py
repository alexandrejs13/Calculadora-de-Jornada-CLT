import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import math

# Constantes da legislação brasileira (CLT)
FATOR_HORA_NOTURNA = 60 / 52.5  # 60 minutos reais de trabalho / 52.5 minutos de hora noturna
INICIO_NOITE = 22
FIM_NOITE = 5

def format_timedelta(td):
    """Formata um objeto timedelta para o formato HH:MM."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m"

def parse_time_to_minutes(time_str: str) -> int:
    """Converte uma string 'HH:MM' ou 'HH' para minutos."""
    time_str = time_str.strip()
    if not time_str:
        return 0
    
    if ':' in time_str:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
    else:
        hours = int(time_str)
        minutes = 0
    return hours * 60 + minutes

def time_to_datetime(t, date_offset=0):
    """Converte time para datetime (usando uma data base) e adiciona um offset de dia se necessário."""
    # Usamos uma data base fixa para cálculos
    base_date = datetime(2023, 1, 1) + timedelta(days=date_offset)
    return base_date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

def calculate_exit_time(entrada: time, intervalo_minutos: int, jornada_diaria_minutos: float) -> tuple:
    """
    Calcula o horário de saída considerando a hora noturna reduzida e o intervalo.

    Retorna: (saída, intervalo_str, jornada_liquida_formatada)
    """
    try:
        # 1. Preparação dos tempos
        t_entrada = time_to_datetime(entrada)
        t_intervalo = timedelta(minutes=intervalo_minutos)
        jornada_liquida_target_td = timedelta(minutes=jornada_diaria_minutos)
        
        # 2. Simulação minuto a minuto (ajustada para eficiência)
        
        current_dt = t_entrada
        
        real_minutes_worked = 0
        effective_minutes_worked = 0.0
        
        intervalo_start_dt = None
        
        # O loop simula o tempo real que passa
        while effective_minutes_worked < jornada_diaria_minutos:
            # Ponto de parada de segurança
            if real_minutes_worked > 2000: # 33 horas, limite seguro
                break

            current_hour = current_dt.hour
            
            # Início do período noturno (22:00)
            is_night_start = (current_hour >= INICIO_NOITE) 
            # Fim do período noturno (05:00) (considera o ciclo 00:00-05:00)
            is_night_end = (current_hour < FIM_NOITE)

            is_night_time = is_night_start or is_night_end
            
            # 3. Inserção do Intervalo: Assumimos que o intervalo começa após 4 horas (240 minutos) de trabalho efetivo,
            # e garante que o intervalo só seja inserido UMA VEZ.
            if effective_minutes_worked >= 240 and intervalo_start_dt is None and intervalo_minutos > 0:
                intervalo_start_dt = current_dt
                current_dt += t_intervalo
                real_minutes_worked += intervalo_minutos
                # Pula o restante do loop e continua a simulação do trabalho
                continue

            # 4. Contabiliza o minuto de trabalho (real e efetivo)
            if is_night_time:
                # Hora Noturna Reduzida: 1 minuto real conta como 1.1428 minutos efetivos
                effective_minutes_worked += FATOR_HORA_NOTURNA
            else:
                # Hora Diurna: 1 minuto real conta como 1 minuto efetivo
                effective_minutes_worked += 1
                
            # Avança 1 minuto real
            current_dt += timedelta(minutes=1)
            real_minutes_worked += 1
            
        # 5. Define o horário de saída
        saida_dt = current_dt

        # 6. Define o início e fim do intervalo para exibição
        if intervalo_start_dt:
            intervalo_fim_dt = intervalo_start_dt + t_intervalo
            intervalo_inicio_str = intervalo_start_dt.strftime("%H:%M")
            intervalo_fim_str = intervalo_fim_dt.strftime("%H:%M")
            # Verifica se o fim do intervalo é no dia seguinte para a exibição (ex: 01:00)
            if intervalo_fim_dt < intervalo_start_dt:
                intervalo_fim_str += " (+1D)"
                
            intervalo_str = f"{intervalo_inicio_str} - {intervalo_fim_str} ({format_timedelta(t_intervalo)})"
        else:
            intervalo_str = format_timedelta(t_intervalo)

        # 7. Verifica se a saída é no dia seguinte
        if saida_dt < t_entrada:
            saida_str = saida_dt.strftime("%H:%M") + " (+1D)"
        else:
            saida_str = saida_dt.strftime("%H:%M")
             
        jornada_liquida_formatada = format_timedelta(jornada_liquida_target_td)

        return saida_str, intervalo_str, jornada_liquida_formatada

    except Exception as e:
        st.error(f"Ocorreu um erro no cálculo: {e}")
        return "Erro", "Erro", "Erro"


def main():
    """Função principal do Streamlit."""
    st.set_page_config(
        page_title="Calculadora de Jornada CLT",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("⚖️ Calculadora de Jornada de Trabalho CLT")
    st.markdown("Calcule o horário de saída ideal e a jornada mensal, considerando o **Regime** e a **Hora Noturna Reduzida** (Art. 73 da CLT).") 


    # --- Sidebar para Inputs ---
    st.sidebar.header("Parâmetros da Jornada")

    regime_trabalho = st.sidebar.radio(
        "Regime de Jornada:",
        options=["Jornada Padrão (Semanal)", "Regime 12x36"],
        index=0
    )

    if regime_trabalho == "Jornada Padrão (Semanal)":
        # 1. Jornada Semanal
        jornada_semanal_str = st.sidebar.text_input(
            "Carga Horária Semanal (Ex: 44, 40, 42:30):",
            "44",
            key="jornada_semanal_str"
        )
        # Parse weekly hours
        try:
            total_semanal_minutos_target = parse_time_to_minutes(jornada_semanal_str)
            if total_semanal_minutos_target == 0:
                 st.error("Jornada semanal deve ser maior que zero.")
                 return
        except:
            st.error("Formato de jornada semanal inválido. Use 'HH' ou 'HH:MM'.")
            return

        # 2. Dias Trabalhados
        dias_trabalho_semana = st.sidebar.selectbox(
            "Dias de Trabalho na Semana:",
            options=[5, 6],
            index=0,
            format_func=lambda x: f"{x} dias/semana",
            key="dias_trabalho_semana"
        )

        # 3. Cálculo da Jornada Diária
        jornada_padrao_minutos = total_semanal_minutos_target / dias_trabalho_semana
        jornada_texto = format_timedelta(timedelta(minutes=jornada_padrao_minutos))
        dias_uteis_no_mes = 22 if dias_trabalho_semana == 5 else 26

    else: # Regime 12x36
        dias_trabalho_semana = 7 # O ciclo envolve 7 dias, embora trabalhe 3.5 dias em média
        jornada_padrao_minutos = 720 # 12 horas
        jornada_texto = "12h00m"
        total_semanal_minutos_target = 42 * 60 # Média de 42h (168h/4 semanas)
        dias_uteis_no_mes = 15 # Aproximadamente 15 dias de trabalho (12h) por mês

    st.sidebar.markdown(f"**Jornada Diária Líquida Calculada:** **{jornada_texto}**")


    # 4. Intervalo (Aplica-se a ambos)
    # Garante no mínimo 1h para jornadas >= 6h (360 min). Se for menor, permite 0.5h.
    min_intervalo = 1.0 if jornada_padrao_minutos >= 360 else 0.5 
    
    intervalo_horas = st.sidebar.slider(
        "Horas de Intervalo (Refeição/Descanso):",
        min_value=min_intervalo, 
        max_value=2.0, 
        value=min_intervalo, # Define o valor padrão com base no mínimo legal
        step=0.5,
        format="%.1f h"
    )
    intervalo_minutos = int(intervalo_horas * 60)
    
    # 5. Horário de Entrada (Aplica-se a ambos)
    entrada_default = time(8, 0)
    if jornada_padrao_minutos > 480: # 8h shift or more
        entrada_default = time(8, 0)
    elif regime_trabalho == "Regime 12x36":
        entrada_default = time(19, 0) # 12x36 night shift is common

    entrada = st.sidebar.time_input(
        "Horário de Entrada (Ex.: 08:00 ou 22:30):",
        entrada_default,
        key="entrada"
    )
    
    # --- Cálculo da Jornada ---

    data = []
    
    if regime_trabalho == "Jornada Padrão (Semanal)":
        dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
        if dias_trabalho_semana == 6:
            dias.append("Sábado")
        
        for dia in dias:
            saida, intervalo_str, jornada_diaria_str = calculate_exit_time(
                entrada, 
                intervalo_minutos, 
                jornada_padrao_minutos
            )
            
            data.append({
                "Dia": dia,
                "Entrada": entrada.strftime("%H:%M"),
                "Intervalo": intervalo_str,
                "Saída": saida,
                "Jornada Diária (Líquida)": jornada_diaria_str,
                "Descanso Após Jornada": "11h (Mínimo CLT)"
            })
            
    else: # Regime 12x36
        # Simula 4 dias de trabalho para ilustrar o ciclo 12x36 (12h trabalho / 36h descanso)
        dias = ["Dia 1 (Trabalho)", "Dia 2 (Trabalho)", "Dia 3 (Trabalho)", "Dia 4 (Trabalho)"]
        
        for i, dia in enumerate(dias):
            saida, intervalo_str, jornada_diaria_str = calculate_exit_time(
                entrada, 
                intervalo_minutos, 
                jornada_padrao_minutos # 720 minutos (12h)
            )
            
            data.append({
                "Dia": dia,
                "Entrada": entrada.strftime("%H:%M"),
                "Intervalo": intervalo_str,
                "Saída": saida,
                "Jornada Diária (Líquida)": jornada_diaria_str,
                "Descanso Após Jornada": "36h (Fixa 12x36)"
            })

    df = pd.DataFrame(data)
    
    st.subheader("🗓️ Resumo da Jornada Detalhada")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Resumo Mensal ---
    st.subheader("📊 Resumo Mensal e Legal")
    
    if regime_trabalho == "Regime 12x36":
        total_semanal_str = "Aprox. 42h00m"
        total_mensal_horas_clt = 180 
        col1_caption = "A jornada média semanal é de 42h, considerando 3.5 turnos de 12h."
        col2_caption = "Valor de referência para cálculo de salário (CLT: 180h/mês)."
        col3_caption = "Média aproximada de dias TRABALHADOS no mês."
    else:
        # Padrão Semanal
        total_semanal_str = format_timedelta(timedelta(minutes=total_semanal_minutos_target))
        # Cálculo baseado em semanas comerciais (aprox. 5 semanas/mês)
        total_mensal_horas_clt = round(total_semanal_minutos_target / 60 * 5)
        
        col1_caption = f"Jornada informada pelo usuário. Limite legal é de 44 horas."
        col2_caption = f"Referência CLT: {total_mensal_horas_clt}h/mês (5 semanas x {total_semanal_str})."
        col3_caption = f"Dias de trabalho por semana: {dias_trabalho_semana}."
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Semanal", total_semanal_str)
        st.caption(col1_caption)
        
    with col2:
        st.metric("Total Mensal (Ref. CLT)", f"{total_mensal_horas_clt}h")
        st.caption(col2_caption)

    with col3:
        st.metric("Dias Úteis Considerados no Mês", f"{dias_uteis_no_mes} dias")
        st.caption(col3_caption)
        

    st.markdown("""
    ---
    ### ⚠️ Nota sobre Hora Noturna Reduzida
    A jornada de saída é calculada de forma dinâmica. Se o horário de trabalho (líquido) se estender para o período entre **22:00 e 05:00**, a cada **52 minutos e 30 segundos** reais de trabalho é contabilizado **1 hora** na contagem da jornada (**Hora Ficta**).
    
    * **Intervalo:** O horário de intervalo é inserido na simulação após o acúmulo de 4 horas de trabalho efetivo.
    """)
    

if __name__ == "__main__":
    main()

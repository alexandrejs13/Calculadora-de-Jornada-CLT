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

def parse_input_to_time(time_input: str) -> time | None:
    """Tenta converter uma string de entrada (HH:MM ou HH) para um objeto time."""
    time_input = time_input.strip()
    if not time_input:
        return None
        
    try:
        if ':' in time_input:
            parts = time_input.split(':')
            hour = int(parts[0])
            minute = int(parts[1])
        else:
            hour = int(time_input)
            minute = 0
            
        # Garante que a hora e o minuto estejam dentro de limites válidos
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
        else:
            return None
            
    except ValueError:
        return None
    except Exception:
        return None

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
             
        jornada_liquida_formatada = format_timedelta(timedelta(minutes=jornada_diaria_minutos))

        return saida_str, intervalo_str, jornada_liquida_formatada

    except Exception as e:
        st.error(f"Ocorreu um erro no cálculo: {e}")
        return "Erro", "Erro", "Erro"

def calculate_short_friday_net_minutes(entrada: time, saida: time, intervalo_minutos: int) -> float:
    """
    Calcula os minutos líquidos efetivos trabalhados na Sexta, dado o horário de entrada, saída e intervalo.
    Este cálculo é necessário para redistribuir a jornada restante para Seg-Qui.
    """
    t_entrada = time_to_datetime(entrada)
    t_saida = time_to_datetime(saida)
    
    # Se a saída for antes da entrada, assume-se que é no dia seguinte (e.g., turno noturno)
    if t_saida <= t_entrada:
        t_saida += timedelta(days=1)

    t_intervalo = timedelta(minutes=intervalo_minutos)
    
    current_dt = t_entrada
    real_minutes_worked = 0
    effective_minutes_worked = 0.0
    intervalo_applied = False
    
    while current_dt < t_saida:
        # Ponto de aplicação do Intervalo (após 4 horas reais)
        if real_minutes_worked >= 240 and not intervalo_applied and intervalo_minutos > 0:
            current_dt += t_intervalo
            real_minutes_worked += intervalo_minutos
            intervalo_applied = True
            if current_dt >= t_saida:
                break # Saiu durante o intervalo
        
        if current_dt >= t_saida:
            break # Parar de contar minutos se já passou da hora de saída

        current_hour = current_dt.hour
        is_night_time = (current_hour >= INICIO_NOITE) or (current_hour < FIM_NOITE)

        if is_night_time:
            # Hora Noturna Reduzida
            effective_minutes_worked += FATOR_HORA_NOTURNA
        else:
            effective_minutes_worked += 1
            
        current_dt += timedelta(minutes=1)
        real_minutes_worked += 1
        
    return effective_minutes_worked


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
        options=["Jornada Padrão (Semanal)", "Regime 12x36", "Short Friday (Sexta Curta)"],
        index=0
    )

    jornada_padrao_minutos = 0 # Inicialização: Jornada diária se fosse dividida igualmente
    jornada_texto = ""
    total_semanal_minutos_target = 0
    dias_trabalho_semana = 0
    dias_uteis_no_mes = 0
    is_short_friday = regime_trabalho == "Short Friday (Sexta Curta)"
    saida_sexta_time = None
    jornada_sexta_minutos = 0 # Usado apenas para Short Friday

    if is_short_friday:
        # Short Friday (Sexta Curta) logic
        
        # 1. Base Semanal (Sexta Curta sempre assume 5 dias úteis)
        jornada_semanal_str = st.sidebar.text_input(
            "Carga Horária Semanal (Base: 44, 40, etc.):",
            "44",
            key="jornada_semanal_base_str"
        )
        try:
            total_semanal_minutos_target = parse_time_to_minutes(jornada_semanal_str)
            if total_semanal_minutos_target <= 0: raise ValueError
            jornada_padrao_minutos = total_semanal_minutos_target / 5 # Base diária antes da compensação
            jornada_texto = format_timedelta(timedelta(minutes=jornada_padrao_minutos))
        except:
             st.error("Formato de jornada semanal inválido para Short Friday.")
             return
             
        dias_trabalho_semana = 5
        dias_uteis_no_mes = 22
        
        # 2. Entrada específica da Sexta (mesmo campo de entrada geral, mas validado aqui)
        st.sidebar.markdown("---")
        saida_sexta_str = st.sidebar.text_input(
            "Horário de Saída na Sexta (HH:MM ou HH):",
            "14:00",
            key="saida_sexta_str"
        )
        saida_sexta_time = parse_input_to_time(saida_sexta_str)
        if saida_sexta_time is None:
            st.warning("Aguardando Horário de Saída na Sexta no formato HH:MM.")

    elif regime_trabalho == "Jornada Padrão (Semanal)":
        # 1. Jornada Semanal
        jornada_semanal_str = st.sidebar.text_input(
            "Carga Horária Semanal (Ex: 44, 40, 42:30):",
            "44",
            key="jornada_semanal_str"
        )
        # 2. Dias Trabalhados
        dias_trabalho_semana = st.sidebar.selectbox(
            "Dias de Trabalho na Semana:",
            options=[5, 6],
            index=0,
            format_func=lambda x: f"{x} dias/semana",
            key="dias_trabalho_semana"
        )
        
        try:
            total_semanal_minutos_target = parse_time_to_minutes(jornada_semanal_str)
            if total_semanal_minutos_target > 0 and dias_trabalho_semana > 0:
                jornada_padrao_minutos = total_semanal_minutos_target / dias_trabalho_semana
                jornada_texto = format_timedelta(timedelta(minutes=jornada_padrao_minutos))
            else:
                 jornada_texto = "Jornada inválida"
                 total_semanal_minutos_target = 0
        except:
            jornada_padrao_minutos = 0
            
        dias_uteis_no_mes = 22 if dias_trabalho_semana == 5 else 26

    else: # Regime 12x36
        dias_trabalho_semana = 7 
        jornada_padrao_minutos = 720 # 12 horas
        jornada_texto = "12h00m"
        total_semanal_minutos_target = 42 * 60 # Média de 42h
        dias_uteis_no_mes = 15 

    st.sidebar.markdown(f"**Jornada Diária Líquida Estimada:** **{jornada_texto}**")


    # 3. Intervalo (Aplica-se a todos)
    min_intervalo = 1.0 if jornada_padrao_minutos >= 360 else 0.5 
    
    intervalo_horas = st.sidebar.slider(
        "Horas de Intervalo (Refeição/Descanso):",
        min_value=min_intervalo, 
        max_value=2.0, 
        value=min_intervalo, 
        step=0.5,
        format="%.1f h"
    )
    intervalo_minutos = int(intervalo_horas * 60)
    
    # 4. Horário de Entrada (INPUT DE TEXTO LIVRE)
    entrada_default_str = "08:00"
    if regime_trabalho == "Regime 12x36":
        entrada_default_str = "19:00" 
    
    entrada_str = st.sidebar.text_input(
        "Horário de Entrada (HH:MM ou HH):",
        entrada_default_str,
        key="entrada_str"
    )
    
    # Botão de Cálculo
    calcular_button = st.sidebar.button("Calcular Jornada", type="primary")


    # --- Bloco de Cálculo Condicional ---
    if calcular_button:
        
        # 4b. Validação do Horário de Entrada
        entrada = parse_input_to_time(entrada_str)
        
        if entrada is None:
            st.error("Horário de Entrada inválido. Use o formato HH:MM (ex: 08:00) ou apenas HH (ex: 14).")
            return
            
        # Revalidação de inputs críticos antes do cálculo principal
        if total_semanal_minutos_target <= 0:
            st.error("Por favor, insira uma jornada semanal válida antes de calcular. Verifique a Carga Horária Semanal.")
            return

        data = []
        
        if regime_trabalho == "Jornada Padrão (Semanal)":
            dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
            if dias_trabalho_semana == 6:
                dias.append("Sábado")
            
            # Jornada diária é a jornada padrão calculada no início
            shift_minutes = jornada_padrao_minutos
            
            for dia in dias:
                saida, intervalo_str, jornada_diaria_str = calculate_exit_time(
                    entrada, 
                    intervalo_minutos, 
                    shift_minutes
                )
                
                data.append({
                    "Dia": dia,
                    "Entrada": entrada.strftime("%H:%M"),
                    "Intervalo": intervalo_str,
                    "Saída": saida,
                    "Jornada Diária (Líquida)": jornada_diaria_str,
                    "Descanso Após Jornada": "11h (Mínimo CLT)"
                })
                
        elif is_short_friday:
            
            if saida_sexta_time is None:
                st.error("Por favor, informe e valide o Horário de Saída na Sexta.")
                return

            # 1. Cálculo dos minutos efetivos trabalhados na Sexta (Jornada Fixa)
            jornada_sexta_minutos = calculate_short_friday_net_minutes(
                entrada, 
                saida_sexta_time, 
                intervalo_minutos
            )
            
            # 2. Redistribuição para Seg-Qui
            minutes_needed_for_mon_to_thu = total_semanal_minutos_target - jornada_sexta_minutos
            
            if minutes_needed_for_mon_to_thu < 0:
                 st.error("A jornada de Sexta Curta informada excede a Carga Horária Semanal total. Por favor, ajuste a Saída na Sexta.")
                 return
                 
            jornada_seg_a_qui_minutos = minutes_needed_for_mon_to_thu / 4
            
            # Limite legal de 10 horas diárias (8h normais + 2h extras compensatórias)
            if jornada_seg_a_qui_minutos > (10 * 60): 
                st.error(f"A jornada de Segunda a Quinta ({format_timedelta(timedelta(minutes=jornada_seg_a_qui_minutos))}) excede o limite legal de 10 horas diárias (Art. 59, CLT).")
                return


            # 3. População da Tabela
            dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
            
            t_entrada_base = time_to_datetime(entrada)

            for dia in dias:
                if dia != "Sexta":
                    # Days Mon-Thu use the redistributed hours
                    saida, intervalo_str, jornada_diaria_str = calculate_exit_time(
                        entrada, 
                        intervalo_minutos, 
                        jornada_seg_a_qui_minutos
                    )
                else:
                    # Friday uses the fixed exit time and already calculated net time
                    saida_sexta_str_display = saida_sexta_time.strftime("%H:%M")
                    # Check if Friday exit is next day (e.g., entry 22:00, exit 01:00)
                    t_saida_sexta_check = time_to_datetime(saida_sexta_time)
                    if t_saida_sexta_check <= t_entrada_base:
                         saida_sexta_str_display += " (+1D)"
                        
                    intervalo_str = format_timedelta(timedelta(minutes=intervalo_minutos))
                    saida = saida_sexta_str_display
                    jornada_diaria_str = format_timedelta(timedelta(minutes=jornada_sexta_minutos))
                    
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
            dias = ["Dia 1 (Trabalho)", "Dia 2 (Descanso)", "Dia 3 (Trabalho)", "Dia 4 (Descanso)"]
            
            # Jornada diária é 12h (720 min)
            shift_minutes = jornada_padrao_minutos

            for i, dia in enumerate(dias):
                if "Trabalho" in dia:
                    saida, intervalo_str, jornada_diaria_str = calculate_exit_time(
                        entrada, 
                        intervalo_minutos, 
                        shift_minutes
                    )
                    descanso = "36h (Fixa 12x36)"
                    entrada_disp = entrada.strftime("%H:%M")
                else:
                    saida = "-"
                    intervalo_str = "-"
                    jornada_diaria_str = "00h 00m"
                    descanso = "Em Descanso 36h"
                    entrada_disp = "-"
                
                data.append({
                    "Dia": dia,
                    "Entrada": entrada_disp,
                    "Intervalo": intervalo_str,
                    "Saída": saida,
                    "Jornada Diária (Líquida)": jornada_diaria_str,
                    "Descanso Após Jornada": descanso
                })

        # --- Exibição de Resultados ---
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
            # Padrão Semanal e Short Friday
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

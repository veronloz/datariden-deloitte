#!/usr/bin/env python3
import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np


def parse_data_from_content():
    """Robust parser: detecta bloques por título, localiza la fila de encabezado y la columna
    'ACUMULAT', y obtiene el total de cada bloque (última fila numérica).
    """

    file_path = "/home/veron/Documents/Hackaton-25/dataset/Datasets Barcelona/Resum dades mensuals i diàries de viatgers FMB 2025_1er Semestre.xlsx"
    import os
    try:
        print(f"Intentando abrir el archivo: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        # Leer la hoja sin headers
        df = pd.read_excel(file_path, sheet_name='Mensuals', header=None)
        print(f"Archivo leído. Dimensiones: {df.shape}")

        # Localizar filas título que marcan bloques
        title_rows = []
        for idx, row in df.iterrows():
            for cell in row:
                if isinstance(cell, str) and 'VIATGERS REALS LÍNIA' in cell.upper():
                    title_rows.append(idx)
                    break
                if isinstance(cell, str) and 'FUNICULAR' == cell.strip().upper():
                    # Funicular puede estar tratado como bloque independiente
                    title_rows.append(idx)
                    break

        if not title_rows:
            print("No se encontraron bloques de línea en la hoja 'Mensuals'")
            raise ValueError("No hay bloques detectados")

        lines_data = {}

        # función auxiliar para buscar encabezado y columna ACUMULAT
        def find_header_and_acumulat(start_idx, look_ahead=12):
            end = min(start_idx + look_ahead, len(df))
            for r in range(start_idx, end):
                row = df.iloc[r]
                row_text = ' '.join([str(x) for x in row if pd.notna(x)])
                up = row_text.upper()
                if 'LÍNIA' in up or 'LINIA' in up:
                    if 'ACUMULAT' in up:
                        # localizar índice exacto de ACUMULAT
                        for col_idx, val in enumerate(row):
                            if pd.notna(val) and isinstance(val, str) and 'ACUMULAT' in val.upper():
                                return r, col_idx
            return None, None

        for i, t_idx in enumerate(title_rows):
            header_idx, acumulat_col = find_header_and_acumulat(t_idx + 1)
            block_start = header_idx + 1 if header_idx is not None else t_idx + 1
            block_end = title_rows[i+1] if i+1 < len(title_rows) else len(df)

            # obtener título original
            title_cell = df.iloc[t_idx].dropna().values
            title_text = str(title_cell[0]) if len(title_cell) > 0 else f"LÍNIA_{i+1}"
            # extraer nombre de línea (desde 'LÍNIA' hasta '(' si existe)
            up = title_text.upper()
            if 'LÍNIA' in up:
                pos = up.find('LÍNIA')
                line_name = title_text[pos:].split('(')[0].strip()
            elif 'FUNICULAR' in up:
                line_name = 'FUNICULAR'
            else:
                line_name = title_text

            print(f"\nProcesando bloque '{line_name}': filas {block_start}..{block_end-1}")

            if header_idx is None or acumulat_col is None:
                print(f"  No se encontró encabezado/columna ACUMULAT para {line_name}; saltando")
                continue

            print(f"  Encabezado en fila {header_idx}, columna ACUMULAT={acumulat_col}")

            # obtener el total del bloque (última fila con valor numérico en ACUMULAT)
            total = None
            total_row = None
            # buscar de abajo hacia arriba para encontrar el total
            for ridx in range(block_end - 1, block_start - 1, -1):
                if ridx >= len(df):
                    continue
                raw_val = df.iloc[ridx, acumulat_col] if acumulat_col < len(df.columns) else None
                if pd.notna(raw_val):
                    val = pd.to_numeric(raw_val, errors='coerce')
                    if pd.notna(val):
                        total = float(val)
                        total_row = ridx
                        print(f"  Total encontrado en fila {ridx+1}: {total:,.2f}")
                        break

            if total is None:
                print(f"  No se encontró total para {line_name}")
                continue

            # para debug: mostrar contexto alrededor del total
            print(f"\n  Contexto alrededor del total (filas {max(total_row-1, 0)+1}..{min(total_row+2, len(df))})")
            for r in range(max(total_row-1, 0), min(total_row+2, len(df))):
                row_vals = [str(x) for x in df.iloc[r, max(0, acumulat_col-1):acumulat_col+1] if pd.notna(x)]
                if row_vals:
                    print(f"  Fila {r+1}: {' | '.join(row_vals)}")

            print(f"  Total validado para {line_name}: {total:,.2f}")
            if total > 0:
                lines_data[line_name] = total

        if lines_data:
            print("\nTotales detectados por línea:")
            for k, v in lines_data.items():
                print(f"  {k}: {v:,.2f}")
            return lines_data

        print("No se extrajeron totales")
        return {}

    except Exception as e:
        print(f"Error procesando Excel: {e}")
        return {}

def create_bar_chart(sort_order="Descendente"):
    """Create a bar chart of lines by passenger volume"""
    try:
        data = parse_data_from_content()
        
        print("Datos para el gráfico:", data)  # Debug
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(list(data.items()), columns=['Línea', 'Viajeros'])
        
        # Sort based on user selection
        if sort_order == "Descendente":
            df = df.sort_values('Viajeros', ascending=False)
        else:
            df = df.sort_values('Viajeros', ascending=True)
        
        # Create the plot
        plt.figure(figsize=(14, 8))
        colors = plt.cm.Set3(np.linspace(0, 1, len(df)))
        bars = plt.bar(df['Línea'], df['Viajeros'], color=colors, edgecolor='black', alpha=0.8)
        
        # Customize the plot
        plt.title('Líneas de Metro por Número de Viajeros - 1er Semestre 2025', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Líneas', fontsize=12, fontweight='bold')
        plt.ylabel('Total de Viajeros Acumulados', fontsize=12, fontweight='bold')
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.yticks(fontsize=10)
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{height:,.0f}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Format y-axis with commas
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        plt.tight_layout()
        
        # Save plot to a temporary file
        temp_file = "temp_chart.png"
        plt.savefig(temp_file, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        
        return temp_file
        
    except Exception as e:
        print(f"Error creating chart: {e}")
        # Save error message as image
        temp_file = "temp_chart.png"
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, f'Error: {e}', ha='center', va='center', transform=plt.gca().transAxes, fontsize=12)
        plt.axis('off')
        plt.savefig(temp_file, format='png')
        plt.close()
        return temp_file

def generate_analysis():
    """Generate analysis text based on real data"""
    try:
        data = parse_data_from_content()
        
        df = pd.DataFrame(list(data.items()), columns=['Línea', 'Viajeros'])
        df_sorted = df.sort_values('Viajeros', ascending=False)
        
        total_passengers = df['Viajeros'].sum()
        top_line = df_sorted.iloc[0]
        second_line = df_sorted.iloc[1]
        third_line = df_sorted.iloc[2]
        
        analysis = f"""
# 📊 ANÁLISIS DE DEMANDA POR LÍNEA - 1er Semestre 2025

## Resumen General
**Total de viajeros en todas las líneas:** {total_passengers:,.0f}

## Top 3 Líneas

### 🏆 Línea con mayor demanda
* **Línea:** {top_line['Línea']}
* **Viajeros totales:** {top_line['Viajeros']:,.0f}
* **Porcentaje del total:** {(top_line['Viajeros']/total_passengers)*100:.1f}%

### 🥈 Segunda línea con mayor demanda
* **Línea:** {second_line['Línea']}
* **Viajeros totales:** {second_line['Viajeros']:,.0f}
* **Porcentaje del total:** {(second_line['Viajeros']/total_passengers)*100:.1f}%

### 🥉 Tercera línea con mayor demanda
* **Línea:** {third_line['Línea']}
* **Viajeros totales:** {third_line['Viajeros']:,.0f}
* **Porcentaje del total:** {(third_line['Viajeros']/total_passengers)*100:.1f}%

## 📈 Distribución
* Las 3 líneas principales concentran el **{(top_line['Viajeros'] + second_line['Viajeros'] + third_line['Viajeros'])/total_passengers*100:.1f}%** del total
* Diferencia entre 1ª y 2ª: **{(top_line['Viajeros'] - second_line['Viajeros'])/second_line['Viajeros']*100:+.1f}%**

## 🔍 Ranking completo
        """
        
        # Add ranking
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            analysis += f"\n* **{i}.** {row['Línea']}: **{row['Viajeros']:,.0f}** viajeros (**{(row['Viajeros']/total_passengers)*100:.1f}%**)"
        
        return analysis
        
    except Exception as e:
        return f"**Error en el análisis:** {str(e)}"

def update_dashboard(sort_order):
    """Update the dashboard with new sort order"""
    print(f"Actualizando dashboard con orden: {sort_order}")  # Debug
    chart = create_bar_chart(sort_order)
    analysis = generate_analysis()
    return chart, analysis

# Create the Gradio interface
with gr.Blocks(title="Dashboard de Análisis de Demanda - Metro Barcelona", theme=gr.themes.Soft()) as dashboard:
    gr.Markdown("""
    # 🚇 Dashboard de Análisis de Demanda - Metro Barcelona
    ### Visualización de líneas por volumen de viajeros - 1er Semestre 2025
    *Datos reales extraídos del archivo Excel proporcionado*
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            sort_dropdown = gr.Dropdown(
                choices=["Descendente", "Ascendente"],
                value="Descendente",
                label="🎯 Orden de clasificación",
                info="Ordenar de mayor a menor demanda o viceversa"
            )
            
            gr.Markdown("### 📋 Líneas Analizadas")
            gr.Markdown("""
            - Línea 1
            - Línea 2  
            - Línea 3
            - Línea 4
            - Línea 5
            - Línea 9/10 Nord
            - Línea 9/10 Sud
            - Línea 11
            - Funicular
            
            **Período:** Enero - Junio 2025
            **Fuente:** Datos mensuales acumulados
            """)
            
        with gr.Column(scale=2):
            with gr.Row():
                chart_output = gr.Image(label="📊 Gráfico de Líneas por Demanda", height=500)
            
            with gr.Row():
                analysis_output = gr.Markdown(label="📈 Análisis Detallado")
    
    # Set up the interaction
    sort_dropdown.change(
        fn=update_dashboard,
        inputs=sort_dropdown,
        outputs=[chart_output, analysis_output]
    )
    
    # Initial load
    dashboard.load(
        fn=lambda: update_dashboard("Descendente"),
        outputs=[chart_output, analysis_output]
    )

# Launch the dashboard
if __name__ == "__main__":
    # Test data parsing
    print("=== INICIO DEBUG ===")
    data = parse_data_from_content()
    print("\nDatos parseados:")
    for line, passengers in data.items():
        print(f"  {line}: {passengers:,.2f} viajeros")
    
    if data:
        total = sum(data.values())
        print(f"\nTotal viajeros: {total:,.2f}")
    print("=== FIN DEBUG ===")
    
    dashboard.launch(share=False)

def build_demanda_tab(parent_blocks=None):
    """Devuelve el bloque (tab) de análisis de demanda."""
    with gr.Tab("🚇 Demanda Metro Barcelona"):
        gr.Markdown("""
        # 🚇 Dashboard de Análisis de Demanda - Metro Barcelona
        ### Visualización de líneas por volumen de viajeros - 1er Semestre 2025
        *Datos reales extraídos del archivo Excel proporcionado*
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                sort_dropdown = gr.Dropdown(
                    choices=["Descendente", "Ascendente"],
                    value="Descendente",
                    label="🎯 Orden de clasificación",
                    info="Ordenar de mayor a menor demanda o viceversa"
                )
                
                gr.Markdown("### 📋 Líneas Analizadas")
                gr.Markdown("""
                - Línea 1
                - Línea 2  
                - Línea 3
                - Línea 4
                - Línea 5
                - Línea 9/10 Nord
                - Línea 9/10 Sud
                - Línea 11
                - Funicular
                
                **Período:** Enero - Junio 2025  
                **Fuente:** Datos mensuales acumulados
                """)
                
            with gr.Column(scale=2):
                with gr.Row():
                    chart_output = gr.Image(label="📊 Gráfico de Líneas por Demanda", height=500)
                
                with gr.Row():
                    analysis_output = gr.Markdown(label="📈 Análisis Detallado")
        
        # Interacciones
        sort_dropdown.change(
            fn=update_dashboard,
            inputs=sort_dropdown,
            outputs=[chart_output, analysis_output]
        )
        
        # Carga inicial
        if parent_blocks:
            parent_blocks.load(
                fn=lambda: update_dashboard("Descendente"),
                outputs=[chart_output, analysis_output]
            )

# Solo lanza el dashboard si este script se ejecuta directamente
if __name__ == "__main__":
    with gr.Blocks(theme=gr.themes.Soft(), title="Dashboard de Análisis de Demanda") as dashboard:
        build_demanda_tab()
    dashboard.launch(share=False)
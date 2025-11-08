import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np

def parse_data_from_content():
    """Parse the data directly from the provided content"""
    
    # Extract line totals from the provided data
    lines_data = {}
    
    # Línea 1
    lines_data['LÍNIA 1'] = 63780977.95031774
    
    # Línea 2
    lines_data['LÍNIA 2'] = 26473229.063012976
    
    # Línea 3
    lines_data['LÍNIA 3'] = 45112195.2744986
    
    # Línea 4
    lines_data['LÍNIA 4'] = 30740378.18746676
    
    # Línea 5
    lines_data['LÍNIA 5'] = 61019322.68223789
    
    # Línea 9/10 Nord
    lines_data['LÍNIA 9/10 NORD'] = 6756971.69
    
    # Línea 9/10 Sud
    lines_data['LÍNIA 9/10 SUD'] = 9520422.84
    
    # Línea 11
    lines_data['LÍNIA 11'] = 716876.7896539989
    
    # Funicular
    lines_data['FUNICULAR'] = 498016.52281203633
    
    return lines_data

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
    print("Datos parseados:")
    for line, passengers in data.items():
        print(f"  {line}: {passengers:,.0f} viajeros")
    
    total = sum(data.values())
    print(f"Total viajeros: {total:,.0f}")
    print("=== FIN DEBUG ===")
    
    dashboard.launch(share=False)
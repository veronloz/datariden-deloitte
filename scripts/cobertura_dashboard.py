import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import folium
from folium import plugins

# --- 1. Definir noms de fitxers ---
# Fem servir els noms de fitxer exactes que existeixen al directori
FILE_POBLACIO = "dataset/Datasets Barcelona/Densitat Poblacio Barcelona 2021.xlsx"
FILE_TRANSPORT = "dataset/Datasets Barcelona/Transport Public Barcelona.xlsx"
OUTPUT_CSV = "analisis_transporte_poblacion.csv"

# --- Coordenadas aproximadas de los distritos de Barcelona ---
DISTRITOS_COORDS = {
    'Ciutat Vella': [41.3851, 2.1734],
    'Eixample': [41.3874, 2.1686],
    'Sants-Montjuic': [41.3715, 2.1448],
    'Les Corts': [41.3856, 2.1195],
    'Sarrià-Sant Gervasi': [41.3961, 2.1437],
    'Gràcia': [41.4075, 2.1696],
    'Horta-Guinardó': [41.4278, 2.2145],
    'Nou Barris': [41.4351, 2.1886],
    'Sant Andreu': [41.4335, 2.1806],
    'Sant Martí­': [41.4088, 2.2190]
}

# --- 2. Funció principal de l'anàlisi ---
def analyze_data(dummy=None):
    """
    Funció principal que carrega les dades, les processa, calcula KPIs,
    genera gràfics i retorna els resultats per a Gradio.
    """
    try:
        # Comprovar si els fitxers existeixen
        if not os.path.exists(FILE_POBLACIO):
            return (None, None, None, None, None, f"Error: No s'ha trobat el fitxer {FILE_POBLACIO}")
        if not os.path.exists(FILE_TRANSPORT):
            return (None, None, None, None, None, f"Error: No s'ha trobat el fitxer {FILE_TRANSPORT}")

        # Carregar Dades
        df_transport = pd.read_excel(FILE_TRANSPORT, sheet_name='Parades Transport Public Barcel')
        df_poblacio = pd.read_excel(FILE_POBLACIO, sheet_name='Densitat Poblacio Barcelona 202')

        # --- Fase I: Processament i Neteja ---
        
        # 1. Processar Transport (Filtrar per Metro)
        # Usem 'contains' per incloure 'Metro' i 'Metro i línies urbanes FGC'
        df_metro = df_transport[df_transport['NOM_CAPA'].str.contains('Metro', na=False)]
        
        # 2. Agregar estacions per barri
        # Comptem quantes parades hi ha per 'NOM_BARRI'
        estacions_per_barri = df_metro.groupby('NOM_BARRI').size().reset_index(name='Nombre_Estacions_Metro')

        # 3. Preparar dades de població (seleccionem columnes rellevants)
        df_poblacio_clean = df_poblacio[['Nom_Districte', 'Nom_Barri', 'Població', 'Superfície (ha)', 'Densitat neta (hab/ha)']].copy()

        # 4. Fusionar Dades
        # Unim la població amb el recompte d'estacions
        # 'how=left' manté tots els barris, tinguin o no estacions
        df_final = pd.merge(
            df_poblacio_clean,
            estacions_per_barri,
            left_on='Nom_Barri',
            right_on='NOM_BARRI',
            how='left'
        )
        
        # 5. Netejar dades fusionades
        # Els barris sense metro tindran 'NaN' (Nul). Els canviem per 0.
        df_final['Nombre_Estacions_Metro'] = df_final['Nombre_Estacions_Metro'].fillna(0).astype(int)
        
        # Eliminar columna redundant del merge
        if 'NOM_BARRI' in df_final.columns:
            df_final = df_final.drop(columns=['NOM_BARRI'])

        # --- Fase II: Càlcul d'Indicadors (KPIs) ---
        
        # KPI 1: Població per Estació
        # Usem np.where per evitar la divisió per zero
        df_final['Poblacio_per_Estacio'] = np.where(
            df_final['Nombre_Estacions_Metro'] > 0,
            df_final['Població'] / df_final['Nombre_Estacions_Metro'],
            np.inf  # Assignem 'infinit' als barris sense metro per identificar-los
        )
        # Arrodonim per claredat
        df_final['Poblacio_per_Estacio'] = df_final['Poblacio_per_Estacio'].round(0)

        # KPI 2: Estacions per km² (densitat de la xarxa)
        df_final['Estacions_per_km2'] = np.where(
            df_final['Superfície (ha)'] > 0,
            # Convertim 'ha' a 'km2' (100 ha = 1 km2)
            df_final['Nombre_Estacions_Metro'] / (df_final['Superfície (ha)'] / 100),
            0
        )

        # --- Preparar Dades per Visualització ---
        
        # Top 10 Barris amb MÉS pressió (excloent els que tenen 0 estacions, que són 'inf')
        df_pressure = df_final[df_final['Poblacio_per_Estacio'] != np.inf].sort_values(
            by='Poblacio_per_Estacio', ascending=False
        ).head(10)

        # Top 10 Barris MÉS POBLATS SENSE metro (on estacions == 0)
        df_no_metro = df_final[df_final['Nombre_Estacions_Metro'] == 0].sort_values(
            by='Població', ascending=False
        ).head(10)

        # --- Fase III: Visualització ---

        # Gràfic 1: Població per Estació (Més pressió)
        fig1, ax1 = plt.subplots(figsize=(10, 7))
        ax1.barh(df_pressure['Nom_Barri'], df_pressure['Poblacio_per_Estacio'], color='tomato')
        ax1.set_title('Top 10 Barris amb Més Població per Estació de Metro')
        ax1.set_xlabel('Població per Estació (Habitants)')
        ax1.set_ylabel('Barri')
        ax1.invert_yaxis()  # Mostra el valor més alt a dalt
        plt.tight_layout() # Ajusta el gràfic per evitar que es tallin les etiquetes

        # Gràfic 2: Població SENSE Metro
        fig2, ax2 = plt.subplots(figsize=(10, 7))
        ax2.barh(df_no_metro['Nom_Barri'], df_no_metro['Població'], color='skyblue')
        ax2.set_title('Top 10 Barris Més Poblats SENSE Estació de Metro')
        ax2.set_xlabel('Població Total')
        ax2.set_ylabel('Barri')
        ax2.invert_yaxis()
        plt.tight_layout()

        # Guardar el dataset complet per descarregar
        df_final.sort_values(by='Poblacio_per_Estacio', ascending=False).to_csv(OUTPUT_CSV, index=False)

        # Retornar tots els elements per a la interfície de Gradio
        return (
            fig1, 
            df_pressure[['Nom_Barri', 'Població', 'Nombre_Estacions_Metro', 'Poblacio_per_Estacio']], 
            fig2, 
            df_no_metro[['Nom_Barri', 'Població', 'Nombre_Estacions_Metro']], 
            OUTPUT_CSV, 
            "Anàlisi completada amb èxit."
        )

    except Exception as e:
        # En cas d'error, el mostrem a l'usuari
        error_message = f"Error durant l'anàlisi: {str(e)}"
        return (None, None, None, None, None, error_message)

def analyze_estaciones_por_distrito(dummy=None):
    """
    Funció que analitza les estacions de metro per districte i retorna visualitzacions.
    """
    try:
        # Comprovar si el fitxer existeix
        if not os.path.exists(FILE_TRANSPORT):
            return (None, None, None, f"Error: No s'ha trobat el fitxer {FILE_TRANSPORT}")

        # Carregar dades de transport
        df_transport = pd.read_excel(FILE_TRANSPORT, sheet_name='Parades Transport Public Barcel')
        
        # Filtrar per Metro
        df_metro = df_transport[df_transport['NOM_CAPA'].str.contains('Metro', na=False)].copy()
        
        if df_metro.empty:
            return (None, None, None, "Error: No s'han trobat dades de metro")
        
        # Contar estacions per districte
        estacions_per_distrito = df_metro.groupby('NOM_DISTRICTE').size().reset_index(name='Nombre_Estaciones')
        estacions_per_distrito = estacions_per_distrito.sort_values('Nombre_Estaciones', ascending=False)
        
        # Gràfic 1: Barres amb número de estacions per districte
        fig1, ax1 = plt.subplots(figsize=(12, 7))
        colors = plt.cm.Set3(np.linspace(0, 1, len(estacions_per_distrito)))
        bars = ax1.bar(estacions_per_distrito['NOM_DISTRICTE'], estacions_per_distrito['Nombre_Estaciones'], 
                      color=colors, edgecolor='black', alpha=0.8)
        ax1.set_title('Estaciones de Metro por Distrito en Barcelona', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Distrito', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Número de Estaciones', fontsize=12, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Añadir etiquetas en las barras
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold')
        plt.tight_layout()
        
        # Gràfic 2: Gràfic circular (pie chart)
        fig2, ax2 = plt.subplots(figsize=(10, 8))
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(estacions_per_distrito)))
        wedges, texts, autotexts = ax2.pie(estacions_per_distrito['Nombre_Estaciones'], 
                                             labels=estacions_per_distrito['NOM_DISTRICTE'],
                                             autopct='%1.1f%%',
                                             colors=colors_pie,
                                             startangle=90)
        ax2.set_title('Distribución de Estaciones de Metro por Distrito', fontsize=14, fontweight='bold')
        
        # Mejorar legibilidad
        for text in texts:
            text.set_fontsize(9)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        plt.tight_layout()
        
        # Retornar gràfics i dades
        return (
            fig1,
            fig2,
            estacions_per_distrito,
            "Anàlisi completada amb èxit."
        )
    
    except Exception as e:
        error_message = f"Error durant l'anàlisi: {str(e)}"
        return (None, None, None, error_message)

def create_heatmap_distritos(dummy=None):
    """
    Funció que crea un mapa interactiu amb Folium on els distritos es resalten 
    amb colors segons el nombre d'estacions de metro en els popups.
    """
    try:
        # Comprovar si el fitxer existeix
        if not os.path.exists(FILE_TRANSPORT):
            return (None, f"Error: No s'ha trobat el fitxer {FILE_TRANSPORT}")

        # Carregar dades de transport
        df_transport = pd.read_excel(FILE_TRANSPORT, sheet_name='Parades Transport Public Barcel')
        
        # Filtrar per Metro
        df_metro = df_transport[df_transport['NOM_CAPA'].str.contains('Metro', na=False)].copy()
        
        if df_metro.empty:
            return (None, "Error: No s'han trobat dades de metro")
        
        # Contar estacions per districte
        estaciones_per_distrito = df_metro.groupby('NOM_DISTRICTE').size().reset_index(name='Nombre_Estaciones')
        
        # Obtenir min i max per normalitzar colors
        min_estaciones = estaciones_per_distrito['Nombre_Estaciones'].min()
        max_estaciones = estaciones_per_distrito['Nombre_Estaciones'].max()
        
        # Crear mapa centrat en Barcelona
        mapa = folium.Map(
            location=[41.3851, 2.1734],  # Coordenadas de Barcelona
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Función para normalizar colores (de amarillo a rojo según número de estaciones)
        def get_color(num_estaciones):
            # Normalizar entre 0 y 1 (0 = pocos, 1 = muchos)
            if max_estaciones > min_estaciones:
                normalized = (num_estaciones - min_estaciones) / (max_estaciones - min_estaciones)
            else:
                normalized = 0.5
            
            # Crear color de transición amarillo -> naranja -> rojo
            if normalized < 0.33:
                # Amarillo a Naranja (0.0 a 0.33)
                r, g = 255, int(165 + (normalized / 0.33) * 90)
                b = 0
            elif normalized < 0.66:
                # Naranja a Rojo oscuro (0.33 a 0.66)
                r, g = 255, int(255 - ((normalized - 0.33) / 0.33) * 140)
                b = 0
            else:
                # Rojo oscuro a Rojo brillante (0.66 a 1.0)
                r, g = 255, int(115 - ((normalized - 0.66) / 0.34) * 115)
                b = 0
            
            return f'#{int(r):02x}{int(g):02x}{int(b):02x}'
        
        # Función para obtener color de Folium más cercano al color hex
        def get_folium_color(num_estaciones):
            if max_estaciones > min_estaciones:
                normalized = (num_estaciones - min_estaciones) / (max_estaciones - min_estaciones)
            else:
                normalized = 0.5
            
            # Primero: si está en el tercio inferior -> amarillo
            if normalized < 0.33:
                return 'yellow'
            # Segundo tercio -> naranja
            elif normalized < 0.66:
                return 'orange'
            # Tercio superior -> rojo
            else:
                return 'red'
        
        # Agregar marcadores con popups de color para cada distrito
        for idx, row in estaciones_per_distrito.iterrows():
            distrito = row['NOM_DISTRICTE']
            num_estaciones = row['Nombre_Estaciones']
            
            # Obtener coordenadas (usar las predefinidas o calcular)
            if distrito in DISTRITOS_COORDS:
                coords = DISTRITOS_COORDS[distrito]
            else:
                # Si no existe en el diccionario, intentar usar coordenadas de los datos
                continue
            
            color = get_color(num_estaciones)
            
            # Crear HTML personalizado para el popup con color
            popup_html = f"""
            <div style="font-family: Arial; width: 220px;">
                <div style="background-color: {color}; padding: 10px; border-radius: 5px 5px 0 0; color: white;">
                    <h4 style="margin: 0; font-size: 16px; font-weight: bold;">{distrito}</h4>
                </div>
                <div style="background-color: #f0f0f0; padding: 12px; border-radius: 0 0 5px 5px; border: 1px solid #ddd;">
                    <p style="margin: 5px 0;"><b>🚇 Estaciones:</b> {num_estaciones}</p>
                    <p style="margin: 5px 0; font-size: 12px; color: #666;">Metro Barcelona</p>
                </div>
            </div>
            """
            
            # Crear marcador con icono de color
            folium.Marker(
                location=coords,
                popup=folium.Popup(popup_html, max_width=280),
                icon=folium.Icon(
                    color=get_folium_color(num_estaciones),
                    icon='subway',
                    prefix='fa'
                ),
                tooltip=f"{distrito}: {num_estaciones} estaciones"
            ).add_to(mapa)
        
        # Agregar leyenda
        legend_html = '''
        <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 280px; height: 220px; 
                background-color: white; border: 2px solid grey; z-index: 9999; 
                font-size: 14px; padding: 15px; border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2);">
                <p style="margin: 0 0 12px 0; font-weight: bold; font-size: 16px;">🚇 Estaciones por Distrito</p>
                <hr style="margin: 8px 0;">
                <p style="margin: 8px 0; font-size: 13px;">
                    <span style="display: inline-block; background-color: #FFD700; width: 18px; height: 18px; border-radius: 50%; margin-right: 8px;"></span>
                    Pocas estaciones
                </p>
                <p style="margin: 8px 0; font-size: 13px;">
                    <span style="display: inline-block; background-color: #FFA500; width: 18px; height: 18px; border-radius: 50%; margin-right: 8px;"></span>
                    Estaciones medias
                </p>
                <p style="margin: 8px 0; font-size: 13px;">
                    <span style="display: inline-block; background-color: #FF0000; width: 18px; height: 18px; border-radius: 50%; margin-right: 8px;"></span>
                    Muchas estaciones
                </p>
                <hr style="margin: 10px 0;">
                <p style="margin: 8px 0 0 0; font-size: 12px; color: #666;">
                    <b>Rango:</b> {min_est} - {max_est} estaciones
                </p>
        </div>
        '''.format(min_est=min_estaciones, max_est=max_estaciones)
        
        mapa.get_root().html.add_child(folium.Element(legend_html))
        
        # Guardar mapa a archivo HTML
        mapa_file = "mapa_estaciones_distritos.html"
        mapa.save(mapa_file)
        
        return (mapa_file, "✅ Mapa creado correctamente")
    
    except Exception as e:
        error_message = f"Error durant la creació del mapa: {str(e)}"
        return (None, error_message)

def build_cobertura_tab(parent_blocks=None):
    """
    Construeix la pestanya de cobertura de transport, integrada en el dashboard global.
    
    Parameters:
    -----------
    parent_blocks : gr.Blocks, optional
        El bloc pare (dashboard global) on s'integrarà aquesta pestanya.
        S'utilitza per fer load events en el dashboard global.
    """
    with gr.Tab("📍 Cobertura de Transport"):
        gr.Markdown(
            """
            # 🚇 Anàlisi del Sistema de Transport Metropolità de Barcelona
            Aquesta eina analitza la **cobertura** i **demanda potencial** de la xarxa de metro a Barcelona,
            creuant les dades de parades amb les de població per barris.
            
            Premeu el botó per executar l'anàlisi amb els fitxers XLSX proporcionats.
            """
        )
        
        with gr.Tabs():
            # ===== PESTAÑA 1: ANÁLISIS POR BARRIOS =====
            with gr.Tab("📊 Análisis por Barrios"):
                # State to store a dummy input for the button click
                dummy_input = gr.State(value=0)
                
                # Botó principal per executar l'anàlisi
                btn_run = gr.Button("Executar Anàlisi de Barris", variant="primary", size="lg")
                
                # Caixa de text per mostrar l'estat (èxit o error)
                status_box = gr.Textbox(label="Estat de l'Anàlisi", interactive=False)
                
                gr.Markdown("## Resultats de l'Anàlisi per Barris")
                
                # Sub-tabs para análisis de barrios
                with gr.Tabs():
                    # Barris amb més pressió
                    with gr.Tab("Barris amb Més Pressió de Demanda"):
                        gr.Markdown("Aquests barris tenen el ràtio més alt d'habitants per cada estació de metro. Són punts de potencial congestió.")
                        with gr.Row():
                            plot_pressure = gr.Plot(label="Top 10 Barris: Més Població per Estació")
                            data_pressure = gr.DataFrame(label="Dades: Barris amb Més Pressió")
                    
                    # Barris amb dèficit de cobertura
                    with gr.Tab("Barris amb Dèficit de Cobertura (Sense Metro)"):
                        gr.Markdown("Aquests són els barris més poblats que actualment no tenen cap estació de metro.")
                        with gr.Row():
                            plot_no_metro = gr.Plot(label="Top 10 Barris: Més Població SENSE Metro")
                            data_no_metro = gr.DataFrame(label="Dades: Barris Més Poblats Sense Metro")
                            
                    # Descàrrega del dataset complet
                    with gr.Tab("📥 Dataset Complet Resultant"):
                        gr.Markdown("Aquí podeu descarregar el fitxer CSV complet amb les dades dels 73 barris i els KPIs calculats.")
                        output_file = gr.File(label="Descarregar Dataset Complet (CSV)")

                # Connectar el botó a la funció
                btn_run.click(
                    fn=analyze_data,
                    inputs=dummy_input,
                    outputs=[
                        plot_pressure, 
                        data_pressure, 
                        plot_no_metro, 
                        data_no_metro, 
                        output_file, 
                        status_box
                    ]
                )
            
            # ===== PESTAÑA 2: ANÁLISIS POR DISTRITOS =====
            with gr.Tab("🏘️ Análisis por Distritos"):
                gr.Markdown(
                    """
                    ## Estacions de Metro per Districte
                    Visualiza la distribución de estaciones de metro por cada distrito de Barcelona.
                    """
                )
                
                # State for button
                dummy_input_dist = gr.State(value=0)
                
                # Button to run analysis
                btn_run_dist = gr.Button("Executar Anàlisi de Districtes", variant="primary", size="lg")
                
                # Status box
                status_box_dist = gr.Textbox(label="Estat de l'Anàlisi", interactive=False)
                
                # Row with both charts
                with gr.Row():
                    chart_barras = gr.Plot(label="Gràfic de Barres: Estacions per Districte")
                    chart_pie = gr.Plot(label="Gràfic Circular: Distribució per Districte")
                
                # Dataframe with data
                with gr.Row():
                    data_distritos = gr.DataFrame(label="Dades: Estacions per Districte")
                
                # Connect button to function
                btn_run_dist.click(
                    fn=analyze_estaciones_por_distrito,
                    inputs=dummy_input_dist,
                    outputs=[
                        chart_barras,
                        chart_pie,
                        data_distritos,
                        status_box_dist
                    ]
                )
            
            # ===== PESTAÑA 3: MAPA HEATMAP CON FOLIUM =====
            with gr.Tab("🗺️ Mapa de Calor por Distrito"):
                gr.Markdown(
                    """
                    ## Mapa Interactivo de Estaciones de Metro
                    Este mapa muestra la densidad de estaciones de metro por distrito:
                    - 🟡 **Amarillo**: Pocos estaciones
                    - 🟠 **Naranja**: Estaciones medias
                    - 🔴 **Rojo**: Muchas estaciones
                    
                    El tamaño del círculo también indica la cantidad de estaciones.
                    """
                )
                
                # State for button
                dummy_input_map = gr.State(value=0)
                
                # Button to create map
                btn_run_map = gr.Button("Crear Mapa de Calor", variant="primary", size="lg")
                
                # Status box
                status_box_map = gr.Textbox(label="Estat de la Creació", interactive=False)
                
                # Map output
                map_output = gr.File(label="📍 Descargar Mapa (HTML)")
                
                # HTML viewer for inline display
                map_html = gr.HTML(label="Vista previa del mapa")
                
                # Connect button to function
                btn_run_map.click(
                    fn=create_heatmap_distritos,
                    inputs=dummy_input_map,
                    outputs=[
                        map_output,
                        status_box_map
                    ]
                )


# --- 4. Definición de la Interfície de Gradio ---
# Executar directament si aquest és l'script principal
if __name__ == "__main__":
    with gr.Blocks(title="Anàlisi Transport BCN") as app:
        build_cobertura_tab()
    app.launch(share=False, inbrowser=False)
import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# --- 1. Definir noms de fitxers ---
# Fem servir els noms de fitxer exactes que existeixen al directori
FILE_POBLACIO = "Densitat Poblacio Barcelona 2021.xlsx"
FILE_TRANSPORT = "Transport Public Barcelona.xlsx"
OUTPUT_CSV = "analisis_transporte_poblacion.csv"

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
        
        # State to store a dummy input for the button click
        dummy_input = gr.State(value=0)
        
        # Botó principal per executar l'anàlisi
        btn_run = gr.Button("Executar Anàlisi", variant="primary", size="lg")
        
        # Caixa de text per mostrar l'estat (èxit o error)
        status_box = gr.Textbox(label="Estat de l'Anàlisi", interactive=False)
        
        gr.Markdown("## Resultats de l'Anàlisi")
        
        # Pestanya 1: Barris amb més pressió
        with gr.Tab("Barris amb Més Pressió de Demanda"):
            gr.Markdown("Aquests barris tenen el ràtio més alt d'habitants per cada estació de metro. Són punts de potencial congestió.")
            with gr.Row():
                plot_pressure = gr.Plot(label="Top 10 Barris: Més Població per Estació")
                data_pressure = gr.DataFrame(label="Dades: Barris amb Més Pressió")
        
        # Pestanya 2: Barris amb dèficit de cobertura
        with gr.Tab("Barris amb Dèficit de Cobertura (Sense Metro)"):
            gr.Markdown("Aquests són els barris més poblats que actualment no tenen cap estació de metro.")
            with gr.Row():
                plot_no_metro = gr.Plot(label="Top 10 Barris: Més Població SENSE Metro")
                data_no_metro = gr.DataFrame(label="Dades: Barris Més Poblats Sense Metro")
                
        # Pestanya 3: Descàrrega del dataset complet
        with gr.Tab("Dataset Complet Resultant"):
            gr.Markdown("Aquí podeu descarregar el fitxer CSV complet amb les dades dels 73 barris i els KPIs calculats.")
            output_file = gr.File(label="Descarregar Dataset Complet (CSV)")

        # --- 5. Connectar el botó a la funció ---
        # Defineix què passa quan es fa clic al botó
        btn_run.click(
            fn=analyze_data,  # La funció a executar
            inputs=dummy_input,      # Dummy input per permetre que el click funcioni
            outputs=[         # Els components de sortida on s'enviaran els resultats
                plot_pressure, 
                data_pressure, 
                plot_no_metro, 
                data_no_metro, 
                output_file, 
                status_box
            ]
        )


# --- 4. Definición de la Interfície de Gradio ---
# Executar directament si aquest és l'script principal
if __name__ == "__main__":
    with gr.Blocks(title="Anàlisi Transport BCN") as app:
        build_cobertura_tab()
    app.launch(share=False, inbrowser=False)
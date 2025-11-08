import gradio as gr
from demanda_dashboard import build_demanda_tab
# from otra_pestaña import build_otra_tab  # si quieres más pestañas

with gr.Blocks(title="📊 Dashboard Global", theme=gr.themes.Soft()) as main_dashboard:
    gr.Markdown("# 🧠 Dashboard Global de Análisis de Datos")
    gr.Markdown("Selecciona una pestaña para explorar los diferentes módulos de visualización:")

    with gr.Tabs():
        build_demanda_tab(main_dashboard)          # Pestaña 1: Demanda Metro Barcelona
        # build_otra_tab()           # Pestaña 2: otros análisis (por ejemplo, usuarios)

main_dashboard.launch()

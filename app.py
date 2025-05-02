import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os

firma_path = None
firmas_por_pagina = {}  # {número_pagina: [(x, y), ...]}

def seleccionar_firma():
    global firma_path
    firma_path = filedialog.askopenfilename(title="Selecciona la imagen de la firma", filetypes=[("Imagen", "*.png *.jpg *.jpeg")])
    return firma_path

def seleccionar_y_previsualizar_pdf():
    pdf_path = filedialog.askopenfilename(title="Selecciona un PDF de ejemplo", filetypes=[("PDF", "*.pdf")])
    if not pdf_path:
        return

    mostrar_previsualizacion(pdf_path)

def mostrar_previsualizacion(pdf_path):
    global firmas_por_pagina
    firmas_por_pagina = {}
    archivos_temporales = []
    sizes = {}


    def registrar_click(event):
        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)

        for i, (offset_y, altura) in enumerate(offsets):
            if offset_y <= y <= offset_y + altura:
                coord = (x, y - offset_y)
                if i not in firmas_por_pagina:
                    firmas_por_pagina[i] = []
                firmas_por_pagina[i].append(coord)
                draw_firma_preview(i, coord)
                break

    def draw_firma_preview(page_index, coord):
        marker = canvas.create_rectangle(
            coord[0]-5, offsets[page_index][0] + coord[1]-5,
            coord[0]+5, offsets[page_index][0] + coord[1]+5,
            outline='red', width=2
        )
        canvas.firma_markers.append(marker)

    def aplicar_firmas_y_cerrar():
        if not firmas_por_pagina:
            messagebox.showwarning("Aviso", "No se seleccionó ninguna posición para firmar.")
            return
        eliminar_temporales()
        top.destroy()
        aplicar_firma_en_lote(pdf_path, sizes)

    def eliminar_temporales():
        for archivo in archivos_temporales:
            if os.path.exists(archivo):
                os.remove(archivo)

    def cerrar_ventana():
        eliminar_temporales()
        top.destroy()

    # --- Ventana de previsualización ---
    top = tk.Toplevel(root)
    top.title("Selecciona dónde colocar las firmas")
    top.protocol("WM_DELETE_WINDOW", cerrar_ventana)

    doc = fitz.open(pdf_path)
    imagenes = []
    offsets = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        path = f"preview_page_{i}.png"
        pix.save(path)
        archivos_temporales.append(path)
        img = Image.open(path)
        imagenes.append(img)
        sizes[i] = img.size


    frame = tk.Frame(top)
    frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame, width=800, height=600)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    canvas.images = []
    canvas.firma_markers = []
    y_offset = 0
    for img in imagenes:
        tk_img = ImageTk.PhotoImage(img)
        canvas.create_image(0, y_offset, anchor=tk.NW, image=tk_img)
        canvas.images.append(tk_img)
        offsets.append((y_offset, img.height))
        y_offset += img.height

    canvas.config(scrollregion=canvas.bbox("all"))
    canvas.bind("<Button-1>", registrar_click)

    btn_aplicar = tk.Button(top, text="Aplicar firmas", command=aplicar_firmas_y_cerrar)
    btn_aplicar.pack(pady=10)

def aplicar_firma_en_lote(pdf_ejemplo_path, sizes):
    if not firma_path or not firmas_por_pagina:
        messagebox.showerror("Error", "Falta la imagen o las posiciones de firma.")
        return

    pdf_paths = filedialog.askopenfilenames(title="Selecciona los PDFs a firmar", filetypes=[("PDF", "*.pdf")])
    if not pdf_paths:
        return


    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)

        for page_index, coords in firmas_por_pagina.items():
            if page_index >= len(doc):
                messagebox.showwarning("Aviso", f"{pdf_path} tiene menos páginas que la {page_index + 1}.")
                continue

            page = doc.load_page(page_index)
            page_width, page_height = page.rect.width, page.rect.height
            img_width, img_height = sizes[page_index]

            scale_x = page_width / img_width
            scale_y = page_height / img_height

            for coord in coords:
                x0 = coord[0] * scale_x
                y0 = coord[1] * scale_y
                x1 = x0 + 150 * scale_x
                y1 = y0 + 50 * scale_y

                rect = fitz.Rect(x0, y0, x1, y1)
                page.insert_image(rect, filename=firma_path)

        # Guardar en carpeta "firmados" junto al original
        pdf_dir = os.path.dirname(pdf_path)
        output_folder = os.path.join(pdf_dir, "firmados")
        os.makedirs(output_folder, exist_ok=True)

        filename = os.path.basename(pdf_path)
        nuevo_nombre = filename.replace(".pdf", "_firmado.pdf")
        nuevo = os.path.join(output_folder, nuevo_nombre)
        doc.save(nuevo)
        doc.close()

    messagebox.showinfo("Éxito", "PDFs firmados correctamente.")

# Interfaz
root = tk.Tk()
root.title("Firmador de PDFs con Vista Previa")
root.geometry("350x180")

tk.Label(root, text="Paso 1: Selecciona la imagen de la firma").pack(pady=5)
tk.Button(root, text="Seleccionar Firma", command=seleccionar_firma).pack()

tk.Label(root, text="Paso 2: Selecciona PDF para vista previa").pack(pady=5)
tk.Button(root, text="Vista Previa PDF", command=seleccionar_y_previsualizar_pdf).pack()

root.mainloop()

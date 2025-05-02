import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz 
import os

firma_path = None
firmas_por_pagina = {}

def seleccionar_firma():
    global firma_path
    firma_path = filedialog.askopenfilename(title="Select signature image", filetypes=[("Image", "*.png *.jpg *.jpeg")])
    return firma_path

def seleccionar_y_previsualizar_pdf():
    pdf_path = filedialog.askopenfilename(title="Select a sample PDF", filetypes=[("PDF", "*.pdf")])
    if not pdf_path:
        return

    mostrar_previsualizacion(pdf_path)

def mostrar_previsualizacion(pdf_path):
    click_en_cruz = {"valor": False}

    global firmas_por_pagina
    firmas_por_pagina = {}
    archivos_temporales = []
    sizes = {}
    firma_seleccionada = {"id": None, "offset": (0, 0)}
    cruz_hover = None
    firma_imagenes = {}


    escala_firma = tk.DoubleVar(value=100)
    escala_firma.trace_add("write", lambda *args: redibujar_firmas())

    def manejar_hover(event):
        nonlocal cruz_hover
        x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)

        for fid, meta in firma_imagenes.items():
            fx, fy = meta["x"], meta["y"]
            fw = meta.get("w", 0)
            fh = meta.get("h", 0)

            if fx <= x <= fx + fw and fy <= y <= fy + fh:
                if cruz_hover:
                    canvas.delete(cruz_hover)

                cruz_id = canvas.create_text(fx + fw - 5, fy + 5, text="❌", fill="red", font=("Arial", 12, "bold"))
                firma_imagenes[fid]["cruz_id"] = cruz_id
                cruz_hover = cruz_id
                canvas.tag_bind(cruz_id, "<Button-1>", lambda e, fid=fid: click_en_cruz.update({"valor": True}) or borrar_firma(fid))
                return

        if cruz_hover:
            canvas.delete(cruz_hover)
            cruz_hover = None


    def borrar_firma(fid):
        nonlocal cruz_hover
        meta = firma_imagenes[fid]
        page = meta["pagina"]
        coord = meta["coord"]
        canvas.delete(fid)
        if cruz_hover:
            canvas.delete(cruz_hover)
        canvas.tk_firmas.remove(meta["img_ref"])
        firmas_por_pagina[page].remove(coord)
        del firma_imagenes[fid]

    def iniciar_arrastre(event):
        x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        for fid, meta in firma_imagenes.items():
            fx, fy = meta["x"], meta["y"]
            fw = meta.get("w", 0)
            fh = meta.get("h", 0)
            if fx <= x <= fx + fw and fy <= y <= fy + fh:
                firma_seleccionada["id"] = fid
                firma_seleccionada["offset"] = (x - fx, y - fy)
                break

    def mover_firma(event):
        fid = firma_seleccionada["id"]
        if fid is None:
            return

        x = canvas.canvasx(event.x) - firma_seleccionada["offset"][0]
        y = canvas.canvasy(event.y) - firma_seleccionada["offset"][1]

        canvas.coords(fid, x, y)

        cruz_id = firma_imagenes[fid].get("cruz_id")
        if cruz_id:
            w = firma_imagenes[fid]["w"]
            h = firma_imagenes[fid]["h"]
            canvas.coords(cruz_id, x + w - 5, y + 5)


    def soltar_firma(event):
        fid = firma_seleccionada["id"]
        if fid is None:
            return
        x = canvas.canvasx(event.x) - firma_seleccionada["offset"][0]
        y = canvas.canvasy(event.y) - firma_seleccionada["offset"][1]

        meta = firma_imagenes[fid]
        page = meta["pagina"]
        offset_y = offsets[page][0]
        nueva_coord = (x, y - offset_y)

        old_coord = meta["coord"]
        meta.update({"x": x, "y": y, "coord": nueva_coord}) 

        if old_coord in firmas_por_pagina[page]:
            index = firmas_por_pagina[page].index(old_coord)
            firmas_por_pagina[page][index] = nueva_coord

        firma_seleccionada["id"] = None



    def redibujar_firmas():
        for fid in list(firma_imagenes.keys()):
            canvas.delete(fid)
        canvas.tk_firmas.clear()
        firma_imagenes.clear()

        scale = escala_firma.get() / 100
        firma_img_base = Image.open(firma_path)
        new_size = (int(firma_img_base.width * scale), int(firma_img_base.height * scale))
        firma_img_resized = firma_img_base.resize(new_size, Image.Resampling.LANCZOS)

        for page_index, coords in firmas_por_pagina.items():
            for coord_rel in coords:
                x = coord_rel[0]
                y = coord_rel[1] + offsets[page_index][0]
                tk_firma = ImageTk.PhotoImage(firma_img_resized)
                img_id = canvas.create_image(x, y, anchor=tk.NW, image=tk_firma)
                canvas.tag_bind(img_id, "<ButtonPress-1>", iniciar_arrastre)
                canvas.tag_bind(img_id, "<B1-Motion>", mover_firma)
                canvas.tag_bind(img_id, "<ButtonRelease-1>", soltar_firma)
                canvas.tk_firmas.append(tk_firma)
                firma_imagenes[img_id] = {
                    "cruz_id": None,
                    "coord": coord_rel,
                    "pagina": page_index,
                    "x": x,
                    "y": y,
                    "w": new_size[0],
                    "h": new_size[1],
                    "img_ref": tk_firma
                }





    def registrar_click(event):
        if click_en_cruz["valor"]:
            click_en_cruz["valor"] = False
            return

        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)

        for fid, meta in list(firma_imagenes.items()):
            fx, fy = meta["x"], meta["y"]
            fw, fh = meta["w"], meta["h"]
            if fx <= x <= fx + fw and fy <= y <= fy + fh:
                return  

        for i, (offset_y, altura) in enumerate(offsets):
            if offset_y <= y <= offset_y + altura:
                coord_rel = (x, y - offset_y)

                if i not in firmas_por_pagina:
                    firmas_por_pagina[i] = []
                firmas_por_pagina[i].append(coord_rel)

                scale = escala_firma.get() / 100
                firma_img = Image.open(firma_path)
                new_size = (int(firma_img.width * scale), int(firma_img.height * scale))
                firma_img = firma_img.resize(new_size, Image.Resampling.LANCZOS)
                tk_firma = ImageTk.PhotoImage(firma_img)

                img_id = canvas.create_image(x, y, anchor=tk.NW, image=tk_firma)
                canvas.tag_bind(img_id, "<ButtonPress-1>", iniciar_arrastre)
                canvas.tag_bind(img_id, "<B1-Motion>", mover_firma)
                canvas.tag_bind(img_id, "<ButtonRelease-1>", soltar_firma)
                canvas.tk_firmas.append(tk_firma)
                firma_imagenes[img_id] = {
                    "cruz_id": None,
                    "coord": coord_rel,
                    "pagina": i,
                    "x": x,
                    "y": y,
                    "w": new_size[0],
                    "h": new_size[1],
                    "img_ref": tk_firma
                }
                break

    def aplicar_firmas_y_cerrar():
        if not firmas_por_pagina:
            messagebox.showwarning("Warning", "No signature positions selected.")
            return
        eliminar_temporales()
        top.destroy()
        aplicar_firma_en_lote(pdf_path, sizes, escala_firma.get())

    def eliminar_temporales():
        for archivo in archivos_temporales:
            if os.path.exists(archivo):
                os.remove(archivo)

    def cerrar_ventana():
        eliminar_temporales()
        top.destroy()

    top = tk.Toplevel(root)
    top.title("Select where to place the signatures")
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
    canvas.bind("<Motion>", manejar_hover)

    canvas.images = []
    canvas.tk_firmas = []
    y_offset = 0
    for img in imagenes:
        tk_img = ImageTk.PhotoImage(img)
        canvas.create_image(0, y_offset, anchor=tk.NW, image=tk_img)
        canvas.images.append(tk_img)
        offsets.append((y_offset, img.height))
        y_offset += img.height

    canvas.config(scrollregion=canvas.bbox("all"))
    canvas.bind("<Button-1>", registrar_click)

    tk.Label(top, text="Signature scale (%)").pack()
    tk.Scale(top, from_=10, to=300, orient="horizontal", variable=escala_firma).pack()

    tk.Button(top, text="Apply signatures", command=aplicar_firmas_y_cerrar).pack(pady=10)

def aplicar_firma_en_lote(pdf_ejemplo_path, sizes, escala_percent):
    if not firma_path or not firmas_por_pagina:
        messagebox.showerror("Error", "Missing signature image or positions.")
        return

    pdf_paths = filedialog.askopenfilenames(title="Select PDFs to sign", filetypes=[("PDF", "*.pdf")])
    if not pdf_paths:
        return

    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)

        for page_index, coords in firmas_por_pagina.items():
            if page_index >= len(doc):
                messagebox.showwarning("Warning", f"{pdf_path} has fewer pages than page {page_index + 1}.")
                continue

            page = doc.load_page(page_index)
            page_width, page_height = page.rect.width, page.rect.height
            img_width, img_height = sizes[page_index]

            scale_x = page_width / img_width
            scale_y = page_height / img_height

            firma_img = Image.open(firma_path)
            firma_width, firma_height = firma_img.size

            scale = escala_percent / 100
            firma_width_scaled = firma_width * scale
            firma_height_scaled = firma_height * scale

        for coord in coords:
            x0 = coord[0] * scale_x
            y0 = coord[1] * scale_y
            x1 = x0 + firma_width_scaled * scale_x
            y1 = y0 + firma_height_scaled * scale_y

            rect = fitz.Rect(x0, y0, x1, y1)
            page.insert_image(rect, filename=firma_path)


        pdf_dir = os.path.dirname(pdf_path)
        output_folder = os.path.join(pdf_dir, "signed")
        os.makedirs(output_folder, exist_ok=True)

        filename = os.path.basename(pdf_path)
        nuevo_nombre = filename.replace(".pdf", "_signed.pdf")
        nuevo = os.path.join(output_folder, nuevo_nombre)
        doc.save(nuevo)
        doc.close()

    messagebox.showinfo("Success", "PDFs signed successfully.")



root = tk.Tk()
root.title("PDF Signer with Preview")
root.geometry("350x180")

tk.Label(root, text="Step 1: Select signature image").pack(pady=5)
tk.Button(root, text="Select Signature", command=seleccionar_firma).pack()

tk.Label(root, text="Step 2: Select PDF for preview").pack(pady=5)
tk.Button(root, text="Preview PDF", command=seleccionar_y_previsualizar_pdf).pack()

root.mainloop()

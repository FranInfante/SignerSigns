import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os

firma_path = None
firma_coords = None  # (x, y) relativa a la página
pagina_seleccionada = None  # índice de la página donde se hizo clic

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
    def registrar_click(event):
        global firma_coords, pagina_seleccionada

        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)

        for i, (offset_y, altura) in enumerate(offsets):
            if offset_y <= y <= offset_y + altura:
                firma_coords = (x, y - offset_y)  # coordenada relativa a esa página
                pagina_seleccionada = i
                break

        top.destroy()
        aplicar_firma_en_lote(pdf_path)

    top = tk.Toplevel(root)
    top.title("Selecciona dónde colocar la firma")

    doc = fitz.open(pdf_path)
    imagenes = []
    offsets = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        path = f"preview_page_{i}.png"
        pix.save(path)
        img = Image.open(path)
        imagenes.append(img)

    frame = tk.Frame(top)
    frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame, width=800, height=600)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    canvas.images = []
    y_offset = 0
    for img in imagenes:
        tk_img = ImageTk.PhotoImage(img)
        canvas.create_image(0, y_offset, anchor=tk.NW, image=tk_img)
        canvas.images.append(tk_img)
        offsets.append((y_offset, img.height))
        y_offset += img.height

    canvas.config(scrollregion=canvas.bbox("all"))
    canvas.bind("<Button-1>", registrar_click)

def aplicar_firma_en_lote(pdf_ejemplo_path):
    if not firma_path or not firma_coords or pagina_seleccionada is None:
        messagebox.showerror("Error", "Falta la imagen, posición o página.")
        return

    pdf_paths = filedialog.askopenfilenames(title="Selecciona los PDFs a firmar", filetypes=[("PDF", "*.pdf")])
    if not pdf_paths:
        return

    # Cargar imagen preview de la página seleccionada
    preview_img = Image.open(f"preview_page_{pagina_seleccionada}.png")
    img_width, img_height = preview_img.size

    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)
        if pagina_seleccionada >= len(doc):
            messagebox.showwarning("Aviso", f"{pdf_path} tiene menos páginas que la seleccionada.")
            continue

        page = doc.load_page(pagina_seleccionada)
        page_width, page_height = page.rect.width, page.rect.height

        scale_x = page_width / img_width
        scale_y = page_height / img_height

        x0 = firma_coords[0] * scale_x
        y0 = firma_coords[1] * scale_y
        x1 = x0 + 150 * scale_x
        y1 = y0 + 50 * scale_y

        rect = fitz.Rect(x0, y0, x1, y1)
        page.insert_image(rect, filename=firma_path)

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

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz 
import os
from io import BytesIO

signature_path = None
signature_preview_label = None
signatures_by_page = {}

def select_signature():
    global signature_path, signature_preview_label

    signature_path = filedialog.askopenfilename(
        title="Select signature image",
        filetypes=[("Image", "*.png *.jpg *.jpeg")]
    )
    if signature_path:
        img = Image.open(signature_path)
        img.thumbnail((100, 100))  # Resize for preview
        tk_img = ImageTk.PhotoImage(img)

        if signature_preview_label:
            signature_preview_label.config(image=tk_img)
            signature_preview_label.image = tk_img  # Keep reference
        else:
            signature_preview_label = tk.Label(root, image=tk_img)
            signature_preview_label.image = tk_img
            signature_preview_label.pack(pady=5)
    return signature_path


def select_and_preview_pdf():
    if not signature_path:
        messagebox.showwarning("Firma no cargada", "Primero selecciona una imagen de firma.")
        return

    pdf_path = filedialog.askopenfilename(title="Select a sample PDF", filetypes=[("PDF", "*.pdf")])
    if not pdf_path:
        return

    show_preview(pdf_path)

def show_preview(pdf_path):
    delete_click = {"value": False}

    global signatures_by_page
    signatures_by_page = {}
    temp_files = []
    sizes = {}
    selected_signature = {"id": None, "offset": (0, 0)}
    delete_hover = None
    signature_images = {}

    signature_scale = tk.DoubleVar(value=100)
    signature_scale.trace_add("write", lambda *args: redraw_signatures())

    def handle_hover(event):
        nonlocal delete_hover
        x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)

        for sid, meta in signature_images.items():
            sx, sy = meta["x"], meta["y"]
            sw = meta.get("w", 0)
            sh = meta.get("h", 0)

            if sx <= x <= sx + sw and sy <= y <= sy + sh:
                if delete_hover:
                    canvas.delete(delete_hover)

                delete_id = canvas.create_text(sx + sw - 5, sy + 5, text="❌", fill="red", font=("Arial", 12, "bold"))
                signature_images[sid]["delete_id"] = delete_id
                delete_hover = delete_id
                canvas.tag_bind(delete_id, "<Button-1>", lambda e, sid=sid: delete_click.update({"value": True}) or delete_signature(sid))
                return

        if delete_hover:
            canvas.delete(delete_hover)
            delete_hover = None

    def delete_signature(sid):
        nonlocal delete_hover
        meta = signature_images[sid]
        page = meta["page"]
        coord = meta["coord"]
        canvas.delete(sid)
        if delete_hover:
            canvas.delete(delete_hover)
        canvas.tk_signatures.remove(meta["img_ref"])
        signatures_by_page[page].remove(coord)
        del signature_images[sid]

    def start_drag(event):
        x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        for sid, meta in signature_images.items():
            sx, sy = meta["x"], meta["y"]
            sw = meta.get("w", 0)
            sh = meta.get("h", 0)
            if sx <= x <= sx + sw and sy <= y <= sy + sh:
                selected_signature["id"] = sid
                selected_signature["offset"] = (x - sx, y - sy)
                break

    def move_signature(event):
        sid = selected_signature["id"]
        if sid is None:
            return

        x = canvas.canvasx(event.x) - selected_signature["offset"][0]
        y = canvas.canvasy(event.y) - selected_signature["offset"][1]

        canvas.coords(sid, x, y)

        delete_id = signature_images[sid].get("delete_id")
        if delete_id:
            w = signature_images[sid]["w"]
            h = signature_images[sid]["h"]
            canvas.coords(delete_id, x + w - 5, y + 5)

    def drop_signature(event):
        sid = selected_signature["id"]
        if sid is None:
            return
        x = canvas.canvasx(event.x) - selected_signature["offset"][0]
        y = canvas.canvasy(event.y) - selected_signature["offset"][1]

        meta = signature_images[sid]
        page = meta["page"]
        offset_y = offsets[page][0]
        new_coord = (x, y - offset_y)

        old_coord = meta["coord"]
        meta.update({"x": x, "y": y, "coord": new_coord}) 

        if old_coord in signatures_by_page[page]:
            index = signatures_by_page[page].index(old_coord)
            signatures_by_page[page][index] = new_coord

        selected_signature["id"] = None

    def redraw_signatures():
        for sid in list(signature_images.keys()):
            canvas.delete(sid)
        canvas.tk_signatures.clear()
        signature_images.clear()

        scale = signature_scale.get() / 100
        base_img = Image.open(signature_path)
        new_size = (int(base_img.width * scale), int(base_img.height * scale))
        resized_img = base_img.resize(new_size, Image.Resampling.LANCZOS)

        for page_index, coords in signatures_by_page.items():
            for rel_coord in coords:
                x = rel_coord[0]
                y = rel_coord[1] + offsets[page_index][0]
                tk_img = ImageTk.PhotoImage(resized_img)
                img_id = canvas.create_image(x, y, anchor=tk.NW, image=tk_img)
                canvas.tag_bind(img_id, "<ButtonPress-1>", start_drag)
                canvas.tag_bind(img_id, "<B1-Motion>", move_signature)
                canvas.tag_bind(img_id, "<ButtonRelease-1>", drop_signature)
                canvas.tk_signatures.append(tk_img)
                signature_images[img_id] = {
                    "delete_id": None,
                    "coord": rel_coord,
                    "page": page_index,
                    "x": x,
                    "y": y,
                    "w": new_size[0],
                    "h": new_size[1],
                    "img_ref": tk_img
                }

    def register_click(event):
        if delete_click["value"]:
            delete_click["value"] = False
            return

        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)

        for sid, meta in list(signature_images.items()):
            sx, sy = meta["x"], meta["y"]
            sw, sh = meta["w"], meta["h"]
            if sx <= x <= sx + sw and sy <= y <= sy + sh:
                return  

        for i, (offset_y, height) in enumerate(offsets):
            if offset_y <= y <= offset_y + height:
                rel_coord = (x, y - offset_y)

                if i not in signatures_by_page:
                    signatures_by_page[i] = []
                signatures_by_page[i].append(rel_coord)

                scale = signature_scale.get() / 100
                img = Image.open(signature_path)
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)

                img_id = canvas.create_image(x, y, anchor=tk.NW, image=tk_img)
                canvas.tag_bind(img_id, "<ButtonPress-1>", start_drag)
                canvas.tag_bind(img_id, "<B1-Motion>", move_signature)
                canvas.tag_bind(img_id, "<ButtonRelease-1>", drop_signature)
                canvas.tk_signatures.append(tk_img)
                signature_images[img_id] = {
                    "delete_id": None,
                    "coord": rel_coord,
                    "page": i,
                    "x": x,
                    "y": y,
                    "w": new_size[0],
                    "h": new_size[1],
                    "img_ref": tk_img
                }
                break

    def apply_and_close():
        if not signatures_by_page:
            messagebox.showwarning("Warning", "No signature positions selected.")
            return
        delete_temp_files()
        top.destroy()
        apply_signature_batch(pdf_path, sizes, signature_scale.get())

    def delete_temp_files():
        for file in temp_files:
            if os.path.exists(file):
                os.remove(file)

    def close_window():
        delete_temp_files()
        top.destroy()

    top = tk.Toplevel(root)
    top.title("Select where to place the signatures")
    top.protocol("WM_DELETE_WINDOW", close_window)

    doc = fitz.open(pdf_path)
    images = []
    offsets = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        path = f"preview_page_{i}.png"
        pix.save(path)
        temp_files.append(path)
        img = Image.open(path)
        images.append(img)
        sizes[i] = img.size

    frame = tk.Frame(top)
    frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame, width=800, height=600)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    canvas.bind("<Motion>", handle_hover)

    canvas.images = []
    canvas.tk_signatures = []
    y_offset = 0
    for img in images:
        tk_img = ImageTk.PhotoImage(img)
        canvas.create_image(0, y_offset, anchor=tk.NW, image=tk_img)
        canvas.images.append(tk_img)
        offsets.append((y_offset, img.height))
        y_offset += img.height

    canvas.config(scrollregion=canvas.bbox("all"))
    canvas.bind("<Button-1>", register_click)

    tk.Label(top, text="Signature scale (%)").pack()
    tk.Scale(top, from_=10, to=300, orient="horizontal", variable=signature_scale).pack()

    tk.Button(top, text="Apply signatures", command=apply_and_close).pack(pady=10)

def apply_signature_batch(example_pdf_path, sizes, scale_percent):
    if not signature_path or not signatures_by_page:
        messagebox.showerror("Error", "Missing signature image or positions.")
        return

    pdf_paths = filedialog.askopenfilenames(title="Select PDFs to sign", filetypes=[("PDF", "*.pdf")])
    if not pdf_paths:
        return

    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)

        for page_index, coords in signatures_by_page.items():
            if page_index >= len(doc):
                messagebox.showwarning("Warning", f"{pdf_path} has fewer pages than page {page_index + 1}.")
                continue

            page = doc.load_page(page_index)
            page_width, page_height = page.rect.width, page.rect.height
            img_width, img_height = sizes[page_index]

            scale_x = page_width / img_width
            scale_y = page_height / img_height

            signature_img = Image.open(signature_path)
            signature_width, signature_height = signature_img.size

            scale = scale_percent / 100
            signature_width_scaled = signature_width * scale
            signature_height_scaled = signature_height * scale

            rotation = page.rotation  # Detect actual page rotation

            for coord in coords:
                cx, cy = coord
                x0 = y0 = x1 = y1 = 0

                if rotation == 0:
                    x0 = cx * scale_x
                    y0 = cy * scale_y
                    x1 = x0 + signature_width_scaled * scale_x
                    y1 = y0 + signature_height_scaled * scale_y

                elif rotation == 90:
                    x0 = cy * scale_y
                    y0 = page_width - (cx * scale_x + signature_width_scaled * scale_x)
                    x1 = x0 + signature_height_scaled * scale_y
                    y1 = y0 + signature_width_scaled * scale_x

                elif rotation == 180:
                    x0 = page_width - (cx * scale_x + signature_width_scaled * scale_x)
                    y0 = page_height - (cy * scale_y + signature_height_scaled * scale_y)
                    x1 = x0 + signature_width_scaled * scale_x
                    y1 = y0 + signature_height_scaled * scale_y

                elif rotation == 270:
                    x0 = page_height - (cy * scale_y + signature_height_scaled * scale_y)
                    y0 = cx * scale_x
                    x1 = x0 + signature_height_scaled * scale_y
                    y1 = y0 + signature_width_scaled * scale_x

                rect = fitz.Rect(x0, y0, x1, y1)
                signature_img = Image.open(signature_path)

                # Rotate according to page orientation
                if rotation == 90:
                    signature_img = signature_img.rotate(90, expand=True)
                elif rotation == 180:
                    signature_img = signature_img.rotate(180, expand=True)
                elif rotation == 270:
                    signature_img = signature_img.rotate(-270, expand=True)

                # Save rotated image temporarily in memory
                img_bytes = BytesIO()
                signature_img.save(img_bytes, format="PNG")
                img_bytes.seek(0)

                page.insert_image(rect, stream=img_bytes)

        pdf_dir = os.path.dirname(pdf_path)
        output_folder = os.path.join(pdf_dir, "signed")
        os.makedirs(output_folder, exist_ok=True)

        filename = os.path.basename(pdf_path)
        new_name = filename.replace(".pdf", "_signed.pdf")
        new_path = os.path.join(output_folder, new_name)
        doc.save(new_path)
        doc.close()

    messagebox.showinfo("Success", "PDFs signed successfully.")

root = tk.Tk()
root.title("PDF Signer with Preview")
root.geometry("800x600")

main_frame = tk.Frame(root, bg="#e0e0e0", padx=20, pady=20)
main_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

tk.Label(main_frame, text="Step 1: Select signature image", font=("Arial", 12)).grid(row=0, column=0, pady=(0, 5), sticky="w")

tk.Button(main_frame, text="Select Signature", command=select_signature, width=20).grid(row=1, column=0, pady=(0, 15))

tk.Label(main_frame, text="Step 2: Select PDF for preview", font=("Arial", 12)).grid(row=2, column=0, pady=(0, 5), sticky="w")

tk.Button(main_frame, text="Preview PDF", command=select_and_preview_pdf, width=20).grid(row=3, column=0, pady=(0, 15))

from PIL import ImageDraw

placeholder_img = Image.new("RGB", (100, 60), color="#cccccc")
draw = ImageDraw.Draw(placeholder_img)
draw.text((10, 20), "Sign not\nloaded", fill="black")

placeholder_tk_img = ImageTk.PhotoImage(placeholder_img)

signature_preview_label = tk.Label(main_frame, image=placeholder_tk_img)
signature_preview_label.image = placeholder_tk_img  
signature_preview_label.grid(row=4, column=0, pady=(10, 0))



root.mainloop()

# 🖊️ Signs – Firma PDFs fácilmente

Aplicación de escritorio que permite firmar documentos PDF visualmente con tu propia firma arrastrable.

## 📦 Descargas

| Sistema Operativo | Enlace de descarga |
|-------------------|--------------------|
| 🐧 Linux           | [Descargar signs-linux](https://github.com/FranInfante/SignerSigns/releases/download/1.0/signs-linux) |
| 🪟 Windows         | [Descargar signs-windows.exe](https://github.com/FranInfante/SignerSigns/releases/download/1.0/signs-windows) |

## 🚀 Cómo usar

### Linux

1. Abre terminal y da permisos de ejecución:
  
   chmod +x signs-linux
   ./signs-linux


### Windows

1. Haz doble clic en `signs-windows.exe`.


## 🛠️ Requisitos si deseas compilarlo tú mismo

1. Instala las dependencias:

   pip install -r requirements.txt

2. Genera el ejecutable:

   pyinstaller --onefile --windowed app.py

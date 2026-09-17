# -*- coding: utf-8 -*-
import os
import sys

# _sip_lazy_imports.py
# Ağır kütüphaneler lazy yüklenir - uygulama başlarken PyTorch vb.
# yükleyerek UI'yi dondururlardı. Bunun yerine ilk parse çağrısında yüklenir.

_pd = None               # pandas
_Image = None            # PIL.Image
_ImageFilter = None
_ImageOps = None
_QPdfDocument = None     # PyQt6.QtPdf

_pdfplumber = None
_pytesseract = None

_easyocr_module = None
_easyocr_reader = None
_easyocr_reader_failed = False


def _ensure_module(name):
    """Belirli bir modülü ihtiyaca göre yükle."""
    global _pd, _Image, _ImageFilter, _ImageOps, _QPdfDocument
    global _pdfplumber, _pytesseract, _easyocr_module

    if name == "pd" and _pd is None:
        import pandas as _pd_tmp
        _pd = _pd_tmp
    
    elif name == "PIL" and _Image is None:
        try:
            from PIL import Image as _Img, ImageFilter as _IF, ImageOps as _IO
            _Image = _Img
            _ImageFilter = _IF
            _ImageOps = _IO
        except ImportError:
            _Image = False

    elif name == "pdf" and _QPdfDocument is None:
        try:
            from PyQt6.QtPdf import QPdfDocument as _QPdf
            _QPdfDocument = _QPdf
        except Exception:
            _QPdfDocument = False

    elif name == "pdfplumber" and _pdfplumber is None:
        try:
            import pdfplumber as _pdfp
            _pdfplumber = _pdfp
        except ImportError:
            _pdfplumber = False

    elif name == "pytesseract" and _pytesseract is None:
        try:
            import pytesseract as _tess
            tesseract_path = os.path.join(
                os.path.dirname(sys.executable), "Tesseract-OCR", "tesseract.exe"
            )
            if os.path.isfile(tesseract_path):
                _tess.pytesseract.tesseract_cmd = tesseract_path
            _pytesseract = _tess
        except ImportError:
            _pytesseract = False

    elif name == "easyocr" and _easyocr_module is None:
        try:
            import easyocr as _easy
            _easyocr_module = _easy
        except (ImportError, OSError, Exception):
            _easyocr_module = False


# Getter fonksiyonları
def get_pd():
    _ensure_module("pd")
    return _pd

def get_Image():
    _ensure_module("PIL")
    return _Image

def get_ImageFilter():
    _ensure_module("PIL")
    return _ImageFilter

def get_ImageOps():
    _ensure_module("PIL")
    return _ImageOps

def get_QPdfDocument():
    _ensure_module("pdf")
    return _QPdfDocument

def get_pdfplumber():
    _ensure_module("pdfplumber")
    return _pdfplumber

def get_pytesseract():
    _ensure_module("pytesseract")
    return _pytesseract


def _get_easyocr_reader():
    global _easyocr_reader, _easyocr_reader_failed, _easyocr_module
    if _easyocr_module is False or _easyocr_reader_failed:
        return None
    
    if _easyocr_module is None:
        _ensure_module("easyocr")
    
    if _easyocr_module is False or _easyocr_reader_failed:
        return None
    
    if _easyocr_reader is None:
        try:
            _easyocr_reader = _easyocr_module.Reader(["tr", "en"], gpu=False, verbose=False)
        except Exception:
            _easyocr_reader_failed = True
            _easyocr_reader = None
    return _easyocr_reader


# Geriye dönük uyumluluk için eski isimler (getter fonksiyonları ile)
def __getattr__(name):
    if name == "pd":
        return get_pd()
    elif name == "Image":
        return get_Image()
    elif name == "ImageFilter":
        return get_ImageFilter()
    elif name == "ImageOps":
        return get_ImageOps()
    elif name == "QPdfDocument":
        return get_QPdfDocument()
    elif name == "pdfplumber":
        return get_pdfplumber()
    elif name == "pytesseract":
        return get_pytesseract()
    elif name == "get_easyocr_reader":
        return _get_easyocr_reader
    raise AttributeError(f"module {__name__} has no attribute {name}")


def _ensure_heavy_imports():
    """
    Ağır kütüphaneleri (pandas, PIL, pdfplumber vb.) toplu olarak lazy yükler.
    stock_import_parser.parse_file() tarafından ilk parse çağrısında tetiklenir.
    """
    _ensure_module("pd")
    _ensure_module("PIL")
    _ensure_module("pdf")
    _ensure_module("pdfplumber")
    _ensure_module("pytesseract")

# DejaVu Sans Font Installation

## Required for Turkish PDF Support

The application requires DejaVu Sans TrueType fonts to properly render Turkish characters (ğ, ü, ş, ı, ö, ç) in PDF documents.

## Download Instructions

### Option 1: Direct Download (Recommended)

1. Visit: <https://dejavu-fonts.github.io/Download.html>
2. Download: **dejavu-fonts-ttf-2.37.zip** (or latest version)
3. Extract the ZIP file
4. Copy these 4 files to `c:\Users\Admin\Desktop\Hesap programı\fonts\`:
   - `DejaVuSans.ttf`
   - `DejaVuSans-Bold.ttf`
   - `DejaVuSans-Oblique.ttf`
   - `DejaVuSans-BoldOblique.ttf`

### Option 2: GitHub

1. Visit: <https://github.com/dejavu-fonts/dejavu-fonts/releases>
2. Download latest release (ttf package)
3. Extract and copy the 4 files listed above

## Verification

After copying the fonts, the `fonts` directory should contain:

```
fonts/
├── DejaVuSans.ttf
├── DejaVuSans-Bold.ttf
├── DejaVuSans-Oblique.ttf
└── DejaVuSans-BoldOblique.ttf
```

## Testing

Run this Python code to verify fonts are accessible:

```python
from src.utils.pdf_helper import TurkishPDFHelper

try:
    TurkishPDFHelper.register_fonts()
    print("✓ Fonts registered successfully!")
except Exception as e:
    print(f"✗ Error: {e}")
```

## License

DejaVu Fonts are licensed under a Free license, allowing commercial use.
Full license: <https://dejavu-fonts.github.io/License.html>

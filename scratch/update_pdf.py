"""
Update Weekly_Time_Management_Plan_UPDATED.pdf using PyMuPDF (fitz).
"""

import pymupdf

pdf_path = r"C:\Knowledge-Base\docs\Weekly_Time_Management_Plan_UPDATED.pdf"
doc = pymupdf.open(pdf_path)
page = doc[0]

# 1. Tue 9:00 AM -> ICC-600 ONLINE CLASS
# Rect(236.78, 172.92, 289.80, 181.29)
r_tue = pymupdf.Rect(200, 168, 292, 195)
page.draw_rect(r_tue, color=None, fill=(0.95, 0.96, 0.98)) # light cell background or white
page.insert_textbox(r_tue, "ICC-600\nONLINE CLASS\n9:00–10:00", fontsize=7.5, fontname="helv", align=pymupdf.TEXT_ALIGN_CENTER, color=(0.1, 0.2, 0.4))

# 2. Mon 1:00 PM -> BAT-600 ONLINE CLASS
r_mon = pymupdf.Rect(108, 276, 200, 303)
page.draw_rect(r_mon, color=None, fill=(0.95, 0.96, 0.98))
page.insert_textbox(r_mon, "BAT-600\nONLINE CLASS\n1:00–2:00", fontsize=7.5, fontname="helv", align=pymupdf.TEXT_ALIGN_CENTER, color=(0.1, 0.2, 0.4))

# 3. Wed 1:00 PM -> BAT-600 ONLINE CLASS
r_wed = pymupdf.Rect(294, 276, 386, 303)
page.draw_rect(r_wed, color=None, fill=(0.95, 0.96, 0.98))
page.insert_textbox(r_wed, "BAT-600\nONLINE CLASS\n1:00–2:00", fontsize=7.5, fontname="helv", align=pymupdf.TEXT_ALIGN_CENTER, color=(0.1, 0.2, 0.4))

temp_pdf = pdf_path + ".tmp"
doc.save(temp_pdf)
doc.close()

import shutil
shutil.move(temp_pdf, pdf_path)
print(f"Successfully updated PDF: {pdf_path}")

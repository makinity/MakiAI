"""
Render pixel-perfect Weekly_Time_Management_Plan_UPDATED.pdf via Chrome Headless.
"""

import os
import subprocess
from pathlib import Path

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: letter landscape;
    margin: 0.5in;
  }
  body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #111827;
    margin: 0;
    padding: 0;
    background: #fff;
  }
  .header {
    margin-bottom: 8px;
  }
  .title {
    font-size: 14pt;
    font-weight: 800;
    letter-spacing: 0.5px;
    margin: 0;
    color: #111827;
  }
  .subtitle {
    font-size: 9pt;
    color: #4b5563;
    margin-top: 2px;
    margin-bottom: 4px;
    font-weight: 500;
  }
  .priority {
    font-size: 8.5pt;
    font-weight: 700;
    color: #1f2937;
    background: #f3f4f6;
    padding: 3px 8px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 8px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 7.5pt;
    table-layout: fixed;
  }
  th, td {
    border: 1px solid #9ca3af;
    padding: 3px 4px;
    text-align: center;
    vertical-align: middle;
    word-wrap: break-word;
    line-height: 1.15;
  }
  th {
    background-color: #f9fafb;
    font-weight: 700;
    font-size: 8pt;
    padding: 4px 2px;
  }
  th.time-col, td.time-col {
    width: 10%;
    font-weight: 700;
    background-color: #f9fafb;
  }
  .online-class {
    font-weight: 700;
  }
  .f2f-class {
    font-weight: 700;
  }
</style>
</head>
<body>

<div class="header">
  <div class="title">MY WEEKLY SCHEDULE & TIME MANAGEMENT PLAN</div>
  <div class="subtitle">Balance &bull; Work &bull; School &bull; Growth &bull; Life</div>
  <div class="priority">DAILY PRIORITY ORDER: 1. Part-time Content Work (1 hr) &rarr; 2. School &rarr; 3. Job Hunting &rarr; 4. Coding &rarr; 5. Gaming / Leisure</div>
</div>

<table>
  <thead>
    <tr>
      <th class="time-col">Time</th>
      <th>Monday</th>
      <th>Tuesday</th>
      <th>Wednesday</th>
      <th>Thursday</th>
      <th>Friday</th>
      <th>Saturday</th>
      <th>Sunday</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="time-col">8:00–9:00</td>
      <td>Morning routine</td>
      <td>Morning routine</td>
      <td>Morning routine</td>
      <td>Morning routine</td>
      <td>Morning routine / plan</td>
      <td>Wake / breakfast</td>
      <td>Wake / breakfast</td>
    </tr>
    <tr>
      <td class="time-col">9:00–10:00</td>
      <td>Content Work<br>(1 hr)</td>
      <td class="online-class">ICC-600<br>ONLINE CLASS<br>9:00–10:00</td>
      <td>Content Work<br>(1 hr)</td>
      <td>Content Work<br>(1 hr)</td>
      <td>Content Work<br>(1 hr)</td>
      <td>Content Work<br>(1 hr)</td>
      <td>Weekly planning / review</td>
    </tr>
    <tr>
      <td class="time-col">10:00–11:00</td>
      <td>Job Hunting</td>
      <td>Content Work</td>
      <td>Job Hunting</td>
      <td>Job Hunting</td>
      <td>Job Hunting</td>
      <td>Free time / personal</td>
      <td>Optional school catch-up</td>
    </tr>
    <tr>
      <td class="time-col">11:00–12:00</td>
      <td>Job Hunting</td>
      <td>Job Hunting</td>
      <td>Job Hunting</td>
      <td>Job Hunting</td>
      <td>Job Hunting</td>
      <td>Free time / personal</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">12:00–1:00</td>
      <td>Lunch / break</td>
      <td>Lunch / break</td>
      <td>Lunch / break</td>
      <td>Lunch / break</td>
      <td>Lunch / break</td>
      <td>Lunch / break</td>
      <td>Lunch / break</td>
    </tr>
    <tr>
      <td class="time-col">1:00–2:00</td>
      <td class="online-class">BAT-600<br>ONLINE CLASS<br>1:00–2:00</td>
      <td>Free time / personal</td>
      <td class="online-class">BAT-600<br>ONLINE CLASS<br>1:00–2:00</td>
      <td>Coding</td>
      <td>Job Hunting</td>
      <td>Coding</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">2:00–3:00</td>
      <td>Break / rest</td>
      <td>Prepare / travel</td>
      <td>Break / rest</td>
      <td>Prepare / travel</td>
      <td>Job Hunting</td>
      <td>Coding</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">3:00–4:00</td>
      <td>Job Hunting</td>
      <td class="f2f-class">F2F CLASS<br>2:30–4:00</td>
      <td>Coding</td>
      <td class="f2f-class">F2F CLASS<br>2:30–4:00</td>
      <td>Coding</td>
      <td>Break</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">4:00–5:00</td>
      <td>Coding</td>
      <td>Travel / rest</td>
      <td>Coding</td>
      <td>Travel / rest</td>
      <td>Coding</td>
      <td>Job Hunting</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">5:00–6:00</td>
      <td>Coding</td>
      <td>Job Hunting</td>
      <td>Job Hunting</td>
      <td>Coding</td>
      <td>Coding</td>
      <td>Job Hunting / catch-up</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">6:00–7:00</td>
      <td>Exercise / walk</td>
      <td>Exercise / walk</td>
      <td>Exercise / walk</td>
      <td>Exercise / walk</td>
      <td>Exercise / walk</td>
      <td>Exercise / walk</td>
      <td>Exercise / walk</td>
    </tr>
    <tr>
      <td class="time-col">7:00–8:00</td>
      <td>Dinner / break</td>
      <td>Dinner / break</td>
      <td>Dinner / break</td>
      <td>Dinner / break</td>
      <td>Dinner / break</td>
      <td>Dinner / break</td>
      <td>Dinner / break</td>
    </tr>
    <tr>
      <td class="time-col">8:00–9:00</td>
      <td>Gaming / free time</td>
      <td>Coding / light work</td>
      <td>Gaming / free time</td>
      <td>Gaming / free time</td>
      <td>Gaming night</td>
      <td>Gaming / free time</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">9:00–10:00</td>
      <td>Gaming / free time</td>
      <td>Gaming / free time</td>
      <td>Gaming / free time</td>
      <td>Gaming / free time</td>
      <td>Gaming night</td>
      <td>Gaming / free time</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">10:00–11:00</td>
      <td>Gaming / free time</td>
      <td>Gaming / free time</td>
      <td>Gaming / free time</td>
      <td>Gaming / free time</td>
      <td>Gaming night</td>
      <td>Gaming / free time</td>
      <td>Free time / relax</td>
    </tr>
    <tr>
      <td class="time-col">11:00–12:00</td>
      <td>Wind down</td>
      <td>Wind down</td>
      <td>Wind down</td>
      <td>Wind down</td>
      <td>Wind down</td>
      <td>Wind down</td>
      <td>Wind down</td>
    </tr>
    <tr>
      <td class="time-col">12:00 AM</td>
      <td>SLEEP</td>
      <td>SLEEP</td>
      <td>SLEEP</td>
      <td>SLEEP</td>
      <td>SLEEP</td>
      <td>SLEEP</td>
      <td>SLEEP</td>
    </tr>
  </tbody>
</table>

</body>
</html>
"""

html_file = Path(r"c:\development\Python\MakiAI\scratch\schedule_print.html")
html_file.write_text(html_content, encoding="utf-8")

pdf_path = Path(r"C:\Knowledge-Base\docs\Weekly_Time_Management_Plan_UPDATED.pdf")

chrome_candidates = [
    Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google\\Chrome\\Application\\chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google\\Chrome\\Application\\chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google\\Chrome\\Application\\chrome.exe",
]

chrome_exe = None
for cand in chrome_candidates:
    if cand.exists():
        chrome_exe = cand
        break

if chrome_exe:
    cmd = [
        str(chrome_exe),
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path}",
        f"file:///{html_file.resolve().as_posix()}"
    ]
    subprocess.run(cmd, check=True)
    print(f"Successfully generated pristine PDF at {pdf_path}")
else:
    print("Chrome not found for PDF rendering")

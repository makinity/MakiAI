import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.settings.settings_service import SettingsService
from services.kb.kb_reader import KBReader
from services.kb.kb_writer import KBWriter

s = SettingsService()
kb_path = s.get_kb_path()
reader = KBReader(kb_path)
writer = KBWriter(kb_path)

print(f"Updating Knowledge Base at {kb_path}...")

# 1. Update/Create school/subjects/bat-600/README.md
bat600_content = """# BAT 600

> **Subject:** BAT 600 — Business Applications Technology
> **Semester:** 1st Semester A.Y. 2026-2027
> **Schedule:** Monday & Wednesday, 1:00 PM – 2:00 PM (Online Class)
> **Google Meet:** [https://meet.google.com/thb-fnkf-ksm?authuser=0](https://meet.google.com/thb-fnkf-ksm?authuser=0)
> **Google Classroom:** [https://classroom.google.com/c/ODcyMzA4MDEzNTYx](https://classroom.google.com/c/ODcyMzA4MDEzNTYx)

## Overview

BAT 600 focuses on enterprise business application technologies, system integrations, and practical workflows.

## Class Links & Resources

- **Google Meet:** [https://meet.google.com/thb-fnkf-ksm?authuser=0](https://meet.google.com/thb-fnkf-ksm?authuser=0)
- **Google Classroom:** [https://classroom.google.com/c/ODcyMzA4MDEzNTYx](https://classroom.google.com/c/ODcyMzA4MDEzNTYx)
- **Facebook Group / Messenger:** Direct browser session

## Current Status

- [ ] Attend Mon/Wed Online sessions (1:00 PM - 2:00 PM)
- [ ] Submit weekly modules and lab activities on Google Classroom
"""
writer.write("school/subjects/bat-600/README.md", bat600_content)
print("Updated school/subjects/bat-600/README.md")

# 2. Update school/subjects/icc-600/README.md
icc600_content = """# ICC 600

> **Subject:** ICC 600 — Core Information Technology
> **Semester:** 1st Semester A.Y. 2026-2027
> **Schedule:**
>   - **Online Class:** Tuesday & Thursday, 9:00 AM – 10:00 AM
>   - **Face-to-Face Class:** Tuesday & Thursday, 2:30 PM – 4:00 PM
> **Google Meet:** [https://meet.google.com/uzw-xxgo-gzx?authuser=0](https://meet.google.com/uzw-xxgo-gzx?authuser=0)
> **Google Classroom:** [https://classroom.google.com/c/ODc0NzE2NDgxNTYw](https://classroom.google.com/c/ODc0NzE2NDgxNTYw)

## Overview

Core information technology curriculum covering advanced architectures, practical system implementations, and software development.

## Class Links & Resources

- **Google Meet:** [https://meet.google.com/uzw-xxgo-gzx?authuser=0](https://meet.google.com/uzw-xxgo-gzx?authuser=0)
- **Google Classroom:** [https://classroom.google.com/c/ODc0NzE2NDgxNTYw](https://classroom.google.com/c/ODc0NzE2NDgxNTYw)
- **Development Tool:** Visual Studio Code (`code`)

## Current Status

- [ ] Attend Tue/Thu Online Class (9:00 AM - 10:00 AM)
- [ ] Attend Tue/Thu Face-to-Face Class (2:30 PM - 4:00 PM)
- [ ] Complete weekly programming deliverables
"""
writer.write("school/subjects/icc-600/README.md", icc600_content)
print("Updated school/subjects/icc-600/README.md")

# 3. Update workflows/time-management.md
current_tm = reader.read("workflows/time-management.md")
if current_tm:
    # Ensure BAT-600 and ICC-600 are explicitly stated in schedule
    updated_tm = current_tm.replace("ONLINE CLASS 1:00–2:00", "BAT-600 ONLINE CLASS 1:00–2:00")
    updated_tm = updated_tm.replace("ONLINE CLASS 9:00–10:00", "ICC-600 ONLINE CLASS 9:00–10:00")
    writer.write("workflows/time-management.md", updated_tm)
    print("Updated workflows/time-management.md")

# 4. Update va/work/Astra AI/README.md with direct operational links
current_astra = reader.read("va/work/Astra AI/README.md")
if current_astra and "## Direct Account & Workspace Links" not in current_astra:
    account_section = """
------------------------------------------------------------------------

## Direct Account & Workspace Links

- **Chrome Profile Email:** `astra.chile.xuiie@gmail.com` (Chrome `Profile 64`)
- **Metricool Analytics & Scheduler:** [https://app.metricool.com/evolution/instagram?blogId=6895147&userId=5311033](https://app.metricool.com/evolution/instagram?blogId=6895147&userId=5311033)
- **Facebook Page:** [https://www.facebook.com/studymodegreek/](https://www.facebook.com/studymodegreek/)
- **Instagram Profile:** [https://www.instagram.com/studymodegr/](https://www.instagram.com/studymodegr/)
- **YouTube Channel:** [https://www.youtube.com/@studymodegr](https://www.youtube.com/@studymodegr)
- **Astra AI Creator Stats Dashboard:** [https://creators.astra-ai.co/dashboard/stats](https://creators.astra-ai.co/dashboard/stats)
- **ChatGPT Workspace:** [https://chatgpt.com](https://chatgpt.com)
"""
    updated_astra = current_astra.rstrip() + "\n" + account_section
    writer.write("va/work/Astra AI/README.md", updated_astra)
    print("Updated va/work/Astra AI/README.md")

# 5. Update career/clients.md
current_clients = reader.read("career/clients.md")
if current_clients and "astra.chile.xuiie@gmail.com" not in current_clients:
    client_info = """
### Astra AI (StudyMode Greece)
- **Role:** Content Upload Assistant & Social Media Marketing
- **Assigned Account Email:** `astra.chile.xuiie@gmail.com` (Chrome `Profile 64`)
- **Schedule:** Monday – Saturday @ 9:00 AM – 10:00 AM
- **Target Market:** Greece (StudyMode GR)
- **Dashboards:**
  - Metricool: `https://app.metricool.com/evolution/instagram?blogId=6895147&userId=5311033`
  - Facebook: `https://www.facebook.com/studymodegreek/`
  - Instagram: `https://www.instagram.com/studymodegr/`
  - YouTube: `https://www.youtube.com/@studymodegr`
  - Creator Stats: `https://creators.astra-ai.co/dashboard/stats`
"""
    updated_clients = current_clients.rstrip() + "\n" + client_info
    writer.write("career/clients.md", updated_clients)
    print("Updated career/clients.md")

print("All Knowledge Base documents synchronized successfully!")

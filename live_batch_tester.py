"""
MakiAI Live Interactive Batch QA Tester
Executes prompts directly against full MakiAI stack with real OS execution.
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from main import bootstrap_maki_services

BATCHES = {
    1: ("Window Management, Inter-Monitor Dragging & Auto-Tiling", [
        "tile my windows",
        "organize my workspace",
        "drag this window to monitor 2",
        "move Chrome to the main screen",
    ]),
    2: ("Optical Camera Capture & Contextual Screen Vision", [
        "take a photo",
        "look at me and tell me what i am doing",
        "look at my screen and summarize this",
    ]),
    3: ("Desktop App Control, Process Management & Smart File Search", [
        "open notepad",
        "search my files for resume",
        "open my screenshots folder",
        "close notepad",
    ]),
    4: ("Media Controls & YouTube Playback", [
        "play lofi hip hop on youtube",
        "set volume to 60 percent",
        "mute audio",
        "unmute audio",
    ]),
    5: ("Filesystem Operations, File Creation & Fast Access", [
        "create a file named notes.txt with text Meeting tomorrow at 3pm",
        "open notes.txt",
        "delete file notes.txt",
    ]),
    6: ("Skills, Routine Workspaces, Dynamic Memory & Cloud Inboxes", [
        "Good morning Maki",
        "Prepare for my client work",
        "Tandaan mo na paborito kong coffee is Iced Caramel Macchiato",
        "What is my favorite coffee?",
        "Check my latest emails on Gmail",
        "Check my messages on Facebook",
    ]),
}

def run_batch(batch_num: int):
    if batch_num not in BATCHES:
        print(f"Unknown batch {batch_num}")
        return

    name, prompts = BATCHES[batch_num]
    print("\n" + "=" * 80, flush=True)
    print(f"🚀 EXECUTING BATCH {batch_num}: {name.upper()}", flush=True)
    print("=" * 80 + "\n", flush=True)

    ui_api, settings = bootstrap_maki_services()
    orc = ui_api.orchestrator

    for idx, p in enumerate(prompts, 1):
        print(f"[{idx}/{len(prompts)}] 👤 USER: \"{p}\"", flush=True)
        t0 = time.time()
        try:
            resp = orc.handle_command(p)
            dt = round(time.time() - t0, 2)
            print(f"🤖 MAKI ({dt}s): {resp}\n", flush=True)
        except Exception as e:
            print(f"❌ ERROR: {e}\n", flush=True)
        time.sleep(2.0)

    print(f"✅ BATCH {batch_num} COMPLETED SUCCESSFULLY.\n", flush=True)

if __name__ == "__main__":
    b_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_batch(b_num)

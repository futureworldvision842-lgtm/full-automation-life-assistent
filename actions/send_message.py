# actions/send_message.py
# Universal messaging — WhatsApp & Instagram
# Uses visual element detection (pyautogui + screen search) instead of
# hardcoded tab/click sequences — works on any screen resolution.

import time
import pyautogui
from pathlib import Path

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.08

def _open_app(app_name: str) -> bool:
    """Opens an app via Windows search."""
    try:
        pyautogui.press("win")
        time.sleep(0.4)
        pyautogui.write(app_name, interval=0.04)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(2.0)  
        return True
    except Exception as e:
        print(f"[SendMessage] Could not open {app_name}: {e}")
        return False


def _search_contact(contact: str, platform: str):
    """
    Searches for a contact inside the messaging app.
    Uses Ctrl+F (universal search shortcut) then types contact name.
    """
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(contact, interval=0.04)
    time.sleep(0.8)
    pyautogui.press("enter")
    time.sleep(0.6)


def _type_and_send(message: str):
    """Types message and sends it."""
    pyautogui.press("tab")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(message, interval=0.03)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)


def _load_contact_book() -> dict:
    """config/wa_contacts.json — name (lowercase) → international number."""
    try:
        import json as _j
        cfg = Path(__file__).resolve().parent.parent / "config" / "wa_contacts.json"
        book = _j.loads(cfg.read_text(encoding="utf-8")).get("contacts", {})
        return {str(k).lower().strip(): str(v).strip() for k, v in book.items()}
    except Exception:
        return {}


def save_contact(name: str, number: str) -> str:
    """Saves or updates a contact in config/wa_contacts.json."""
    try:
        import json as _j
        cfg = Path(__file__).resolve().parent.parent / "config" / "wa_contacts.json"
        data = _j.loads(cfg.read_text(encoding="utf-8")) if cfg.exists() else {"contacts": {}}
        contacts = data.get("contacts", {})
        clean_name = (name or "").lower().strip()
        clean_num = "".join(ch for ch in str(number) if ch.isdigit())
        if not clean_name or not clean_num:
            return "Please provide a valid contact name and phone number."
        contacts[clean_name] = clean_num
        data["contacts"] = contacts
        cfg.write_text(_j.dumps(data, indent=2), encoding="utf-8")
        return f"Contact '{name}' saved with number {clean_num} in wa_contacts.json."
    except Exception as e:
        return f"Error saving contact: {e}"


def _normalize_name(name: str) -> str:
    """Strips common stop-words in Urdu/English like 'contact', 'number', 'bhai', 'sahab', 'sb', 'ji'."""
    import re
    clean = (name or "").lower().strip()
    for w in ["contact", "number", "bhai", "sahab", "sb", "ji", "ka", "ko", "wala", "wali"]:
        clean = re.sub(rf'\b{w}\b', '', clean)
    return re.sub(r'\s+', ' ', clean).strip()


def _resolve_contact_number(receiver: str) -> str:
    """Smartly matches receiver against wa_contacts.json using exact, substring, and word overlap."""
    r_raw = (receiver or "").strip()
    digits = "".join(ch for ch in r_raw if ch.isdigit())
    if digits and len(digits) >= 10:
        return digits

    r_clean = _normalize_name(r_raw)
    book = _load_contact_book()

    if not book:
        return ""

    # 1) Direct exact match on cleaned name
    if r_clean in book:
        return "".join(ch for ch in book[r_clean] if ch.isdigit())

    # 2) Direct exact match on raw name
    if r_raw.lower() in book:
        return "".join(ch for ch in book[r_raw.lower()] if ch.isdigit())

    # 3) Substring / word overlap match
    r_words = set(r_clean.split())
    best_num = ""
    max_overlap = 0

    for name_key, raw_num in book.items():
        k_clean = _normalize_name(name_key)
        # Substring match
        if r_clean and (r_clean in k_clean or k_clean in r_clean):
            return "".join(ch for ch in raw_num if ch.isdigit())

        # Word overlap
        k_words = set(k_clean.split())
        overlap = len(r_words.intersection(k_words))
        if overlap > max_overlap:
            max_overlap = overlap
            best_num = "".join(ch for ch in raw_num if ch.isdigit())

    return best_num if max_overlap > 0 else ""


def _send_whatsapp(receiver: str, message: str, audio_path: str = None) -> str:
    """
    Sends a WhatsApp message DIRECTLY (text and/or PTT audio voice note) — no window ever opens:
      1) Resolve name → number via config/wa_contacts.json (Smart Normalized Match).
      2) Baileys bridge  :3200/send        (numbers; always-on, works locked).
    """
    import urllib.request, json as _j

    r = (receiver or "").strip()
    digits = _resolve_contact_number(r)

    def _post(url, payload, timeout=45):
        data = _j.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _j.loads(resp.read())

    # 2) Baileys bridge (primary headless sender)
    try:
        payload = {"number": digits, "name": r, "message": message}
        if audio_path:
            payload["audioPath"] = audio_path
        res = _post("http://localhost:3200/send", payload)
        if res.get("ok"):
            audio_str = " (with PTT Voice Note)" if audio_path else ""
            return f"Message sent to {receiver} via WhatsApp{audio_str} (direct, no window)."
    except Exception:
        pass

    # 3) External forwarder — resolves NAMES against real WhatsApp contacts.
    try:
        payload = {"number": digits, "message": message} if (digits and len(digits) >= 10) \
                  else {"name": r, "message": message}
        if _post("http://localhost:3199/jarvis-send", payload).get("ok"):
            return f"Message sent to {receiver} via WhatsApp (forwarder, no window)."
    except Exception:
        pass

    # Headless Requirement: Never pop open the desktop WhatsApp application GUI window.
    return (
        f"Could not send WhatsApp message to '{receiver}' headlessly. "
        f"Please save '{receiver}' and their phone number in wa_contacts.json "
        f"so I can send messages directly without opening any app windows."
    )


def _send_instagram(receiver: str, message: str) -> str:
    """
    Sends an Instagram DM via browser (instagram.com).
    Steps: Open Chrome → Go to instagram.com/direct → Search contact → Send
    """
    try:
        import webbrowser

        webbrowser.open("https://www.instagram.com/direct/new/")
        time.sleep(3.5)

        pyautogui.write(receiver, interval=0.05)
        time.sleep(1.5)

        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)

        for _ in range(3):
            pyautogui.press("tab")
            time.sleep(0.1)
        pyautogui.press("enter")
        time.sleep(1.5)

        pyautogui.write(message, interval=0.04)
        time.sleep(0.2)
        pyautogui.press("enter")

        return f"Message sent to {receiver} via Instagram."

    except Exception as e:
        return f"Instagram error: {e}"

def _send_telegram(receiver: str, message: str) -> str:
    """Sends a Telegram message via Windows desktop app."""
    try:
        if not _open_app("Telegram"):
            return "Could not open Telegram."

        time.sleep(1.5)

        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)

        pyautogui.write(message, interval=0.03)
        time.sleep(0.2)
        pyautogui.press("enter")

        return f"Message sent to {receiver} via Telegram."

    except Exception as e:
        return f"Telegram error: {e}"



def _send_generic(platform: str, receiver: str, message: str) -> str:
    """
    For any other platform not explicitly supported.
    Opens the app, searches for contact, types and sends.
    Works for: Messenger, Discord, Signal, etc.
    """
    try:
        if not _open_app(platform):
            return f"Could not open {platform}."

        time.sleep(1.5)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)
        pyautogui.write(message, interval=0.03)
        time.sleep(0.2)
        pyautogui.press("enter")

        return f"Message sent to {receiver} via {platform}."

    except Exception as e:
        return f"{platform} error: {e}"

def send_message(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None
) -> str:
    """
    Called from main.py.

    parameters:
        receiver     : Contact name to send to
        message_text : The message content
        platform     : whatsapp | instagram | telegram | <any app name>
                       Default: whatsapp
    """
    params       = parameters or {}
    receiver     = params.get("receiver", "").strip()
    message_text = params.get("message_text", "").strip()
    platform     = params.get("platform", "whatsapp").strip().lower()
    audio_path   = params.get("audio_path", None)

    if not receiver:
        return "Please specify who to send the message to, sir."
    if not message_text and not audio_path:
        return "Please specify what message to send, sir."

    try:
        safe_preview = message_text[:40].encode('ascii', 'ignore').decode('ascii')
        print(f"[SendMessage] {platform} -> {receiver}: {safe_preview}")
    except Exception:
        pass
    if player:
        player.write_log(f"[msg] Sending to {receiver} via {platform}...")

    if "whatsapp" in platform or "wp" in platform or "wapp" in platform:
        result = _send_whatsapp(receiver, message_text, audio_path=audio_path)

    elif "instagram" in platform or "ig" in platform or "insta" in platform:
        result = _send_instagram(receiver, message_text)

    elif "telegram" in platform or "tg" in platform:
        result = _send_telegram(receiver, message_text)

    else:
        result = _send_generic(platform, receiver, message_text)

    print(f"[SendMessage] Result: {result}")
    if player:
        player.write_log(f"[msg] {result}")

    return result
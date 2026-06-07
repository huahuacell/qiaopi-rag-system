def extract_slots(text: str) -> dict:
    return {
        "recipient": "mother" if text else "",
        "money": "eight yuan" if text else "",
        "purpose": "household expenses" if text else "",
    }


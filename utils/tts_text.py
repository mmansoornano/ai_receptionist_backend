"""TTS-specific text preprocessing. Strips non-speech UI blocks before synthesis."""
import re

# Max characters to send to TTS; long replies degrade quality and create very long audio.
_TTS_MAX_CHARS = 2000
# Max sentences to keep when truncating (approx).
_TTS_MAX_SENTENCES = 15


def _normalize_numbers(text: str) -> str:
    """Convert numbers to words for better pronunciation.
    
    Examples:
        "Rs. 1,500" -> "Rs. one thousand five hundred"
        "Qty: 5" -> "Qty: five"
        "123-456-7890" -> "one two three, four five six, seven eight nine zero"
    """
    # Handle currency amounts
    def replace_currency(match):
        amount = match.group(1).replace(',', '')
        try:
            num = int(amount)
            if num == 0:
                return match.group(0)
            # Convert to words (simple implementation for common cases)
            words = _number_to_words(num)
            return f"{match.group(2)} {words}"
        except ValueError:
            return match.group(0)
    
    # Pattern: Rs. 1,500 or PKR 1,500
    text = re.sub(r'(Rs\.|PKR)\s*([\d,]+)', replace_currency, text, flags=re.IGNORECASE)
    
    # Handle phone numbers: 123-456-7890 -> one two three, four five six, seven eight nine zero
    def replace_phone(match):
        digits = match.group(0).replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        words = []
        for i, digit in enumerate(digits):
            if digit.isdigit():
                words.append(_digit_to_word(digit))
                # Add pause after every 3 digits
                if (i + 1) % 3 == 0 and i < len(digits) - 1:
                    words.append(',')
        return ' '.join(words)
    
    # Pattern: phone numbers with dashes or spaces
    text = re.sub(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', replace_phone, text)
    
    # Handle quantities: Qty: 5 -> Qty: five
    def replace_qty(match):
        try:
            num = int(match.group(1))
            return f"{match.group(2)} {_number_to_words(num)}"
        except ValueError:
            return match.group(0)
    
    text = re.sub(r'(Qty|Quantity)[:\s]+(\d+)', replace_qty, text, flags=re.IGNORECASE)
    
    return text


def _digit_to_word(digit: str) -> str:
    """Convert single digit to word."""
    words = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    return words.get(digit, digit)


def _number_to_words(num: int) -> str:
    """Convert number to words (simplified for common cases)."""
    if num < 20:
        words = {
            0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
            6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
            11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen', 15: 'fifteen',
            16: 'sixteen', 17: 'seventeen', 18: 'eighteen', 19: 'nineteen'
        }
        return words.get(num, str(num))
    
    if num < 100:
        tens = num // 10
        ones = num % 10
        tens_words = {
            2: 'twenty', 3: 'thirty', 4: 'forty', 5: 'fifty',
            6: 'sixty', 7: 'seventy', 8: 'eighty', 9: 'ninety'
        }
        if ones == 0:
            return tens_words.get(tens, str(num))
        return f"{tens_words.get(tens, str(tens))} {_number_to_words(ones)}"
    
    if num < 1000:
        hundreds = num // 100
        remainder = num % 100
        if remainder == 0:
            return f"{_number_to_words(hundreds)} hundred"
        return f"{_number_to_words(hundreds)} hundred {_number_to_words(remainder)}"
    
    if num < 1000000:
        thousands = num // 1000
        remainder = num % 1000
        if remainder == 0:
            return f"{_number_to_words(thousands)} thousand"
        return f"{_number_to_words(thousands)} thousand {_number_to_words(remainder)}"
    
    # For very large numbers, just return the number
    return str(num)


def _expand_abbreviations(text: str) -> str:
    """Expand common abbreviations for better pronunciation."""
    abbreviations = {
        r'\bPKR\b': 'Pakistani Rupees',
        r'\bRs\.': 'Rupees',
        r'\bQty\b': 'Quantity',
        r'\bQty\.': 'Quantity',
        r'\bID\b': 'I D',
        r'\bAPI\b': 'A P I',
        r'\bURL\b': 'U R L',
        r'\bHTTP\b': 'H T T P',
        r'\bHTTPS\b': 'H T T P S',
        r'\bSMS\b': 'S M S',
        r'\bTTS\b': 'T T S',
        r'\bSTT\b': 'S T T',
    }
    
    for pattern, replacement in abbreviations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text


def _add_prosody_pauses(text: str) -> str:
    """Add natural pauses based on punctuation for better prosody.
    
    Adds slight pauses for commas and longer pauses for periods, question marks, exclamation marks.
    This helps TTS models produce more natural-sounding speech.
    """
    # Add pause after commas (replace with comma + space, which TTS models interpret as pause)
    text = re.sub(r',([^\s])', r', \1', text)
    
    # Ensure proper spacing after sentence-ending punctuation
    text = re.sub(r'([.!?])([^\s])', r'\1 \2', text)
    
    # Add longer pause after sentence endings (double space)
    text = re.sub(r'([.!?])\s+', r'\1  ', text)
    
    return text


def _normalize_currency(text: str) -> str:
    """Normalize currency formatting for better pronunciation."""
    # Convert "Rs. 1,500" to "Rupees one thousand five hundred"
    # This is handled in _normalize_numbers, but we can add more specific currency handling here
    text = re.sub(r'Rs\.\s*', 'Rupees ', text, flags=re.IGNORECASE)
    text = re.sub(r'PKR\s*', 'Pakistani Rupees ', text, flags=re.IGNORECASE)
    return text


def _strip_customer_id_line(text: str) -> str:
    """Remove 'Customer ID: X - use this for all cart tools.' lines."""
    pattern = r"^\s*Customer ID:\s*\d+\s*-\s*use this for all cart tools\.?\s*$"
    return re.sub(pattern, "", text, flags=re.MULTILINE)


def _is_product_catalog_line(line: str) -> bool:
    """True if line is part of product catalog (category header, product row, etc.)."""
    s = line.strip()
    if not s:
        return False
    if s == "PRODUCT CATALOG" or s.startswith("===") and s.endswith("==="):
        return True
    if re.match(r"^-\s+.+[:\s]+(?:PKR|Rs\.)\s*[\d,]+\.?\d*\s*$", s):
        return True
    if "[Add]" in s or "[+]" in s:
        return True
    if re.match(r"^-\s+.+$", s) and any(
        x in s for x in ("Rs.", "PKR", "Cookie", "Protein", "Granola", "Gift Box")
    ):
        return True
    return False


def _is_cart_block_line(line: str) -> bool:
    """True if line is part of cart block (Cart Contents, items, total)."""
    s = line.strip()
    if not s:
        return False
    if "Cart Contents:" in s or "Your cart is empty." in s:
        return True
    if re.match(r"^-.+\(Qty:\s*\d+\).+Rs\.\s*[\d,]+\.?\d*\s*$", s):
        return True
    if re.match(r"^Total:\s*Rs\.\s*[\d,]+\.?\d*\s*$", s, re.IGNORECASE):
        return True
    return False


def _is_standalone_button_label(line: str) -> bool:
    """True if line is only 'Proceed' or 'Continue' (UI button, not natural speech)."""
    s = line.strip()
    return s in ("Proceed", "Continue", "Proceed.", "Continue.")


def _truncate_sentences(text: str, max_sentences: int = _TTS_MAX_SENTENCES) -> str:
    """Keep roughly the first max_sentences sentences."""
    if not text or len(text) <= _TTS_MAX_CHARS:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text)
    if len(parts) <= max_sentences:
        return text[: _TTS_MAX_CHARS]
    kept = " ".join(parts[:max_sentences])
    return kept[: _TTS_MAX_CHARS] if len(kept) > _TTS_MAX_CHARS else kept


def prepare_text_for_tts(text: str) -> str:
    """Prepare agent response text for TTS by stripping UI-only content and enhancing for natural speech.

    Processing steps:
    1. Removes 'Customer ID: X - use this for all cart tools.'
    2. Removes product catalog blocks (headers, product rows, Add/+).
    3. Removes cart blocks (Cart Contents, items, total).
    4. Removes standalone 'Proceed' / 'Continue' button lines.
    5. Expands abbreviations (PKR -> Pakistani Rupees, Qty -> Quantity, etc.)
    6. Normalizes numbers and currency for better pronunciation
    7. Adds prosody pauses based on punctuation
    8. Preserves dialogue tags [S1]/[S2] and nonverbal tags (laughs), (coughs), etc.
    9. Collapses excessive newlines, trims.
    10. Truncates to first _TTS_MAX_CHARS chars or _TTS_MAX_SENTENCES sentences.
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Step 1: Strip UI-only content
    out = _strip_customer_id_line(text)
    lines = out.split("\n")
    kept = []
    in_catalog = False
    in_cart = False
    for raw in lines:
        line = raw.rstrip()
        if _is_product_catalog_line(line):
            in_catalog = True
            continue
        if _is_cart_block_line(line):
            in_cart = True
            continue
        if _is_standalone_button_label(line):
            continue
        in_catalog = False
        in_cart = False
        kept.append(line)
    out = "\n".join(kept)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    
    if not out:
        return "I received your message."
    
    # Step 2: Expand abbreviations
    out = _expand_abbreviations(out)
    
    # Step 3: Normalize currency
    out = _normalize_currency(out)
    
    # Step 4: Normalize numbers (but preserve dialogue tags and nonverbal tags)
    # Split by dialogue tags to preserve them
    parts = re.split(r'(\[S[12]\])', out)
    normalized_parts = []
    for part in parts:
        if re.match(r'\[S[12]\]', part):
            normalized_parts.append(part)  # Keep dialogue tags as-is
        else:
            # Normalize numbers but preserve nonverbal tags like (laughs), (coughs)
            normalized_parts.append(_normalize_numbers(part))
    out = ''.join(normalized_parts)
    
    # Step 5: Add prosody pauses (but preserve nonverbal tags)
    # Split by nonverbal tags to preserve them
    parts = re.split(r'(\([^)]+\))', out)  # Match (laughs), (coughs), etc.
    paused_parts = []
    for part in parts:
        if re.match(r'\([^)]+\)', part):
            paused_parts.append(part)  # Keep nonverbal tags as-is
        else:
            paused_parts.append(_add_prosody_pauses(part))
    out = ''.join(paused_parts)
    
    # Step 6: Truncate if needed
    return _truncate_sentences(out)

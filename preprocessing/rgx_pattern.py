import re
import regex

MONTH_MAP = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


BOILERPLATE_PATTERNS = [
    r"Please provide all common names,?\s*trade names,?\s*and CAS numbers.*?Main Hazard Class of your chemical/material\.?",
    r"Please provide all common names,?\s*trade names,?\s*and CAS numbers.*?chemical/material\.?",
    r"Please provide all common names,?\s*trade names,?\s*and CAS numbers.*?Storage Group Identifier[^.]*\.?",
    r"Please provide all common names.*?Read the MSDSs as well as the",
    r"Please provide all common names.*?secondary chemicals[^.]*\.",
    r"Include an MSDS,? if available[^.]*\.",
    r"Make sure to include information for any new secondary chemicals[^.]*\.",
    r"Read the MSDSs as well as the",
    r"Vendor/manufacturer info:?\s*address and phone number,?\s*website URL\.?",
    r"address and phone number,?\s*website URL\.?",
    r"Please give serious thought to this\..*?Will any of the current SNF approved chemicals and materials work for me\?",
    r"Please give serious thought to this\..*?work for me\?",
    r"Please give serious thought to this\..*?newer/safer alternatives[^?]*\?",
    r"Please provide a detailed process flow description.*?MOS grade or better\.?\s*",
    r"Please provide a detailed process flow description.*?better\.?\s*",
    r"Please provide a detailed process flow description.*?wet benches\.?",
    r"Please provide a detailed process flow description.*?clean.*?tool[^.]*\.",
    r"all Lab equipment to be used for processing[^.]*\.",
    r"Make sure to include wet benches\.?",
    r"Please note that.*?the material should MOS grade or better\.?\s*",
    r"How much will you bring in\?.*?Do you need to mix it to use it\?",
    r"How much will you bring in\?.*?mix it to use it\?",
    r"How much will you bring in\?.*?powders are not permitted[^.]*\.",
    r"Is it solid,? powder or liquid\?[^.]*\.?",
    r"Will you be storing your chemical/material at SNF\?.*?at any wet bench\.?\s*",
    r"Will you be storing your chemical/material at SNF\?.*?wet bench\.?\s*",
    r"Will you be storing your chemical/material at SNF\?.*?bulk storage area\.?",
    r"Storage groups? A,? B,? D and L are stored[^.]*\.",
    r"Ensure your chemical container or material is properly labeled\.?",
    r"How will you dispose of any waste.*?available in the lab\.?\s*",
    r"How will you dispose of any waste.*?the lab\.?\s*",
    r"How will you dispose of any waste.*?Safety Manual[^.]*\.",
    r"for the different methods of waste disposal[^.]*\.",
    r"Stanford Chemical Storage Groups\s*to determine[^.]*\.",
    r"to determine the Storage Group Identifier[^.]*\.",
]


BANNER = r"""
/******************************************************************************\
*                                                                              *
*                         N E X T   E M A I L   T H R E A D                    *
*                                                                              *
\******************************************************************************/
"""

def strip_boilerplate(content: str) -> str:
    if not content:
        return content

    result = re.sub(r"\s+", " ", content).strip()

    for pattern in BOILERPLATE_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    result = re.sub(r"\s+", " ", result).strip()
    return result


def collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# def fuzzy_find(text: str, target: str, max_errors: int = 1) -> int:
#     escaped_target = regex.escape(target)
#     pattern = f"(\\b{escaped_target}\\b){{e<={max_errors}}}"
#     match = regex.search(pattern, text, regex.IGNORECASE)
#     if match:
#         return match.start()
#     return -1


def header_variants(target: str) -> list[str]:
    base = collapse_spaces(target)
    seeds = [base]

    no_number = re.sub(r"^\s*\d+\s*[\.\)\-:]?\s*", "", base).strip()
    if no_number and no_number not in seeds:
        seeds.append(no_number)

    variants = []
    seen = set()
    for seed in seeds:
        candidates = [seed]

        no_trailing_punct = re.sub(r"[:\.\-]\s*$", "", seed).strip()
        if no_trailing_punct:
            candidates.append(no_trailing_punct)
            candidates.append(f"{no_trailing_punct}:")

        for candidate in candidates:
            cleaned_candidate = collapse_spaces(candidate)
            if cleaned_candidate and cleaned_candidate not in seen:
                seen.add(cleaned_candidate)
                variants.append(cleaned_candidate)

    return variants


def fuzzy_find_header(text: str, target: str, max_errors: int = 1):
    variants = header_variants(target)

    # Prefer exact variant matches before fuzzy matches to reduce false positives.
    match_list = []
    for variant in variants:
        escaped_variant = regex.escape(variant)
        exact_pattern = rf"(?<!\w){escaped_variant}(?!\w)"
        for exact_match in regex.finditer(exact_pattern, text, regex.IGNORECASE):
            duplicate = False
            for item in match_list:
                if exact_match.span()[0] in item or exact_match.span()[1] in item:
                    duplicate = True
            if not duplicate:
                match_list.append(exact_match.span())

    if match_list:
        return sorted(match_list, key=lambda span: span[0])

    for variant in variants:
        escaped_variant = regex.escape(variant)
        fuzzy_pattern = rf"(?<!\w)({escaped_variant}){{e<={max_errors}}}(?!\w)"
        for fuzzy_match in regex.finditer(fuzzy_pattern, text, regex.IGNORECASE):
            duplicate = False
            for item in match_list:
                if fuzzy_match.span()[0] in item or fuzzy_match.span()[1] in item:
                    duplicate = True
            if not duplicate:
                match_list.append(fuzzy_match.span())
                print("got a fuzzy match")

    if match_list:
        return sorted(match_list, key=lambda span: span[0])
    else:
        return None


def first_span_after(candidates, min_start: int):
    if not candidates:
        return None
    for span in candidates:
        if span[0] >= min_start:
            return span
    return None


def extract_date_from_section(section_text: str) -> str:
    if not section_text:
        return ""

    cleaned = re.sub(r"(?i)\bDate\b\s*:?\s*", "", section_text)
    cleaned = re.sub(r"(\d{1,2})(st|nd|rd|th)\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bof\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", " ")
    cleaned = re.sub(r"([A-Za-z]{3,})\.", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    match = re.search(r"(?<!\d)(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})(?!\d)", cleaned)
    if match:
        y, m, d = match.group(1), int(match.group(2)), int(match.group(3))
        return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"(?<!\d)(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})(?!\d)", cleaned)
    if match:
        m, d, y = int(match.group(1)), int(match.group(2)), match.group(3)
        if len(y) == 2:
            y = "20" + y
        return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"(\d{4})\s+(\d{1,2})\s+(\d{1,2})", cleaned)
    if match:
        y, m, d = match.group(1), int(match.group(2)), int(match.group(3))
        return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})", cleaned)
    if match:
        m, d, y = int(match.group(1)), int(match.group(2)), match.group(3)
        if len(y) == 2:
            y = "20" + y
        return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})", cleaned)
    if match:
        d = int(match.group(1))
        month_name = match.group(2).lower()
        y = match.group(3)
        if len(y) == 2:
            y = "20" + y
        if month_name in MONTH_MAP:
            m = MONTH_MAP[month_name]
            return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"([A-Za-z]+)\s+(\d{1,2})\s+(\d{2,4})", cleaned)
    if match:
        month_name = match.group(1).lower()
        d = int(match.group(2))
        y = match.group(3)
        if len(y) == 2:
            y = "20" + y
        if month_name in MONTH_MAP:
            m = MONTH_MAP[month_name]
            return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"(\d{1,2})([A-Za-z]+)(\d{2,4})", cleaned)
    if match:
        d = int(match.group(1))
        month_name = match.group(2).lower()
        y = match.group(3)
        if len(y) == 2:
            y = "20" + y
        if month_name in MONTH_MAP:
            m = MONTH_MAP[month_name]
            return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"([A-Za-z]+)(\d{1,2})(\d{4})", cleaned)
    if match:
        month_name = match.group(1).lower()
        d = int(match.group(2))
        y = match.group(3)
        if month_name in MONTH_MAP:
            m = MONTH_MAP[month_name]
            return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"(\d{1,2})[\/\-.]([A-Za-z]+)[\/\-.](\d{2,4})", cleaned)
    if match:
        d = int(match.group(1))
        month_name = match.group(2).lower()
        y = match.group(3)
        if len(y) == 2:
            y = "20" + y
        if month_name in MONTH_MAP:
            m = MONTH_MAP[month_name]
            return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"([A-Za-z]+)[\/\-.](\d{1,2})[\/\-.](\d{2,4})", cleaned)
    if match:
        month_name = match.group(1).lower()
        d = int(match.group(2))
        y = match.group(3)
        if len(y) == 2:
            y = "20" + y
        if month_name in MONTH_MAP:
            m = MONTH_MAP[month_name]
            return f"{m:02d}/{d:02d}/{y}"

    match = re.search(r"([A-Za-z]+)\s+(\d{4})", cleaned)
    if match:
        month_name = match.group(1).lower()
        y = match.group(2)
        if month_name in MONTH_MAP:
            m = MONTH_MAP[month_name]
            return f"{m:02d}/01/{y}"

    return ""

import pypdfium2 as pdfium
from pathlib import Path
import re
import regex
import pypdfium2.internal as pdfium_i
import time
import docx2txt
f


target_list = [
    "Title",
    "Requestor:",
    "Date:",
    "1. The chemical or material",
    "2. Vendor/manufacturer info",
    "3. Reason for request",
    "4. Process Flow",
    "5. Amount and form",
    "6. Storage",
    "7. Disposal",
]

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

BANNER = r"""
/******************************************************************************\
*                                                                              *
*                         N E X T   E M A I L   T H R E A D                    *
*                                                                              *
\******************************************************************************/
"""

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


def fuzzy_find(text: str, target: str, max_errors: int = 1) -> int:
    escaped_target = regex.escape(target)
    pattern = f"(\\b{escaped_target}\\b){{e<={max_errors}}}"
    match = regex.search(pattern, text, regex.IGNORECASE)
    if match:
        return match.start()
    return -1


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


def pdf_extractor(file_path: str) -> str:
    pdf = pdfium.PdfDocument(file_path)
    cleaned_text = ""

    for i in range(len(pdf)):
        page = pdf[i]
        textpage = page.get_textpage()
        text_all = textpage.get_text_bounded()
        page_text = collapse_spaces(text_all)
        cleaned_text += page_text + " "
        textpage.close()
        page.close()
    pdf.close()
    

    return cleaned_text

def docx_extractor(file_path: str) -> str:
    docx_text = docx2txt.process(file_path)
    cleaned_text = collapse_spaces(docx_text)
    return cleaned_text


def extractor(cleaned_text: str, file_path: str ):
    numbered_fields = {}
    min_header_start = 0

    for t_idx in range(len(target_list)):
        current_header_candidates = fuzzy_find_header(cleaned_text, target_list[t_idx])
        current_header_span = first_span_after(current_header_candidates, min_header_start)
        if current_header_span is None:
            print(f"Can't find target: {target_list[t_idx]} in {file_path}")
            numbered_fields[t_idx] = ""
            return target_list[t_idx]
        start_pos = current_header_span[1]
        min_header_start = start_pos


        if t_idx < (len(target_list) - 1):
            next_header_candidates = fuzzy_find_header(cleaned_text, target_list[t_idx + 1])
            next_header_span = first_span_after(next_header_candidates, start_pos)
            if next_header_span is None:
                end_pos = len(cleaned_text)
            else:
                end_pos = next_header_span[0]
        else:
            end_pos = len(cleaned_text)
        section_text = cleaned_text[start_pos:end_pos]
        section_text = re.sub(r"^[\s:.\-]+", "", section_text).strip()
        numbered_fields[t_idx] = section_text


    date_section = numbered_fields.get(2, "")
    extracted_date = extract_date_from_section(date_section)

    prom_form = {
        "date": extracted_date,
        "filename": Path(file_path).name,
        "requestor": strip_boilerplate(numbered_fields.get(1, "")),
        "request_title": strip_boilerplate(numbered_fields.get(0, "")),
        "chemicals_and_processes": strip_boilerplate(numbered_fields.get(3, "")),
        "request_reason": strip_boilerplate(numbered_fields.get(5, "")),
        "process_flow": strip_boilerplate(numbered_fields.get(6, "")),
        "amount_and_form": strip_boilerplate(numbered_fields.get(7, ""))
    }

    return prom_form


def print_problematic_file_texts(trouble_files):
    if not trouble_files:
        print("\nNo problematic files to inspect.")
        return

    for idx, trouble_item in enumerate(trouble_files, start=1):
        file_path, missing_target = trouble_item
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".docx":
            extracted_text = docx_extractor(file_path)
        elif suffix == ".pdf":
            extracted_text = pdf_extractor(str(file_path))
        else:
            extracted_text = f"UNSUPPORTED FILE FORMAT: {suffix}"

        print("\n" + "=" * 100)
        print(f"PROBLEM FILE {idx}/{len(trouble_files)}")
        print(f"File: {file_path.name}")
        print(f"Type: {suffix or 'NO_SUFFIX'}")
        print(f"Missing target: {missing_target}")
        print("-" * 100)
        print("EXTRACTED TEXT")
        print("-" * 100)
        print(extracted_text)
        print("=" * 100)


if __name__ == "__main__":
    directory = Path(__file__).parent.parent / "files" / "promForms" / "2019"
    pdfs = [file for file in directory.iterdir()]
    print(f"Found {len(pdfs)} PDF files")
    trouble_files = []
    counter = 0
    for pdf_file in pdfs:
        if pdf_file.suffix == ".docx":
            cleaned_text = docx_extractor(pdf_file)
        elif pdf_file.suffix == ".pdf":
            cleaned_text = pdf_extractor(pdf_file)
        else:
            print("UNSUPPORTED FILE FORMAT")
        print(f"\nProcessing: {pdf_file.name}")
        result = extractor(cleaned_text, str(pdf_file))
        if isinstance(result, str):
            trouble_files.append([pdf_file, result])
            continue
        print("\nReturned PromForm data:")
        for key, value in result.items():
            preview = (
                value[:50] + "..."
                if isinstance(value, str) and len(value) > 50
                else value
            )
            print(f"  {key}: {preview}")
            # counter+=1

        print("\n" + "=" * 70)
        counter+=1
    print(f"completed {(counter/len(pdfs)) * 100}% or {counter}/{len(pdfs)}")
    print("Trouble Files")
    print(trouble_files)
    print_problematic_file_texts(trouble_files)

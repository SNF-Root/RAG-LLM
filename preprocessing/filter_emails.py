import re
from typing import Iterable, Optional


REMOVE_HEADER_KEYS = {
    "from", "date", "subject", "to", "cc", "bcc",
    "message-id", "in-reply-to", "references", "reply-to",
    "content-type", "content-transfer-encoding", "mime-version",
    "x-mailer", "x-originating-ip", "received", "return-path",
}


HEADER_LINE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):")

MBOX_ENVELOPE_RE = re.compile(
    r"^From\s+\S+.*\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b.*\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b"
)

ON_WROTE_RE = re.compile(r"^On .+ wrote:\s*$", re.IGNORECASE)
ON_DATE_WROTE_RE = re.compile(r"^On \d{1,2}/\d{1,2}/\d{2,4}.+wrote:\s*$", re.IGNORECASE)
ANGLE_ON_WROTE_RE = re.compile(r"^>\s*On .+ wrote:\s*$", re.IGNORECASE)

ON_DATE_MULTILINE_RE = re.compile(
    r"^On\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
    re.IGNORECASE
)


TIME_PATTERN = re.compile(r"\d{1,2}:\d{2}")
DATE_PATTERN = re.compile(r"\d{1,2}[./\-\s]+(?:\d{1,2}|\w{3,9})[./\-\s]+\d{2,4}|\d{1,2}\s+\w{3,9}\.?\s+\d{4}")

def is_quote_header_line(line: str, next_line: str = "") -> bool:
    """
    Detect quote headers in any language by checking for:
    - A time pattern (HH:MM)
    - A date pattern
    - Angle brackets (< and >) for email address
    Can span two lines.
    """
    combined = line + " " + next_line
    has_time = bool(TIME_PATTERN.search(combined))
    has_date = bool(DATE_PATTERN.search(combined))
    has_angle_open = "<" in combined
    has_angle_close = ">" in combined
    
    return has_time and has_date and has_angle_open and has_angle_close


MESSAGE_ID_LINE_RE = re.compile(r"^<[^@>]+@[^>]+>\s*$")


FOLDED_HEADER_RE = re.compile(r"^[\t ]+\S")


DIVIDER_RE = re.compile(r"^[_=-]{5,}\s*$")


ATTACHMENT_RE = re.compile(
    r"(?i)(^[-]{2,}\s*next part\s*[-]{2,}$|"
    r"attachment was scrubbed|"
    r"^An HTML attachment was scrubbed|"
    r"^A non-text attachment was scrubbed|"
    r"^An embedded and charset-unspecified text was scrubbed|"
    r"^Name:\s*\S+\.\S+\s*$|" 
    r"^Type:\s*(application|image|text|audio|video)/|"  
    r"^Size:\s*\d+\s*bytes|"
    r"^Desc:\s*|"
    r"^URL:\s*<https?://)"
)


LIST_BOILERPLATE_RE = re.compile(
    r"(?i)(^_{3,}$|"
    r"mailing list$|"
    r"mailman|"
    r"/listinfo/|"
    r"^snf-promcommittee\s|"
    r"lists\.stanford\.edu$)"
)


FORWARDED_RE = re.compile(r"^-{5,}\s*Forwarded message\s*-{5,}\s*$", re.IGNORECASE)
ORIGINAL_MSG_RE = re.compile(r"^-{5,}\s*Original Message\s*-{5,}\s*$", re.IGNORECASE)


OUTLOOK_HEADER_RE = re.compile(
    r"^\*?(From|Sent|To|Cc|Subject|Date):\*?\s*.+$",
    re.IGNORECASE
)

ON_BEHALF_RE = re.compile(
    r"^From:.+On Behalf Of",
    re.IGNORECASE
)

# Image placeholders: [image: xyz] or [xyz]<url>
IMAGE_PLACEHOLDER_RE = re.compile(r"\[image:\s*[^\]]+\]|\[[^\]]+\]\s*<https?://[^>]+>")

# Mailto links: <mailto:...>
MAILTO_RE = re.compile(r"<mailto:[^>]+>")

# "Sent from" footers
SENT_FROM_RE = re.compile(
    r"^Sent from (Mail|my iPhone|my iPad|Outlook|Samsung|Yahoo|Gmail)",
    re.IGNORECASE
)

# Confidentiality notice patterns
CONFIDENTIALITY_RE = re.compile(
    r"(?i)(CONFIDENTIAL|"
    r"This e-?mail.+intended solely|"
    r"If you are not the intended recipient|"
    r"please.+delete this message|"
    r"do not disclose the contents)"
)

# Professional signature markers (name, title, phone, address patterns)
PHONE_RE = re.compile(r"^(?:Tel|Phone|Mobile|Fax|Cell)?:?\s*[\+]?[\d\s\-\(\)\.]{10,}$")
ADDRESS_LINE_RE = re.compile(r"^\d+\s+[A-Za-z].*(?:Ave|Avenue|St|Street|Rd|Road|Way|Mall|Blvd|Drive|Dr)\b", re.IGNORECASE)
WEBSITE_LINE_RE = re.compile(r"^(?:www\.|https?://)[^\s]+$|^[a-z]+\.(com|edu|org|net)$", re.IGNORECASE)

# Email-only lines (just an email address)
EMAIL_ONLY_RE = re.compile(r"^[a-zA-Z0-9._%+-]+\s*(?:at|@)\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*$")

# Inline quoted email header block (From: ... Date: ... To: ... Subject: pattern)
INLINE_QUOTE_HEADER_RE = re.compile(
    r"^From:.+$|^Date:.+$|^To:.+$|^Subject:.+$|^Cc:.+$",
    re.IGNORECASE
)


def is_inline_quoted_header_block(lines: list, idx: int) -> bool:
    """
    Detect if current line is part of an inline quoted header block.
    These appear in Outlook-style replies without '>' prefix.
    Pattern: From: ... / Sent: ... / To: ... / Subject: ...
    """
    if idx >= len(lines):
        return False
    
    line = lines[idx].strip()
    
    # Check if this line starts with a typical reply header keyword
    header_keywords = ['from:', 'sent:', 'to:', 'cc:', 'subject:', 'date:']
    line_lower = line.lower()
    
    if not any(line_lower.startswith(kw) for kw in header_keywords):
        return False
    
    # Look ahead/behind to see if this is part of a header block
    header_count = 0
    for i in range(max(0, idx - 3), min(len(lines), idx + 4)):
        test_line = lines[i].strip().lower()
        if any(test_line.startswith(kw) for kw in header_keywords):
            header_count += 1
    
    # If we see 2+ header-like lines in proximity, it's likely a quoted header block
    return header_count >= 2


def extract_main_message(raw_email: str) -> str:
    """
    Extracts the main message body from raw/mboxed email text.
    Removes: envelope lines, selected header lines, quoted history, 
    list boilerplate, attachments markers, signatures, forwarded content.
    """
    lines = raw_email.splitlines()
    out_lines = []
    in_headers = True
    stop_after = False
    saw_body = False
    in_signature = False
    in_forwarded = False
    in_confidentiality = False
    consecutive_filtered = 0
    
    last_was_header = False
    pending_on_wrote = False  # Track multi-line "On ... wrote:" patterns
    
    for idx, line in enumerate(lines):
        if stop_after:
            continue
        
        stripped = line.strip("\r\n")
        stripped_clean = stripped.strip()
        
        # Blank line ends header region
        if in_headers and stripped_clean == "":
            in_headers = False
            last_was_header = False
            continue
        
        # Skip mbox envelope lines
        if MBOX_ENVELOPE_RE.match(stripped):
            continue
        
        # Skip folded header continuation lines (start with whitespace after a header)
        if in_headers and FOLDED_HEADER_RE.match(stripped) and last_was_header:
            continue
        
        # Header-style lines - remove selected keys
        m = HEADER_LINE_RE.match(stripped)
        if m and in_headers:
            key = m.group(1).lower()
            if key in REMOVE_HEADER_KEYS:
                last_was_header = True
                continue
            last_was_header = True
        else:
            last_was_header = False
        
        # Skip standalone Message-ID style lines: <...@...>
        if MESSAGE_ID_LINE_RE.match(stripped_clean):
            continue
        
        # Forwarded message marker - skip forwarded content
        if FORWARDED_RE.match(stripped_clean):
            in_forwarded = True
            continue
        
        # Original message marker - stop processing
        if ORIGINAL_MSG_RE.match(stripped_clean):
            stop_after = True
            continue
        
        # Skip content after forwarded message header until we see actual content
        if in_forwarded:
            # Check if this looks like a header line in forwarded section
            if INLINE_QUOTE_HEADER_RE.match(stripped_clean):
                continue
            if stripped_clean == "":
                continue
            # Reset - we're now in the forwarded body
            in_forwarded = False
        
        # Quoted reply lines (starting with >)
        if stripped_clean.startswith(">"):
            continue
        
        # "On ... wrote:" reply introducers
        if ON_WROTE_RE.match(stripped_clean) or ON_DATE_WROTE_RE.match(stripped_clean):
            stop_after = True
            continue
        
        # Angle-bracket quoted "On wrote"
        if ANGLE_ON_WROTE_RE.match(stripped_clean):
            stop_after = True
            continue
        
        # Multi-line "On ... wrote:" - first line has "On Mon, Feb..." pattern
        # Check if next line contains "wrote:"
        if ON_DATE_MULTILINE_RE.match(stripped_clean):
            # Look ahead to see if next non-empty line contains "wrote:"
            for lookahead in range(idx + 1, min(idx + 3, len(lines))):
                next_line = lines[lookahead].strip()
                if next_line and "wrote:" in next_line.lower():
                    stop_after = True
                    break
            if stop_after:
                continue
        
        # Handle the second line of multi-line "On wrote" (email + wrote:)
        if "wrote:" in stripped_clean.lower() and idx > 0:
            prev_line = lines[idx - 1].strip()
            if ON_DATE_MULTILINE_RE.match(prev_line):
                stop_after = True
                continue
        
        # Generic quote header detection (any language)
        # Check current line + next line for date + time + angle brackets
        next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
        if is_quote_header_line(stripped_clean, next_line):
            stop_after = True
            continue
        
        # Detect inline quoted header blocks (Outlook style without >)
        if is_inline_quoted_header_block(lines, idx):
            consecutive_filtered += 1
            if consecutive_filtered >= 3:
                stop_after = True
            continue
        
        # Outlook "On Behalf Of" lines
        if ON_BEHALF_RE.match(stripped_clean):
            continue
        
        # Divider lines
        if DIVIDER_RE.match(stripped_clean):
            continue
        
        # Mailing list boilerplate
        if LIST_BOILERPLATE_RE.search(stripped_clean):
            continue
        
        # Attachment markers
        if ATTACHMENT_RE.search(stripped_clean):
            continue
        
        # "Sent from" footers
        if SENT_FROM_RE.match(stripped_clean):
            continue
        
        # Confidentiality notice - skip until end
        if CONFIDENTIALITY_RE.search(stripped_clean):
            in_confidentiality = True
            continue
        
        if in_confidentiality:
            # Skip lines that look like continuation of legal text
            if len(stripped_clean) > 50 and not stripped_clean.endswith(('.', '!', '?')):
                continue
            if stripped_clean == "":
                in_confidentiality = False
            continue
        
        # Clean up image placeholders and mailto links from the line
        cleaned_line = IMAGE_PLACEHOLDER_RE.sub('', stripped_clean)
        cleaned_line = MAILTO_RE.sub('', cleaned_line)
        cleaned_line = cleaned_line.strip()
        
        # Skip lines that are just email addresses
        if EMAIL_ONLY_RE.match(cleaned_line):
            continue
        
        # Skip phone number only lines (signature)
        if PHONE_RE.match(cleaned_line):
            in_signature = True
            continue
        
        # Skip address lines (signature)
        if ADDRESS_LINE_RE.match(cleaned_line):
            in_signature = True
            continue
        
        # Skip website-only lines
        if WEBSITE_LINE_RE.match(cleaned_line):
            continue
        
        # Signature delimiter
        if cleaned_line == "--" or cleaned_line == "—" or cleaned_line == "-- ":
            in_signature = True
            continue
        

        if in_signature:
            if len(cleaned_line) > 80:
                in_signature = False
            else:
                continue
        

        consecutive_filtered = 0
        
        # Keep the line
        if cleaned_line != "":
            saw_body = True
            out_lines.append(cleaned_line)
        else:

            if saw_body and (len(out_lines) == 0 or out_lines[-1] != ""):
                out_lines.append("")
    

    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    
    return "\n".join(out_lines)



if __name__ == "__main__":
    test_email = """From alex.xing at 10xgenomics.com  Wed Dec  4 22:58:44 2019
From: alex.xing at 10xgenomics.com (Alex Xing)
Date: Wed, 4 Dec 2019 22:58:44 -0800
Subject: [snf-promcommittee] apply for review of new material
Message-ID: <CAE7c8nDXPpqy2fi11D16u7_ydraVbeaQM0cSC1TPYNNOv-pkHQ@mail.gmail.com>

Hello,

Please attached find the application form, msds and datasheet. Thank you
for your consideration. Hope to hear from you soon.

Best,

Alex

-- 
Alex Xing
Microfluidics Engineer 3
alex.xing at 10xgenomics.com
[image: 10x Genomics] <http://www.10xgenomics.com/>
6230 Stoneridge Mall Road
Pleasanton, CA 94588-3260 | 10xgenomics.com <http://www.10xgenomics.com/>
[image: LinkedIn] <https://www.linkedin.com/company/10x-technologies>
-------------- next part --------------
An HTML attachment was scrubbed...
URL: <https://mailman.stanford.edu/mailman/private/snf-promcommittee/attachments/20191204/7a6190f6/attachment-0001.html>
"""
    
    print("Original email length:", len(test_email))
    result = extract_main_message(test_email)
    print("\nExtracted message:")
    print("-" * 50)
    print(result)
    print("-" * 50)
    print("Extracted length:", len(result))

"""Short-lived OCR process: PDF bytes on stdin, page indexes as arguments, JSON [[text, conf, low_share], ...] on stdout.
Exits after one document so every byte the OCR models used goes back to the OS (see extraction.OCR_ISOLATE)."""
import json
import os
import sys


def main() -> int:
    os.environ["OCR_ISOLATE"] = "0"  # this process *is* the OCR process
    out = sys.stdout
    sys.stdout = sys.stderr  # library logging/prints must not corrupt the JSON reply
    from app import extraction

    if sys.argv[1:] == ["--check"]:
        extraction.get_ocr()
        return 0
    import pymupdf

    pdf = sys.stdin.buffer.read()
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    res = [extraction._ocr_page(doc[int(i)]) for i in sys.argv[1:]]
    doc.close()
    out.write(json.dumps(res))
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())

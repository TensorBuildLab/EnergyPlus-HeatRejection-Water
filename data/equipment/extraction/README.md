`extract_kloppers2003.py` built `../kloppers2003_fill_tests.csv` from OCR text of Kloppers (2003), PhD thesis,
Stellenbosch University, http://hdl.handle.net/10019.1/1476, Appendices R (trickle), S (splash), T (film).
Usage: `python extract_kloppers2003.py thesis_ocr.txt > ../kloppers2003_fill_tests.csv`. The line ranges and the OCR typo
fixes in the script are specific to that OCR text; every extracted row was checked for flow and temperature consistency.
Merkel numbers in the CSV are per fill (the thesis tabulates them per metre of fill; multiplied by the fill height).

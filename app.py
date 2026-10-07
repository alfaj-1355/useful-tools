import base64
import csv
import io
import json
import math
import os
import re
import secrets
import string
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter, Transformation
import qrcode

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

UPLOAD_DIR = Path(tempfile.gettempdir()) / "usefultools"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

TOOLS = [
    # Text
    ("word-counter", "Word Counter", "Count words, characters, sentences and paragraphs.", "Text"),
    ("case-converter", "Case Converter", "Convert text to upper, lower, title and sentence case.", "Text"),
    ("remove-duplicates", "Remove Duplicate Lines", "Remove repeated lines while preserving order.", "Text"),
    ("text-reverser", "Text Reverser", "Reverse characters, words or lines.", "Text"),
    ("find-replace", "Find & Replace", "Replace text quickly with optional case matching.", "Text"),
    ("slug-generator", "Slug Generator", "Turn a title into a clean URL slug.", "Text"),
    ("lorem-ipsum", "Lorem Ipsum Generator", "Generate placeholder paragraphs.", "Text"),
    ("sort-lines", "Sort Lines", "Sort lines alphabetically or numerically.", "Text"),
    ("line-breaks", "Line Break Cleaner", "Normalize blank lines and whitespace.", "Text"),
    ("text-to-binary", "Text to Binary", "Encode text as 8-bit binary.", "Text"),
    ("binary-to-text", "Binary to Text", "Decode binary bytes into readable text.", "Text"),
    ("url-encode", "URL Encoder", "Encode text for use inside URLs.", "Text"),
    ("url-decode", "URL Decoder", "Decode percent-encoded URLs.", "Text"),
    ("base64-encode", "Base64 Encoder", "Encode text to Base64.", "Developer"),
    ("base64-decode", "Base64 Decoder", "Decode Base64 text.", "Developer"),
    # Developer
    ("json-formatter", "JSON Formatter", "Format and validate JSON.", "Developer"),
    ("json-minifier", "JSON Minifier", "Minify JSON for compact output.", "Developer"),
    ("html-escape", "HTML Escape", "Escape HTML special characters.", "Developer"),
    ("html-unescape", "HTML Unescape", "Decode HTML entities.", "Developer"),
    ("hex-converter", "Text to HEX", "Convert text to hexadecimal.", "Developer"),
    ("unix-time", "Unix Timestamp", "Convert Unix timestamps and dates.", "Developer"),
    ("uuid-generator", "UUID Generator", "Generate random UUID v4 identifiers.", "Developer"),
    ("random-string", "Random String", "Generate secure random strings.", "Developer"),
    # Image
    ("image-converter", "Image Converter", "Convert PNG, JPG, WEBP and BMP images.", "Image"),
    ("image-resizer", "Image Resizer", "Resize an image by width and height.", "Image"),
    ("image-compressor", "Image Compressor", "Compress JPG, PNG or WEBP images.", "Image"),
    ("image-grayscale", "Grayscale Image", "Convert an image to grayscale.", "Image"),
    ("image-rotate", "Rotate Image", "Rotate an uploaded image.", "Image"),
    # PDF
    ("pdf-merge", "Merge PDF", "Combine multiple PDF files into one.", "PDF"),
    ("pdf-split", "Split PDF", "Extract selected pages from a PDF.", "PDF"),
    ("pdf-rotate", "Rotate PDF", "Rotate all PDF pages.", "PDF"),
    ("pdf-info", "PDF Information", "Inspect page count and document metadata.", "PDF"),
    ("pdf-text", "PDF Text Extractor", "Extract readable text from a PDF.", "PDF"),
    # Calculators
    ("percentage", "Percentage Calculator", "Calculate percentages and percentage change.", "Calculator"),
    ("gst", "GST Calculator", "Calculate GST-inclusive and exclusive amounts.", "Calculator"),
    ("emi", "EMI Calculator", "Calculate monthly loan EMI.", "Calculator"),
    ("profit-loss", "Profit & Loss", "Calculate profit, loss and percentages.", "Calculator"),
    ("bmi", "BMI Calculator", "Calculate BMI from height and weight.", "Calculator"),
    ("age", "Age Calculator", "Calculate age from date of birth.", "Calculator"),
    ("discount", "Discount Calculator", "Calculate sale price and savings.", "Calculator"),
    ("compound-interest", "Compound Interest", "Calculate compound interest.", "Calculator"),
    ("simple-interest", "Simple Interest", "Calculate simple interest.", "Calculator"),
    ("average", "Average Calculator", "Calculate mean from a list of numbers.", "Calculator"),
    ("unit-converter", "Unit Converter", "Convert common length, weight and data units.", "Calculator"),
    ("temperature", "Temperature Converter", "Convert Celsius, Fahrenheit and Kelvin.", "Calculator"),
    # SEO
    ("keyword-density", "Keyword Density", "Analyze keyword frequency in text.", "SEO"),
    ("meta-tags", "Meta Tag Generator", "Generate basic SEO meta tags.", "SEO"),
    ("robots-txt", "Robots.txt Generator", "Create a simple robots.txt file.", "SEO"),
    ("sitemap", "Sitemap Generator", "Generate an XML sitemap from URLs.", "SEO"),
    ("title-checker", "Title Length Checker", "Check title length for search snippets.", "SEO"),
    # Daily Life
    ("tip-calculator", "Tip Calculator", "Calculate a tip and split a restaurant bill.", "Daily Life"),
    ("split-bill", "Split Bill", "Split a bill fairly between people.", "Daily Life"),
    ("date-difference", "Date Difference", "Find the number of days between two dates.", "Daily Life"),
    ("days-until", "Days Until", "Find how many days remain until a date.", "Daily Life"),
    ("time-duration", "Time Duration", "Calculate the duration between two times.", "Daily Life"),
    ("age-detailed", "Detailed Age", "Calculate age in years, months and days.", "Daily Life"),
    ("fuel-cost", "Fuel Cost Calculator", "Estimate trip fuel cost from distance and mileage.", "Daily Life"),
    ("salary-breakup", "Salary Calculator", "Estimate monthly salary from annual income.", "Daily Life"),
    ("electricity-bill", "Electricity Bill Estimator", "Estimate an electricity bill from units and rate.", "Daily Life"),
    ("vat-calculator", "Tax Calculator", "Calculate tax amount and final price.", "Daily Life"),
    ("pace-calculator", "Pace Calculator", "Calculate running pace from distance and time.", "Daily Life"),
    ("password-strength", "Password Strength", "Check password length and basic strength signals.", "Daily Life"),
    ("text-cleaner", "Text Cleaner", "Remove extra spaces and clean copied text.", "Daily Life"),
    ("csv-to-json", "CSV to JSON", "Convert simple CSV data to JSON.", "Developer"),
    ("json-to-csv", "JSON to CSV", "Convert a JSON array to CSV.", "Developer"),
    # Utilities
    ("qr-generator", "QR Code Generator", "Create a downloadable QR code.", "Utility"),
    ("password-generator", "Password Generator", "Generate strong random passwords.", "Utility"),
    ("random-number", "Random Number", "Generate random numbers in a range.", "Utility"),
    ("countdown", "Countdown Timer", "Run a browser countdown timer.", "Utility"),
    ("color-converter", "Color Converter", "Convert HEX colors to RGB and back.", "Utility"),
    ("timestamp", "Date & Time", "Convert dates and timestamps.", "Utility"),
]

TOOL_MAP = {x[0]: {"slug": x[0], "name": x[1], "description": x[2], "category": x[3]} for x in TOOLS}
CATEGORIES = ["All", "Daily Life", "Text", "Developer", "Image", "PDF", "Calculator", "SEO", "Utility"]

def safe_filename(name, fallback="download.bin"):
    return secure_filename(name or fallback) or fallback

def text_value(name, default=""):
    return request.form.get(name, default).strip()

def result_page(slug, title, data=None, error=None):
    return render_template("tool.html", tool=TOOL_MAP[slug], data=data or {}, error=error)

def send_bytes(data, filename, mimetype):
    bio = io.BytesIO(data)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name=safe_filename(filename), mimetype=mimetype)

@app.route("/")
def index():
    return render_template("index.html", tools=TOOLS, categories=CATEGORIES)

@app.route("/tool/<slug>", methods=["GET", "POST"])
def tool(slug):
    if slug not in TOOL_MAP:
        abort(404)
    if request.method == "GET":
        return result_page(slug, TOOL_MAP[slug]["name"])
    try:
        return handle_tool(slug)
    except Exception as e:
        return result_page(slug, TOOL_MAP[slug]["name"], error=f"Could not process the request: {e}")

@app.route("/api/tools")
def api_tools():
    return jsonify({"tools": TOOLS, "categories": CATEGORIES})

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "Useful Tools"})

def handle_tool(slug):
    if slug == "tip-calculator":
        bill=float(text_value("bill","0")); tip=float(text_value("tip","10")); people=max(1,int(text_value("people","1")))
        total=bill*(1+tip/100); return result_page(slug,"",{"result":f"Tip: {bill*tip/100:.2f} | Total: {total:.2f} | Per person: {total/people:.2f}"})
    if slug == "split-bill":
        total=float(text_value("total","0")); people=max(1,int(text_value("people","1")))
        return result_page(slug,"",{"result":f"Each person pays: {total/people:.2f}"})
    if slug in ("date-difference","days-until"):
        from datetime import date
        if slug=="date-difference":
            a=datetime.strptime(text_value("start"),"%Y-%m-%d").date(); b=datetime.strptime(text_value("end"),"%Y-%m-%d").date()
            return result_page(slug,"",{"result":f"Difference: {abs((b-a).days)} days"})
        target=datetime.strptime(text_value("date"),"%Y-%m-%d").date()
        return result_page(slug,"",{"result":f"Days remaining: {(target-date.today()).days}"})
    if slug == "time-duration":
        a=datetime.strptime(text_value("start"),"%H:%M"); b=datetime.strptime(text_value("end"),"%H:%M")
        if b<a: b+=__import__("datetime").timedelta(days=1)
        return result_page(slug,"",{"result":f"Duration: {b-a}"})
    if slug == "fuel-cost":
        d=float(text_value("distance","0")); m=float(text_value("mileage","1")); price=float(text_value("price","0"))
        return result_page(slug,"",{"result":f"Fuel needed: {d/m:.2f} | Estimated cost: {d/m*price:.2f}"})
    if slug == "salary-breakup":
        annual=float(text_value("annual","0")); return result_page(slug,"",{"result":f"Approx monthly gross: {annual/12:.2f} | Approx yearly: {annual:.2f}"})
    if slug == "electricity-bill":
        units=float(text_value("units","0")); rate=float(text_value("rate","0")); fixed=float(text_value("fixed","0"))
        return result_page(slug,"",{"result":f"Estimated bill: {(units*rate)+fixed:.2f}"})
    if slug == "vat-calculator":
        amount=float(text_value("amount","0")); rate=float(text_value("rate","0")); tax=amount*rate/100
        return result_page(slug,"",{"result":f"Tax: {tax:.2f} | Final price: {amount+tax:.2f}"})
    if slug == "pace-calculator":
        km=float(text_value("distance","1")); mins=float(text_value("minutes","0"))
        pace=mins/km if km else 0; return result_page(slug,"",{"result":f"Pace: {int(pace)} min {int((pace%1)*60):02d} sec/km"})
    if slug == "password-strength":
        s=request.form.get("password",""); score=sum([len(s)>=12, bool(re.search(r"[A-Z]",s)), bool(re.search(r"[a-z]",s)), bool(re.search(r"\d",s)), bool(re.search(r"[^A-Za-z0-9]",s))])
        level=["Very weak","Weak","Fair","Good","Strong","Very strong"][score]
        return result_page(slug,"",{"result":f"Strength: {level} | Length: {len(s)} characters"})
    if slug == "text-cleaner":
        text=request.form.get("text",""); out="\n".join(re.sub(r"[ \t]+"," ",x).strip() for x in text.splitlines())
        return result_page(slug,"",{"output":out})
    if slug == "csv-to-json":
        import csv
        rows=list(csv.DictReader(io.StringIO(request.form.get("text",""))))
        return result_page(slug,"",{"output":json.dumps(rows,indent=2)})
    if slug == "json-to-csv":
        rows=json.loads(request.form.get("text",""))
        if not isinstance(rows,list) or not rows: raise ValueError("Enter a JSON array of objects.")
        keys=sorted({k for r in rows if isinstance(r,dict) for k in r})
        out=io.StringIO(); w=csv.DictWriter(out,fieldnames=keys); w.writeheader(); w.writerows(rows)
        return result_page(slug,"",{"output":out.getvalue()})
    if slug == "word-counter":
        text = request.form.get("text", "")
        words = re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE)
        sentences = len(re.findall(r"[.!?]+(?:\s|$)", text)) or (1 if text.strip() else 0)
        paragraphs = len([p for p in re.split(r"\n\s*\n", text.strip()) if p])
        return result_page(slug, "", {"text": text, "result": f"Words: {len(words)} | Characters: {len(text)} | Sentences: {sentences} | Paragraphs: {paragraphs}"})

    if slug == "case-converter":
        text = request.form.get("text", "")
        mode = text_value("mode", "upper")
        if mode == "upper": out = text.upper()
        elif mode == "lower": out = text.lower()
        elif mode == "title": out = text.title()
        else: out = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1)+m.group(2).upper(), text.lower())
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "remove-duplicates":
        text = request.form.get("text", "")
        seen, out = set(), []
        for line in text.splitlines():
            key = line.strip()
            if key not in seen:
                seen.add(key); out.append(line)
        return result_page(slug, "", {"text": text, "output": "\n".join(out)})

    if slug == "text-reverser":
        text = request.form.get("text", "")
        mode = text_value("mode", "characters")
        if mode == "words": out = " ".join(text.split()[::-1])
        elif mode == "lines": out = "\n".join(text.splitlines()[::-1])
        else: out = text[::-1]
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "find-replace":
        text = request.form.get("text", "")
        find = request.form.get("find", "")
        repl = request.form.get("replace", "")
        if not find: raise ValueError("Enter text to find.")
        out = text.replace(find, repl)
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "slug-generator":
        text = request.form.get("text", "")
        out = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "lorem-ipsum":
        n = min(max(int(request.form.get("count", 3)), 1), 20)
        seed = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Integer posuere, erat a condimentum pretium, justo arcu facilisis nisl, "
                "sed tincidunt neque libero non lorem.")
        out = "\n\n".join(seed for _ in range(n))
        return result_page(slug, "", {"output": out})

    if slug == "sort-lines":
        text = request.form.get("text", "")
        numeric = request.form.get("numeric") == "1"
        lines = text.splitlines()
        if numeric:
            lines.sort(key=lambda x: float(x.strip()) if x.strip().replace(".", "", 1).isdigit() else math.inf)
        else:
            lines.sort(key=str.casefold)
        return result_page(slug, "", {"text": text, "output": "\n".join(lines)})

    if slug == "line-breaks":
        text = request.form.get("text", "")
        out = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "text-to-binary":
        text = request.form.get("text", "")
        out = " ".join(format(b, "08b") for b in text.encode("utf-8"))
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "binary-to-text":
        bits = re.sub(r"[^01]", "", request.form.get("text", ""))
        if len(bits) % 8: raise ValueError("Binary length must be a multiple of 8.")
        out = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8)).decode("utf-8", errors="replace")
        return result_page(slug, "", {"text": bits, "output": out})

    if slug in ("url-encode", "url-decode"):
        from urllib.parse import quote, unquote
        text = request.form.get("text", "")
        out = quote(text, safe="") if slug == "url-encode" else unquote(text)
        return result_page(slug, "", {"text": text, "output": out})

    if slug in ("base64-encode", "base64-decode"):
        text = request.form.get("text", "")
        if slug == "base64-encode":
            out = base64.b64encode(text.encode()).decode()
        else:
            out = base64.b64decode(text.encode(), validate=True).decode("utf-8", errors="replace")
        return result_page(slug, "", {"text": text, "output": out})

    if slug in ("json-formatter", "json-minifier"):
        text = request.form.get("text", "")
        obj = json.loads(text)
        out = json.dumps(obj, ensure_ascii=False, indent=None if slug.endswith("minifier") else 2, separators=(",", ":") if slug.endswith("minifier") else None)
        return result_page(slug, "", {"text": text, "output": out})

    if slug in ("html-escape", "html-unescape"):
        import html
        text = request.form.get("text", "")
        out = html.escape(text) if slug.endswith("escape") else html.unescape(text)
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "hex-converter":
        text = request.form.get("text", "")
        out = text.encode().hex(" ")
        return result_page(slug, "", {"text": text, "output": out})

    if slug == "unix-time":
        value = request.form.get("value", "")
        if value:
            ts = int(value)
            out = datetime.fromtimestamp(ts).astimezone().isoformat()
        else:
            out = str(int(time.time()))
        return result_page(slug, "", {"output": out})

    if slug == "uuid-generator":
        out = str(uuid.uuid4())
        return result_page(slug, "", {"output": out})

    if slug == "random-string":
        length = min(max(int(request.form.get("length", 16)), 1), 256)
        alphabet = string.ascii_letters + string.digits
        out = "".join(secrets.choice(alphabet) for _ in range(length))
        return result_page(slug, "", {"output": out})

    # Image tools
    if slug.startswith("image-"):
        file = request.files.get("file")
        if not file or not file.filename:
            raise ValueError("Choose an image file.")
        img = Image.open(file.stream)
        img = ImageOps.exif_transpose(img)
        if slug == "image-converter":
            fmt = text_value("format", "PNG").upper()
            if fmt == "JPG" and img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, "white"); bg.paste(img, mask=img.getchannel("A")); img = bg
            if fmt == "JPG": fmt = "JPEG"
            buf = io.BytesIO(); img.save(buf, format=fmt, quality=90, optimize=True); ext = "jpg" if fmt == "JPEG" else fmt.lower()
            return send_bytes(buf.getvalue(), f"converted.{ext}", f"image/{'jpeg' if fmt == 'JPEG' else ext}")
        if slug == "image-resizer":
            w = int(request.form.get("width", img.width)); h = int(request.form.get("height", img.height))
            w = min(max(w, 1), 6000); h = min(max(h, 1), 6000)
            img = img.resize((w, h), Image.Resampling.LANCZOS)
        elif slug == "image-compressor":
            fmt = "JPEG" if img.mode not in ("RGB", "L") else "JPEG"
            img = img.convert("RGB")
            buf = io.BytesIO(); img.save(buf, "JPEG", quality=min(max(int(request.form.get("quality", 70)), 10), 95), optimize=True)
            return send_bytes(buf.getvalue(), "compressed.jpg", "image/jpeg")
        elif slug == "image-grayscale":
            img = ImageOps.grayscale(img)
        elif slug == "image-rotate":
            angle = float(request.form.get("angle", 90))
            img = img.rotate(-angle, expand=True)
        buf = io.BytesIO()
        out_fmt = "PNG" if img.mode in ("RGBA", "LA") else "JPEG"
        if out_fmt == "JPEG": img = img.convert("RGB")
        img.save(buf, out_fmt, quality=90)
        return send_bytes(buf.getvalue(), f"result.{out_fmt.lower()}", f"image/{'jpeg' if out_fmt == 'JPEG' else 'png'}")

    # PDF tools
    if slug == "pdf-merge":
        files = request.files.getlist("files")
        if not files: raise ValueError("Choose at least one PDF.")
        writer = PdfWriter()
        for f in files:
            reader = PdfReader(f.stream)
            for page in reader.pages: writer.add_page(page)
        out = io.BytesIO(); writer.write(out)
        return send_bytes(out.getvalue(), "merged.pdf", "application/pdf")

    if slug in ("pdf-split", "pdf-rotate", "pdf-info", "pdf-text"):
        f = request.files.get("file")
        if not f or not f.filename: raise ValueError("Choose a PDF.")
        reader = PdfReader(f.stream)
        if slug == "pdf-info":
            meta = reader.metadata or {}
            output = f"Pages: {len(reader.pages)}\nTitle: {meta.get('/Title','')}\nAuthor: {meta.get('/Author','')}\nSubject: {meta.get('/Subject','')}"
            return result_page(slug, "", {"output": output})
        if slug == "pdf-text":
            output = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            return result_page(slug, "", {"output": output})
        writer = PdfWriter()
        if slug == "pdf-split":
            pages = text_value("pages", "1")
            selected = []
            for part in pages.split(","):
                if "-" in part:
                    a,b = part.split("-",1); selected.extend(range(int(a), int(b)+1))
                else: selected.append(int(part))
            for p in selected:
                if 1 <= p <= len(reader.pages): writer.add_page(reader.pages[p-1])
        else:
            angle = int(request.form.get("angle", 90)) % 360
            for page in reader.pages:
                page.rotate(angle)
                writer.add_page(page)
        out = io.BytesIO(); writer.write(out)
        return send_bytes(out.getvalue(), "result.pdf", "application/pdf")

    # Calculators
    if slug == "percentage":
        a,b = float(request.form["a"]), float(request.form["b"])
        return result_page(slug, "", {"output": f"{b:g}% of {a:g} = {a*b/100:g}\nPercentage change = {(b-a)/a*100:g}%" if a else f"{b:g}% of {a:g} = 0"})
    if slug == "gst":
        amount, rate = float(request.form["amount"]), float(request.form["rate"])
        mode = request.form.get("mode","add")
        gst = amount*rate/100
        total = amount+gst if mode=="add" else amount
        base = amount/(1+rate/100) if mode=="remove" else amount
        gst2 = amount-base if mode=="remove" else gst
        return result_page(slug, "", {"output": f"Base amount: {base:.2f}\nGST: {gst2:.2f}\nTotal: {total:.2f}"})
    if slug == "emi":
        p,r,n = float(request.form["principal"]), float(request.form["rate"])/1200, float(request.form["months"])
        emi = p/n if r==0 else p*r*(1+r)**n/((1+r)**n-1)
        return result_page(slug, "", {"output": f"Monthly EMI: {emi:.2f}\nTotal payment: {emi*n:.2f}\nInterest: {emi*n-p:.2f}"})
    if slug == "profit-loss":
        cost,sell = float(request.form["cost"]), float(request.form["sell"])
        diff=sell-cost
        pct=abs(diff)/cost*100 if cost else 0
        return result_page(slug, "", {"output": f"{'Profit' if diff>=0 else 'Loss'}: {abs(diff):.2f}\nPercentage: {pct:.2f}%"})
    if slug == "bmi":
        kg,cm=float(request.form["weight"]),float(request.form["height"])
        bmi=kg/((cm/100)**2)
        cat="Underweight" if bmi<18.5 else "Normal range" if bmi<25 else "Overweight" if bmi<30 else "Obesity"
        return result_page(slug, "", {"output": f"BMI: {bmi:.2f}\nCategory: {cat}"})
    if slug == "age":
        dob=datetime.strptime(request.form["dob"], "%Y-%m-%d").date()
        today=datetime.now().date()
        years=today.year-dob.year-((today.month,today.day)<(dob.month,dob.day))
        return result_page(slug, "", {"output": f"Age: {years} years"})
    if slug == "discount":
        price,disc=float(request.form["price"]),float(request.form["discount"])
        save=price*disc/100
        return result_page(slug, "", {"output": f"Savings: {save:.2f}\nFinal price: {price-save:.2f}"})
    if slug in ("compound-interest","simple-interest"):
        p=float(request.form["principal"]); r=float(request.form["rate"]); t=float(request.form["years"])
        if slug=="simple-interest":
            interest=p*r*t/100; total=p+interest
        else:
            n=float(request.form.get("times",1)); total=p*(1+r/(100*n))**(n*t); interest=total-p
        return result_page(slug, "", {"output": f"Interest: {interest:.2f}\nTotal: {total:.2f}"})
    if slug == "average":
        nums=[float(x) for x in re.split(r"[,\s]+",request.form["numbers"].strip()) if x]
        if not nums: raise ValueError("Enter numbers.")
        return result_page(slug, "", {"output": f"Count: {len(nums)}\nAverage: {sum(nums)/len(nums):g}"})
    if slug == "unit-converter":
        value=float(request.form["value"]); unit=request.form["unit"]
        factors={"m-to-ft":3.280839895,"ft-to-m":0.3048,"km-to-mi":0.621371192,"mi-to-km":1.609344,"kg-to-lb":2.20462262,"lb-to-kg":0.45359237,"mb-to-gb":1/1024,"gb-to-mb":1024}
        if unit not in factors: raise ValueError("Choose a conversion.")
        return result_page(slug, "", {"output": f"{value:g} → {value*factors[unit]:g}"})
    if slug == "temperature":
        value=float(request.form["value"]); unit=request.form["unit"]
        if unit=="c-f": out=value*9/5+32
        elif unit=="f-c": out=(value-32)*5/9
        elif unit=="c-k": out=value+273.15
        elif unit=="k-c": out=value-273.15
        else: out=value
        return result_page(slug, "", {"output": f"Result: {out:g}"})

    # SEO
    if slug == "keyword-density":
        text=request.form["text"].lower()
        words=re.findall(r"\b[a-z0-9]+\b",text)
        counts={}
        for w in words: counts[w]=counts.get(w,0)+1
        top=sorted(counts.items(),key=lambda x:x[1],reverse=True)[:15]
        output="\n".join(f"{w}: {c} ({c/len(words)*100:.2f}%)" for w,c in top) if words else "No words."
        return result_page(slug, "", {"output": output})
    if slug == "meta-tags":
        title=request.form["title"]; desc=request.form["description"]; keywords=request.form["keywords"]
        output=f'<title>{title}</title>\n<meta name="description" content="{desc}">\n<meta name="keywords" content="{keywords}">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        return result_page(slug, "", {"output": output})
    if slug == "robots-txt":
        site=request.form["site"].rstrip("/")
        output=f"User-agent: *\nAllow: /\nSitemap: {site}/sitemap.xml"
        return result_page(slug, "", {"output": output})
    if slug == "sitemap":
        urls=[x.strip() for x in request.form["urls"].splitlines() if x.strip()]
        xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in urls: xml += f"  <url><loc>{u}</loc></url>\n"
        xml += "</urlset>"
        return result_page(slug, "", {"output": xml})
    if slug == "title-checker":
        title=request.form["title"]; n=len(title)
        status="Good" if 30<=n<=60 else "Consider adjusting"
        return result_page(slug, "", {"output": f"Characters: {n}\nStatus: {status}"})

    # Daily Life
    ("tip-calculator", "Tip Calculator", "Calculate a tip and split a restaurant bill.", "Daily Life"),
    ("split-bill", "Split Bill", "Split a bill fairly between people.", "Daily Life"),
    ("date-difference", "Date Difference", "Find the number of days between two dates.", "Daily Life"),
    ("days-until", "Days Until", "Find how many days remain until a date.", "Daily Life"),
    ("time-duration", "Time Duration", "Calculate the duration between two times.", "Daily Life"),
    ("age-detailed", "Detailed Age", "Calculate age in years, months and days.", "Daily Life"),
    ("fuel-cost", "Fuel Cost Calculator", "Estimate trip fuel cost from distance and mileage.", "Daily Life"),
    ("salary-breakup", "Salary Calculator", "Estimate monthly salary from annual income.", "Daily Life"),
    ("electricity-bill", "Electricity Bill Estimator", "Estimate an electricity bill from units and rate.", "Daily Life"),
    ("vat-calculator", "Tax Calculator", "Calculate tax amount and final price.", "Daily Life"),
    ("pace-calculator", "Pace Calculator", "Calculate running pace from distance and time.", "Daily Life"),
    ("password-strength", "Password Strength", "Check password length and basic strength signals.", "Daily Life"),
    ("text-cleaner", "Text Cleaner", "Remove extra spaces and clean copied text.", "Daily Life"),
    ("csv-to-json", "CSV to JSON", "Convert simple CSV data to JSON.", "Developer"),
    ("json-to-csv", "JSON to CSV", "Convert a JSON array to CSV.", "Developer"),
    # Utilities
    if slug == "qr-generator":
        data=request.form["data"]
        img=qrcode.make(data)
        buf=io.BytesIO(); img.save(buf,"PNG")
        return send_bytes(buf.getvalue(),"qr-code.png","image/png")
    if slug == "password-generator":
        length=min(max(int(request.form.get("length",16)),8),128)
        alphabet=string.ascii_letters+string.digits+"!@#$%^&*_-+="
        out="".join(secrets.choice(alphabet) for _ in range(length))
        return result_page(slug, "", {"output": out})
    if slug == "random-number":
        a=int(request.form["min"]); b=int(request.form["max"])
        if a>b: a,b=b,a
        return result_page(slug, "", {"output": str(secrets.randbelow(b-a+1)+a)})
    if slug == "color-converter":
        value=request.form["color"].strip().lstrip("#")
        if len(value)!=6: raise ValueError("Use a 6-digit HEX color.")
        r,g,b=int(value[:2],16),int(value[2:4],16),int(value[4:],16)
        return result_page(slug, "", {"output": f"HEX: #{value.upper()}\nRGB: rgb({r}, {g}, {b})"})
    if slug == "timestamp":
        value=request.form.get("value","")
        if value:
            ts=int(value); out=datetime.fromtimestamp(ts).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        else: out=str(int(time.time()))
        return result_page(slug, "", {"output": out})

    raise ValueError("This tool is not implemented.")

@app.errorhandler(413)
def too_large(_):
    return render_template("404.html", message="File too large. Maximum upload size is 25 MB."), 413

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", message="The page or tool was not found."), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

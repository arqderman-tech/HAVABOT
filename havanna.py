import requests, re, os, json
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

URLS = [
    "https://tienda.havanna.com.ar/alfajores/",
    "https://www.tienda.havanna.com.ar/havannets/",
    "https://www.tienda.havanna.com.ar/chocolates/"
]
DOLAR_URL = "https://api.comparadolar.ar/usd"
CSV = "havanna_precios.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def obtener_dolar():
    try:
        bn = next((x for x in requests.get(DOLAR_URL, timeout=10).json() if x.get("slug") == "banco-nacion"), None)
        return float(bn["ask"]) if bn else 1.0
    except Exception:
        return 1.0

def inferir_categoria(nombre):
    n = str(nombre).lower()
    if "alfajor" in n: return "Alfajores"
    if "havannet" in n: return "Havannets"
    if "chocolate" in n or "bombon" in n: return "Chocolates"
    if "turron" in n: return "Turrones"
    if "caja" in n or "pack" in n or "surtido" in n: return "Cajas y Packs"
    return "Otros"

def extraer_unidades(nombre):
    m = re.search(r"x\s*(\d+)(?:uds)", nombre, re.IGNORECASE)
    return int(m.group(1)) if m else 1

def scrape_url(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.content, "html.parser")
    for script in soup.find_all("script"):
        if script.string and "const googleItems = [" in script.string:
            m = re.search(r"const googleItems = (.*?);", script.string, re.DOTALL)
            if m:
                return json.loads(m.group(1).strip())
    return []

def main():
    print("HAVANNABOT iniciando...")
    dolar = obtener_dolar()
    print("Dolar: " + str(dolar))
    hoy = datetime.now().strftime("%Y-%m-%d")
    vistos = set()
    rows = []
    for url in URLS:
        try:
            items = scrape_url(url)
            label = url.rstrip("/").split("/")[-1]
            print("  " + label + ": " + str(len(items)) + " items")
            for item in items:
                nombre = item["info"]["item_name"]
                if nombre in vistos: continue
                vistos.add(nombre)
                precio_pkg = float(item["info"]["price"])
                uds = extraer_unidades(nombre)
                precio_u = precio_pkg / uds if uds > 1 else precio_pkg
                rows.append({"Fecha": hoy, "Categoria": inferir_categoria(nombre), "Producto": nombre,
                             "Precio_ARS": round(precio_u, 2), "Precio_USD": round(precio_u / dolar, 2),
                             "Dolar_ARS": dolar})
        except Exception as e:
            print("  Error " + url + ": " + str(e))
    if not rows:
        print("Sin productos."); return
    df = pd.DataFrame(rows)
    if os.path.exists(CSV):
        dh = pd.read_csv(CSV)
        dh["Fecha"] = pd.to_datetime(dh["Fecha"]).dt.strftime("%Y-%m-%d")
        dh = dh[dh["Fecha"] != hoy]
        df = pd.concat([dh, df], ignore_index=True)
    df.to_csv(CSV, index=False)
    print("OK: " + str(len(rows)) + " productos para " + hoy)

if __name__ == "__main__":
    main()

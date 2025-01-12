import gspread
import os
import threading
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

# read credentials from env, then write it to google-credentials.json
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if credentials_json:
    with open(os.path.join("resources", "google-credentials.json"), "w") as f:
        f.write(credentials_json)

creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join("resources", "google-credentials.json"), scope)
client = gspread.authorize(creds)

def addRow(casier, item, quantite, nom):
    if quantite:
        categ = item.split()[0]
        sheet = client.open("Inventaire").get_worksheet_by_id(0)

        ajout = "" if quantite < 0 else quantite
        retrait = "" if quantite > 0 else -1 * quantite
        worker = lambda: sheet.append_row(["", datetime.today().strftime('%d-%m-%Y'), item, categ, ajout, retrait, casier, nom], table_range="B3:I3")

        #lancement dans un thread pour aller plus vite
        thread = threading.Thread(target=worker)
        thread.start()

def readInv():
    sheet = client.open("Inventaire").get_worksheet_by_id(749275013)
    getCell = lambda rowId, colId: sheet.cell(rowId, colId).value

    inv = dict()

    #get the cells
    table = sheet.batch_get(["A2:H20"])[0]

    for colId, colItem in enumerate(table[0][1:]):
        colId += 1 #décalage de 1 à cause du [1:]
        inv[colItem] = {row[0]: int(cell) for row in table[1:] if colId < len(row) and (cell := row[colId]) not in ('0', '')}
    
    return inv
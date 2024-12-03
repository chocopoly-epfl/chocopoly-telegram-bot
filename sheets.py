import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

# read credentials from env, then write it to google-credentials.json
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
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
        sheet.append_row(["", datetime.today().strftime('%d-%m-%Y'), item, categ, ajout, retrait, casier, nom], table_range="B3:I3")

def readInv():
    sheet = client.open("Inventaire").get_worksheet_by_id(749275013)
    getCell = lambda rowId, colId: sheet.cell(rowId, colId).value

    inv = dict()

    #get the cells
    table = sheet.batch_get(["A2:H20"])
    nbCols = 7

    for colId in range(nbCols):
        colItem = table[0][colId]
        if colItem:
            inv[colItem] = {row[0]: cell for row in table if (cell := row[colId]) != '0'}
        else:
            break
    
    """
    for colId in range(2, 8+1):
        colItem = getCell(2, colId)
        if colItem:
            inv[colItem] = {getCell(rowId, 1): cell for rowId in range(3, 12+1) if (cell := getCell(rowId, colId)) != '0'}
        else:
            break
    """
    
    return inv
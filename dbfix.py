import fitz
import uuid
from pathlib import Path
import pandas as pd

def get_uid_and_nip(file:Path):
    doc = fitz.open(file)
    text = ""
    for page in doc:
        text+=page.get_text()
    pieces = text.split()
    for piece in pieces:
        try:
            uid = uuid.UUID(piece)
        except ValueError:
            uid=None
        else:
            break
    for piece in pieces:
        nip = piece
        if nip.isdigit() and len(nip) == 6:
            break
        else:
            nip = None
    try:
        ret = {int(nip):uid}
    except:
        ret = {None:uid}
    return ret

if __name__ == '__main__':
    base_path = Path('F:\TarjetasPlazoleta\codebase\output_cards')
    data_list = {}
    for file in base_path.glob('*.pdf'):
        data = get_uid_and_nip(file)
        print(file.name, ' --> ', data)
        data_list = data_list | data
    database = 'database.xlsx'
    db = pd.read_excel(database)
    db['uuid'] = db['NIP Unizar'].map(data_list).fillna(db['uuid'])
    print(db['NIP Unizar'].map(data_list).fillna(db['uuid']))
    db.to_excel(database, index=False)
    

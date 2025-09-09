from registration.cardgenerator.cardgenerator import generate_card, CardOptions
from registration.cardgenerator.qrshow import show_qr_codes
import pandas as pd
from pathlib import Path
from uuid import uuid4

db = pd.read_excel('database.xlsx')
to_generate = db.loc[db['NIP Unizar'] > 900000]



for _, row in to_generate.iterrows():
    # generate_card(
    #     str(Path('output_cards') / (str(row['NIP Unizar']) + '.pdf')),  # pyright: ignore[reportArgumentType]
    #     row['Fotografia'],
    #     row['uuid'],
    #     str(row['Nombre']),
    #     str(row['Apellidos']),
    #     str(row['NIP Unizar']),
    #     str(row['Estudios Matriculados']),
    #     )
    generate_card(
        'test0.pdf',
        'images/croped/0.png',
        uuid4(),
        'Laia',
        'Apellido1 Apellido2',
        '000000',
        'PDI / PAS',
        CardOptions()
        )
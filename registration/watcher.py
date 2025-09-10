from pathlib import Path
import shutil
from registration.sheets_connector import create_sheets_service
from registration import imageparser as im
import pandas as pd
import face_detection
import cv2
import uuid
from datetime import datetime


DETECTOR = face_detection.build_detector(
        "DSFDDetector",
        max_resolution=1080,
        confidence_threshold=.5, 
        nms_iou_threshold=.3
    )


def sheets_watcher(service, sheet_id, database):

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=sheet_id, range='A1:H')
        .execute()
    )
    values = result.get("values", [])
    print('Got sheet response')
    df = pd.DataFrame(values[1:], columns = values[0])
    df['NIP Unizar'] = pd.to_numeric(df['NIP Unizar'], downcast='integer', errors='coerce')
    if not database.exists():
        print('No db found. creating one...')
        db = pd.DataFrame([], columns = values[0] + ['uuid'])
    else:
        shutil.copy(database, f'database_{datetime.today().strftime("%d%m%Y%H%M")}.xlsx.backup')
        db = pd.read_excel(database, header=0)
    new_nips = set(df['NIP Unizar'].to_list()) - set(db['NIP Unizar'].to_list())
    print('Found the following new NIPs:', new_nips)
    if new_nips:
        new_rows = df[df['NIP Unizar'].isin(new_nips)].copy()  # pyright: ignore[reportArgumentType]
        new_rows = normalize_image(new_rows)  # pyright: ignore[reportArgumentType]
        new_rows = validate_and_normalize_data(new_rows)
        new_rows = assign_uuid(new_rows)
        db = pd.concat([db, new_rows[~(new_rows.isnull().any(axis=1))]])
    new_rows[(new_rows.isnull().any(axis=1))].to_excel('nulls.xlsx', index=False)
    db.to_excel(database, index=False)
    
def validate_and_normalize_data(df:pd.DataFrame)->pd.DataFrame:
    # "Nombre","Apellidos","Fecha de Nacimiento",
    # "Teléfono","Email","NIP Unizar","Estudios Matriculados",
    # "Fotografia","Tratamiento de Datos"
    df['Nombre'] = df['Nombre'].str.title()
    df['Apellidos'] = df['Apellidos'].str.title()
    #df.loc[df['Apellidos'].str.split().str.len() < 2, 'Apellidos'] = None
    #df[df['Fecha de Nacimiento']]
    #TODO: Recast to str?
    #df.loc[~(df['NIP Unizar'].str.len() == 6), 'NIP Unizar'] = None #FIXME
    return df

def normalize_image(df:pd.DataFrame)->pd.DataFrame:
    files = im.download_images(df)
    output_size = (413,531)
    output_files = []
    for image in files:
        output_image = Path("images/croped") / image.name.replace(image.suffix, '.png')
        if output_image.exists():
            print(image.name, 'Already normalized. Skipping...')
            output_files.append(output_image)
        else:
            print('Normalizing ', image.name)
            try:
                dets = im.detect_face(image, detector=DETECTOR)
                face = dets[0, :]
                cropped = im.crop_image(image, face, output_size=output_size)
            except:
                print("No faces for image ", image.name)
                output_files.append(None)
            else:
                cv2.imwrite(output_image , cropped)
                output_files.append(output_image)
    df['Fotografia'] = output_files
    return df

def assign_uuid(df:pd.DataFrame):
    df['uuid'] = [str(uuid.uuid4()) for i in range(0,len(df))]
    return df


if __name__ == '__main__':
    credentials = Path(r"credentials.json")
    token = Path(r"token.json")
    sheet_id = '1neWaw0rKhIBjZbc8ZmsJwFyf2vMVpeN6ifqYwcKGS1U'
    database = Path(r"database.xlsx")
    print("Creating service...")
    service = create_sheets_service(credentials, token)
    if not service:
        raise Exception("No service Created!")
    else:
        sheets_watcher(service, sheet_id, database)
import cv2
import face_detection
import requests as req
import pandas as pd
from pathlib import Path

from torch._prims_common import elementwise_dtypes


database_file = "/home/steve/Projects/TarjetasPlazoleta/opnform/tarjetas-plazoleta-veterinaria-i41yoc-1756572978321-submissions.csv"

def detect_face(image:Path, detector):
    img = cv2.imread(image)
    dets = detector.detect(
            img[:, :, ::-1]
        )[:, :4]
    return dets


def draw_face(im, bbox, window_name = 'preview'):
    im = im.copy()
    x0, y0, x1, y1 = [int(_) for _ in bbox]
    cv2.rectangle(im, (x0, y0), (x1, y1), (0, 0, 255), 5)
    #im = cv2.resize(im, (1000, 1000))
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, im)
    while True:
        if cv2.waitKey(1) == 13:
            cv2.destroyAllWindows()
            break


def crop_image(image, face, output_size = (250, 250), percent_inc = 75): 
    image = cv2.imread(image)
    output_ratio  = output_size[1] / output_size[0]
    #draw_faces(image, (face[0], face[1], face[2], face[3]), window_name='torch_output')
    real_inc_x = (face[2] - face[0]) * (1 + (percent_inc * 0.01))
    real_inc_y = (face[3] - face[1]) * (1 + (percent_inc * 0.01))
    diff_x = (real_inc_x - (face[2] - face[0])) / 2
    diff_y = (real_inc_y - (face[3] - face[1])) / 2
    xmin = face[0] - diff_x
    ymin = face[1] - diff_y
    xmax = face[2] + diff_x
    ymax = face[3] + diff_y
    #draw_faces(image, (xmin, ymin, xmax, ymax), window_name='increase 25%')
    w = (xmax-xmin)
    h = (ymax-ymin)
    if w>h:
        diference = ( (w * output_ratio) - h ) / 2
        ymin = ymin - diference
        ymax = ymax + diference
    else:
        diference = ( (h / output_ratio) - w ) / 2
        xmin = xmin - diference
        xmax = xmax + diference
    #draw_faces(image, (xmin, ymin, xmax, ymax), window_name='Adapt to ratio')
    maxh, maxw = image.shape[:2]
    crop_img = image[
        max(int(ymin), 0):min(int(ymax), maxh), 
        max(int(xmin), 0):min(int(xmax), maxw)
        ]
    #draw_faces(crop_img, (0, 0, 0, 0), window_name='Adapt to ratio')
    cropped = cv2.resize(crop_img, output_size)
    return cropped
    

def download_images(database_file:Path | pd.DataFrame):
    if not type(database_file) == pd.DataFrame :
        db  = pd.read_csv(database_file)
    else:
        db = database_file
    base_folder = Path("images/base")
    files = []
    for index, row in db.iterrows():
        nip = row['NIP Unizar']
        image = row['Fotografia']
        file_extension = image.split('?signature')[0].split('.')[-1]
        file_name = str(nip) + '.' + file_extension
        output_file = base_folder / file_name
        if output_file.exists():
            print(nip, 'exists. Skipping...')
        else:
            print(nip)
            response = req.get(image)
            output_file.write_bytes(response.content)
        files.append(output_file)
    return files


if __name__ == '__main__':
    #download_images(Path(r"F:\tarjetas-plazoleta-veterinaria-i41yoc-1756807830330-submissions.csv"))
    detector = face_detection.build_detector(
        "DSFDDetector",
        max_resolution=1080,
        confidence_threshold=.5, 
        nms_iou_threshold=.3
    )
    output_size = (413,531)
    for image in Path('images/base/').glob('*'):
            try:
                dets = detect_face(image, detector)
                face = dets[0, :]
                cropped = crop_image(image, face, output_size=output_size)
            except:
                print("No faces for image ", image.name)
            else:
                cv2.imwrite(Path("images/croped") / image.name.replace(image.suffix, '.png') , cropped)  # pyright: ignore[reportArgumentType]
            
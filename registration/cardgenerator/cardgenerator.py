from reportlab.pdfgen import canvas as canv
from reportlab.lib.units import mm
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import (ParagraphStyle, getSampleStyleSheet)
from reportlab.platypus import Paragraph
from uuid import UUID
from typing import Literal
from dataclasses import dataclass


@dataclass
class CardOptions:
    background: Literal['emerald', 'silver', 'ruby', 'gold'] = "emerald"

def register_font(ttf_file:Path):
    font_name= ttf_file.name.removesuffix(ttf_file.suffix)
    pdfmetrics.registerFont(TTFont(font_name, ttf_file))


#RESOURCES = Path('/run/media/steve/Data/TarjetasPlazoleta/codebase/registration/cardgenerator/resources')
#RESOURCES = Path('/home/steve/Projects/TarjetasPlazoleta/codebase/registration/cardgenerator/resources')
RESOURCES = Path(r'F:\TarjetasPlazoleta\codebase\registration\cardgenerator\resources')
FONTS = [ 
    RESOURCES / 'Roboto_Mono' / 'static' / 'RobotoMono-Medium.ttf',
    RESOURCES / 'Inter' / 'extras' / 'ttf' / 'Inter-ExtraBold.ttf',
    RESOURCES / 'Inter' / 'extras' / 'ttf' / 'Inter-ExtraLight.ttf',
    ]
for font in FONTS:
    register_font(font)


def generate_card(
    output_file:Path, profile_picture:Path, serial_number:UUID, 
    name:str, surname:str, nip:str, department:str,
    cardoptions:CardOptions
    ):

    canvas = canv.Canvas(
        output_file, 
        pagesize=(85*mm,54*mm)
        )

    # Background image 
    match cardoptions.background:
        case 'emerald':
            background_image = RESOURCES / 'emerald_card.jpg'
        case 'silver':
            background_image = RESOURCES / 'silver_card.jpg'
        case 'ruby':
            background_image = RESOURCES / 'ruby_card.jpg'
        case 'gold':
            background_image = RESOURCES / 'gold_card.jpg'
        
    canvas.drawImage(
        background_image,
        0,0, 
        width=85*mm,height=54*mm,
        )

    # Vet logo
    logo_width = 36.8
    logo_ratio= 443 / float(1631)
    canvas.drawImage(
        RESOURCES / 'logo_vet.png',
        5*mm,39*mm, 
        width=logo_width*mm, 
        height=(logo_width*logo_ratio)*mm,
        preserveAspectRatio=True,
        mask='auto',
        )

    # Profile Picture
    logo_width = 36.8
    logo_ratio= 443 / float(1631)
    frame = RESOURCES / 'frame.png'
    match cardoptions.background:
        case 'emerald':
            canvas.setStrokeColorCMYK(0.8,0.0,0.45,0.2)
        case 'silver':
            canvas.setStrokeColorCMYK(0.2,0.15,0.15,0.4)
        case 'ruby':
            canvas.setStrokeColorCMYK(0.,.9,0.9,0.3)
        case 'gold':
            canvas.setStrokeColorCMYK(0.2,0.3,0.85,0.15)
    
    # draw some lines
    canvas.line(49.1*mm,11*mm,74*mm,11*mm)
    canvas.line(49.1*mm,43*mm,74*mm,43*mm)
    canvas.line(49.1*mm,11*mm,49.1*mm,43*mm)
    canvas.line(74*mm,11*mm,74*mm,43*mm)
    canvas.drawImage(
        profile_picture ,
        49.6*mm,11.5*mm, 
        width=23.9*mm, 
        height=31*mm,
        )

    # Serial Number
    canvas.setFont('RobotoMono-Medium', 6)
    canvas.drawRightString(74*mm, 5*mm, str(serial_number).upper())

    # Personal Details
    p1 = name + ' ' + surname + '<br />\n' + nip
    default_style = getSampleStyleSheet()
    p1_style = ParagraphStyle('name_and_nip',
                            parent=default_style['Normal'],
                            fontName="Inter-ExtraBold",
                            fontSize=8,
                            )
    p2_style = ParagraphStyle('department',
                            parent=default_style['Normal'],
                            fontName="Inter-ExtraLight",
                            fontSize=7,
                            )
    P1=Paragraph(p1,p1_style)
    P1.wrap(38*mm, 7*mm)
    P1.drawOn(canvas,8*mm,21*mm)
    P2=Paragraph(department,p2_style)
    P2.wrap(38*mm, 7*mm)
    P2.drawOn(canvas,8*mm,12*mm)

    canvas.showPage()
    canvas.save()

    return output_file
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import qrcode
from pathlib import Path
import os
import subprocess
import ndef
import struct
import io
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toHexString
from smartcard.CardConnection import CardConnection
import pandas as pd
from typing import Dict, Any, List
import datetime

# --- Ingress Logic from PostgreSQL Function ---
def ingress_logic(uuid: str, action: int, df_ingress: pd.DataFrame, df_student_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Translates the PostgreSQL ingress function logic into Python.

    Args:
        uuid (str): The unique ID of the card.
        action (int): 1 for entry, 0 for exit.
        df_ingress (pd.DataFrame): DataFrame loaded from INGRESS.xlsx.
        df_student_data (pd.DataFrame): DataFrame loaded from database.xlsx.

    Returns:
        Dict[str, Any]: A dictionary with the result of the access control check.
    """
    # Fetch student data for display regardless of access result
    student_data = df_student_data[df_student_data['uuid'] == uuid]
    student_data_dict = student_data.iloc[0].to_dict() if not student_data.empty else None

    # Rule 0: Check input and if user exists
    if not uuid or action is None:
        return {'result': 'DENIED', 'message': 'DENIED - Invalid input', 'student_data': None}
    
    # Check if the user exists in the INGRESS DataFrame
    ingress_user_data = df_ingress[df_ingress['uuid'] == uuid]
    if ingress_user_data.empty:
        return {'result': 'DENIED', 'message': 'DENIED - User not found in access control list', 'student_data': student_data_dict}
    
    # Get the latest INGRESS data for the user
    ingress_user_row = ingress_user_data.iloc[0]
    v_last_change = pd.to_datetime(ingress_user_row['last_change'])
    v_status = ingress_user_row['status']

    # Rule 1: Check if last_change is older than 1 minute
    one_minute_ago = datetime.datetime.now() - datetime.timedelta(minutes=1)
    if v_last_change > one_minute_ago:
        return {'result': 'DENIED', 'message': 'DENIED - Too soon, try again later', 'student_data': student_data_dict}
    
    # Rule 2: Check bitwise operation (as interpreted)
    if action == 1 and v_status == 1:
        return {'result': 'DENIED', 'message': 'DENIED - Already inside', 'student_data': student_data_dict}
    
    if action == 0 and v_status == 0:
        return {'result': 'OK', 'message': 'OK - Already outside', 'student_data': student_data_dict}

    # All rules successful - perform update
    df_ingress.loc[ingress_user_data.index, 'status'] = action
    df_ingress.loc[ingress_user_data.index, 'last_change'] = datetime.datetime.now()
    
    # Save the updated DataFrame back to the Excel file
    df_ingress.to_excel('INGRESS.xlsx', index=False)

    return {'result': 'OK', 'message': 'OK', 'student_data': student_data_dict}


# A function to generate and display the QR code
def show_qr(uuid_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uuid_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

# A function to show a preview of the PDF
def show_pdf_preview(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        # Render the page as a high-resolution image
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    except Exception as e:
        print(f"Error loading PDF preview: {e}")
        return None

def ndef_decode(message_bytes):
    """
    Decodes an NDEF message from a bytes object and extracts the text payload.
    It handles the specific format of NFC Forum Text Records.
    
    Args:
        message_bytes (bytes): A bytes object containing the raw NDEF message.

    Returns:
        str or None: The decoded text string, or None if the message is malformed or not a Text Record.
    """
    try:
        # We process the stream until the end marker is found.
        stream = io.BytesIO(message_bytes)
        
        # Check for NFC Forum Tag TLV structure (Type 0x03 = NDEF message)
        tag_tlv_type = stream.read(1)
        if tag_tlv_type != b'\x03':
            return None
        
        # Read the NDEF message length from the TLV
        ndef_message_length_byte = stream.read(1)
        if not ndef_message_length_byte:
            return None
        
        # Read the first byte which contains the flags
        header = stream.read(1)
        if not header:
            return None
        
        flags = struct.unpack('>B', header)[0]
        
        sr = (flags >> 4) & 1  # Short Record
        il = (flags >> 3) & 1  # ID Length

        # Get the type length (1 byte)
        type_length = struct.unpack('>B', stream.read(1))[0]

        # Get the payload length
        if sr:
            payload_length = struct.unpack('>B', stream.read(1))[0]
        else:
            payload_length = struct.unpack('>I', stream.read(4))[0]

        # Get the ID length if the IL flag is set
        id_length = 0
        if il:
            id_length = struct.unpack('>B', stream.read(1))[0]

        # Read the record type and ID as raw bytes
        record_type = stream.read(type_length)
        record_id = stream.read(id_length)
        
        # Read the entire payload
        payload_data = stream.read(payload_length)

        # Try to decode the payload based on the record type
        if record_type == b'T':
            # NDEF Text Record format:
            # [status byte] [language code] [text payload]
            status_byte = payload_data[0]
            language_code_length = status_byte & 0x3F
            is_utf16 = (status_byte >> 7) & 1
            
            text_bytes = payload_data[1 + language_code_length:]
            
            encoding = 'utf-16be' if is_utf16 else 'utf-8'
            return text_bytes.decode(encoding)

    except (struct.error, IndexError, UnicodeDecodeError):
        return None
        
    return None

class AccessControlApp(tk.Tk):
    def __init__(self, ingress_file, student_data_file):
        super().__init__()
        self.title("Access Control System")
        self.ingress_file = ingress_file
        self.student_data_file = student_data_file
        self.df_ingress = self.load_data(self.ingress_file)
        self.df_student_data = self.load_data(self.student_data_file)
        
        # State variables
        self.mode = tk.StringVar(value='entry')
        
        # GUI elements
        self.create_widgets()
        
        # Start NFC monitoring
        self.cardmonitor = CardMonitor()
        self.cardobserver = NTAG215Observer(self)
        self.cardmonitor.addObserver(self.cardobserver)
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_data(self, file_path):
        """
        Loads data from an Excel file.
        """
        try:
            df = pd.read_excel(file_path)
            # Ensure required columns for INGRESS.xlsx exist
            if 'INGRESS' in file_path and ('uuid' not in df.columns or 'status' not in df.columns or 'last_change' not in df.columns):
                 raise ValueError("Required columns 'uuid', 'status', 'last_change' not found in INGRESS.xlsx.")
            # Ensure last_change column is a datetime object
            if 'last_change' in df.columns:
                 df['last_change'] = pd.to_datetime(df['last_change'])
            return df
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found. Please create it.")
            # Create a dummy file if it doesn't exist to prevent errors
            if 'INGRESS' in file_path:
                dummy_df = pd.DataFrame({'uuid': [], 'status': [], 'last_change': []})
            else:
                dummy_df = pd.DataFrame({'NIP Unizar': [], 'uuid': [], 'Nombre': [], 'Apellidos': [], 'Estudios Matriculados': [], 'Fotografia': []})
            dummy_df.to_excel(file_path, index=False)
            return dummy_df
            
    def create_widgets(self):
        # Mode selection
        mode_frame = ttk.LabelFrame(self, text="Mode")
        mode_frame.pack(pady=10, padx=10, fill='x')
        ttk.Radiobutton(mode_frame, text="Entry", variable=self.mode, value="entry").pack(side='left', padx=10)
        ttk.Radiobutton(mode_frame, text="Exit", variable=self.mode, value="exit").pack(side='left', padx=10)

        # Card and status display
        display_frame = tk.Frame(self)
        display_frame.pack(pady=10)

        self.pdf_label = tk.Label(display_frame)
        self.pdf_label.pack(side='left', padx=10)

        self.qr_label = tk.Label(display_frame)
        self.qr_label.pack(side='left', padx=10)

        # Status text
        self.status_label = ttk.Label(self, text="Waiting for card...", font=("Arial", 24))
        self.status_label.pack(pady=20)
        
        # Student info text
        self.info_text = tk.Text(self, height=15, width=40, state="disabled")
        self.info_text.pack(padx=5, pady=5)

    def on_card_read(self, uuid: str):
        """Callback to handle a successful card read."""
        action = 1 if self.mode.get() == 'entry' else 0
        response = ingress_logic(uuid, action, self.df_ingress, self.df_student_data)
        
        result = response['result']
        message = response['message']
        student_data = response['student_data']
        
        self.update_ui(result, message, student_data, uuid)

    def update_ui(self, result, message, student_data, uuid):
        # Update status label
        self.status_label.config(text=message)
        if result == 'OK':
            self.status_label.config(foreground="green")
        else:
            self.status_label.config(foreground="red")
        
        # Clear previous info
        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        self.pdf_label.configure(image='')
        self.pdf_label.image = None
        self.qr_label.configure(image='')
        self.qr_label.image = None
        
        if student_data:
            # Update Info Textbox
            for key, value in student_data.items():
                self.info_text.insert(tk.END, f"{key}: {value}\n")
            
            # Update QR Code
            qr_image = show_qr(uuid)
            qr_photo = ImageTk.PhotoImage(qr_image)
            self.qr_label.configure(image=qr_photo)
            self.qr_label.image = qr_photo  # Keep a reference
            
            # Update PDF preview
            nip = student_data.get('NIP Unizar')
            if nip:
                pdf_path = Path("output_cards") / f"{nip}.pdf"
                if pdf_path.exists():
                    pdf_image = show_pdf_preview(str(pdf_path))
                    if pdf_image:
                        pdf_photo = ImageTk.PhotoImage(pdf_image)
                        self.pdf_label.configure(image=pdf_photo)
                        self.pdf_label.image = pdf_photo
                    else:
                        self.pdf_label.configure(text="Could not load PDF")
                else:
                    self.pdf_label.configure(text=f"Card for NIP {nip} not found")
            else:
                self.pdf_label.configure(text="NIP not available")
        else:
            self.info_text.insert(tk.END, "Student data not found.")

        self.info_text.config(state="disabled")
        
    def on_closing(self):
        """Clean up and stop card monitoring on application exit."""
        self.cardmonitor.deleteObserver(self.cardobserver)
        self.destroy()

class NTAG215Observer(CardObserver):
    """Observer class for NFC card detection and processing."""
    def __init__(self, app):
        self.app = app
        
    def update(self, observable, actions):
        (addedcards, _) = actions
        for card in addedcards:
            print(f"Card detected, ATR: {toHexString(card.atr)}")
            try:
                connection = card.createConnection()
                connection.connect()
                print("Connected to card")
                
                # --- Read NDEF Message and get UUID ---
                # Start reading from the expected starting page of NDEF message
                read_command = [0xFF, 0xB0, 0x00, 4, 0x04]
                message = b''
                while True:
                    response, sw1, sw2 = connection.transmit(read_command)
                    if sw1 == 0x90 and sw2 == 0x00:
                        message += bytes(response[:4])
                        if 0xFE in response:
                            break
                        read_command[3] += 1
                    else:
                        print(f"Failed to read: SW1={sw1:02X}, SW2={sw2:02X}")
                        return

                print(f"Read NDEF message: {message.hex()}")
                uuid_from_tag = ndef_decode(message)

                if uuid_from_tag:
                    self.app.on_card_read(uuid_from_tag)
                else:
                    self.app.status_label.config(text="ERROR: Could not decode tag.")
                    self.app.status_label.config(foreground="red")
                    print("ERROR: Could not decode NDEF message.")

            except Exception as e:
                print(f"An error occurred: {e}")
                self.app.status_label.config(text="ERROR: Could not read tag.")
                self.app.status_label.config(foreground="red")

if __name__ == "__main__":
    # Create mock data files for testing if they don't exist
    if not os.path.exists('INGRESS.xlsx'):
        print("Creating mock INGRESS.xlsx for demonstration...")
        mock_data_ingress = {
            'uuid': ['76d452ab-89ca-4d0a-a2d1-2ffa9ab61117', 'another-uuid-for-testing'],
            'status': [0, 1], # 0 for outside, 1 for inside
            'last_change': [datetime.datetime.now() - datetime.timedelta(minutes=2), datetime.datetime.now() - datetime.timedelta(minutes=2)]
        }
        df_ingress = pd.DataFrame(mock_data_ingress)
        df_ingress.to_excel('INGRESS.xlsx', index=False)
    
    if not os.path.exists('database.xlsx'):
        print("Creating mock database.xlsx for demonstration...")
        mock_data_students = {
            'NIP Unizar': [123456, 789012],
            'uuid': ['76d452ab-89ca-4d0a-a2d1-2ffa9ab61117', 'another-uuid-for-testing'],
            'Nombre': ['John', 'Jane'],
            'Apellidos': ['Doe', 'Smith'],
            'Estudios Matriculados': ['Computer Science', 'Physics'],
            'Fotografia': ['path/to/photo1.jpg', 'path/to/photo2.jpg']
        }
        df_students = pd.DataFrame(mock_data_students)
        df_students.to_excel('database.xlsx', index=False)

    app = AccessControlApp('INGRESS.xlsx', 'database.xlsx')
    app.mainloop()

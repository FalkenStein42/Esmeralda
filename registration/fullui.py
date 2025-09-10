import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import fitz
import qrcode
from pathlib import Path
import os
import subprocess
from typing import get_type_hints, get_args
from dataclasses import fields
import pandas as pd
from typing import Dict, Any, List, Literal
from registration.cardgenerator.cardgenerator import generate_card, CardOptions

# Import the AccessControlWidget and related functions
from registration.access_control_widget import AccessControlWidget, ingress_logic, ndef_decode, NTAG215Observer, toHexString

# --- Functions from ui.py ---
def load_data(file_path: str) -> (Dict[Any, Dict[str, Any]], List[Any]):
    """
    Loads data from an Excel file and returns a dictionary mapping NIPs to data
    and a sorted list of NIPs.
    """
    try:
        df = pd.read_excel(file_path)
        nip_to_data = {row['NIP Unizar']: row for index, row in df.iterrows()}
        return nip_to_data, sorted(list(nip_to_data.keys()))
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return {}, []

def show_qr(uuid_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uuid_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def show_pdf_preview(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    except Exception as e:
        print(f"Error loading PDF preview: {e}")
        return None

# --- Main application class ---
class IDCardViewerApp:
    def __init__(self, master, data, nips, excel_file):
        self.master = master
        self.master.title("ID Card Viewer & Access Control")
        self.data = data
        self.nips = nips
        self.excel_file = excel_file
        self.current_nip_index = 0
        self.card_options = CardOptions()
        self.option_vars = {}

        self.create_widgets()
        
        # Initialize the AccessControlWidget and pass 'self' to it
        self.access_control_widget = ModifiedAccessControlWidget(self.main_frame, self, 'INGRESS.xlsx', 'database.xlsx')
        self.access_control_widget.pack(side=tk.BOTTOM, fill='x', padx=10, pady=10)

        # Bindings for navigation
        self.master.bind('<Left>', self.prev_nip)
        self.master.bind('<Right>', self.next_nip)
        
        # The app instance is already linked via the constructor, so we don't need this line anymore.
        # self.access_control_widget.app_instance = self
        
        self.update_combobox_and_display()

    def create_widgets(self):
        # Create a main frame to hold everything
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Dropdown for NIPs
        self.nip_selector = ttk.Combobox(self.main_frame, values=self.nips, state="normal")
        self.nip_selector.pack(pady=10)
        
        # Main content frame for QR, PDF, and the menu
        content_frame = tk.Frame(self.main_frame)
        content_frame.pack(fill='both', expand=True)

        # Frame for QR and PDF display
        display_frame = tk.Frame(content_frame)
        display_frame.pack(side=tk.LEFT, padx=10)

        self.qr_label = tk.Label(display_frame)
        self.qr_label.pack(side=tk.LEFT, padx=10)

        self.pdf_label = tk.Label(display_frame)
        self.pdf_label.pack(side=tk.LEFT, padx=10)

        # New frame for the right-side menu
        right_menu_frame = tk.Frame(content_frame)
        right_menu_frame.pack(side=tk.RIGHT, padx=10, fill=tk.Y)
        
        # Section 1: Locked Text Boxes for Student Info
        info_frame = ttk.LabelFrame(right_menu_frame, text="Student Info")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.info_text = tk.Text(info_frame, height=15, width=40, state="disabled")
        self.info_text.pack(padx=5, pady=5)

        ttk.Separator(right_menu_frame, orient='horizontal').pack(fill='x', pady=5)

        # Section 2: Dynamic Card Options
        options_frame = ttk.LabelFrame(right_menu_frame, text="Card Options")
        options_frame.pack(fill=tk.BOTH, pady=5)
        
        type_hints = get_type_hints(CardOptions)
        for field in fields(CardOptions):
            field_name = field.name
            field_type_hints = type_hints.get(field_name)
            
            if hasattr(field_type_hints, '__origin__') and field_type_hints.__origin__ is Literal:
                options = get_args(field_type_hints)
                option_var = tk.StringVar(value=getattr(self.card_options, field_name))
                self.option_vars[field_name] = option_var
                
                ttk.Label(options_frame, text=f"{field_name.capitalize()}:").pack(padx=5, pady=2, anchor='w')
                
                radio_button_frame = tk.Frame(options_frame)
                radio_button_frame.pack(pady=2)

                for option in options:
                    radio_button = ttk.Radiobutton(
                        radio_button_frame, 
                        text=option, 
                        variable=option_var, 
                        value=option,
                        command=lambda name=field_name, value=option: self.update_card_options(name, value)
                    )
                    radio_button.pack(side='left', padx=2)

        ttk.Separator(right_menu_frame, orient='horizontal').pack(fill='x', pady=5)

        # Section 3: Buttons
        button_frame = ttk.LabelFrame(right_menu_frame, text="Actions")
        button_frame.pack(fill=tk.BOTH, pady=5)

        ttk.Button(button_frame, text="Generate", command=self.generate_card_and_display).pack(fill='x', pady=2)
        ttk.Button(button_frame, text="Reload Card", command=self.reload_card).pack(fill='x', pady=2)
        ttk.Button(button_frame, text="Reload Database", command=self.reload_database).pack(fill='x', pady=2)
        ttk.Button(button_frame, text="Open Card", command=self.open_card).pack(fill='x', pady=2)
        
        # New "Virtual Swipe" button
        ttk.Button(button_frame, text="Virtual Swipe", command=self.virtual_swipe).pack(fill='x', pady=2)

        # Bind events
        self.nip_selector.bind("<<ComboboxSelected>>", self.on_nip_select)
        self.nip_selector.bind("<Return>", self.on_nip_select)

    def update_card_options(self, name, value):
        setattr(self.card_options, name, value)
        print(f"Updated card option '{name}' to '{value}'")

    def on_nip_select(self, event=None):
        selected_nip = self.nip_selector.get()
        if selected_nip:
            try:
                nip_int = int(selected_nip)
                self.current_nip_index = self.nips.index(nip_int)
                self.update_display(nip_int)
                
                # Update the access control widget's state for the selected student
                uuid_to_check = str(self.data[nip_int]['uuid'])
                self.update_access_control_status_from_uuid(uuid_to_check)
            except (ValueError, KeyError) as e:
                print(f"Error: Could not find data for NIP '{selected_nip}'. Details: {e}")

    def update_access_control_status_from_uuid(self, uuid: str):
        """
        Updates the access control widget's UI based on a given UUID.
        """
        ingress_df = self.access_control_widget.df_ingress
        ingress_data_for_student = ingress_df[ingress_df['uuid'] == uuid]
        
        if not ingress_data_for_student.empty:
            current_status = ingress_data_for_student.iloc[0]['status']
            if current_status == 1:
                state_text = "CURRENTLY INSIDE"
                color = "green"
            else:
                state_text = "CURRENTLY OUTSIDE"
                color = "red"
            self.access_control_widget.current_state_label.config(text=state_text, foreground=color)
        else:
            self.access_control_widget.current_state_label.config(text="Status Unknown", foreground="gray")

    def update_display(self, nip):
        student_data = self.data[nip]
        uuid = str(student_data['uuid'])
        pdf_path = Path("output_cards") / f"{nip}.pdf"

        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        for key, value in student_data.items():
            self.info_text.insert(tk.END, f"{key}: {value}\n")
        self.info_text.config(state="disabled")
        
        qr_image = show_qr(uuid)
        qr_photo = ImageTk.PhotoImage(qr_image)
        self.qr_label.configure(image=qr_photo)
        self.qr_label.image = qr_photo

        if not pdf_path.exists():
            template_path = Path("output_cards") / "template.pdf"
            if template_path.exists():
                pdf_image = show_pdf_preview(str(template_path))
            else:
                pdf_image = None
                print(f"Template file {template_path} not found.")
        else:
            pdf_image = show_pdf_preview(str(pdf_path))
        
        if pdf_image:
            pdf_photo = ImageTk.PhotoImage(pdf_image)
            self.pdf_label.configure(image=pdf_photo)
            self.pdf_label.image = pdf_photo
        else:
            self.pdf_label.configure(image='', text="Could not load PDF preview.")
            
        # Update the access control widget's status for the currently displayed student
        self.update_access_control_status_from_uuid(uuid)

    def generate_card_and_display(self):
        nip = self.nips[self.current_nip_index]
        row = self.data[nip]
        pdf_path = Path("output_cards") / f"{nip}.pdf"

        loading_label = tk.Label(self.main_frame, text="Generating ID card...", font=("Arial", 16))
        loading_label.pack(pady=10)
        self.master.update_idletasks()

        generate_card(
            str(pdf_path),
            row['Fotografia'],
            row['uuid'],
            str(row['Nombre']),
            str(row['Apellidos']),
            str(row['NIP Unizar']),
            str(row['Estudios Matriculados']),
            self.card_options
        )

        loading_label.pack_forget()
        self.update_display(nip)

    def reload_card(self):
        nip = self.nips[self.current_nip_index]
        self.update_display(nip)

    def reload_database(self):
        current_nip = self.nip_selector.get()
        
        self.data, self.nips = load_data(self.excel_file)
        
        self.nip_selector['values'] = self.nips
        
        try:
            current_nip_int = int(current_nip)
            self.current_nip_index = self.nips.index(current_nip_int)
        except (ValueError, KeyError):
            self.current_nip_index = 0
            
        self.update_combobox_and_display()
        
    def open_card(self):
        nip = self.nips[self.current_nip_index]
        pdf_path = Path("output_cards") / f"{nip}.pdf"
        if pdf_path.exists():
            try:
                if os.name == 'nt':
                    os.startfile(str(pdf_path))
                elif os.name == 'posix':
                    subprocess.run(['xdg-open', str(pdf_path)])
                else:
                    print("Unsupported OS")
            except Exception as e:
                print(f"Error opening file: {e}")
        else:
            print("Card not generated yet.")

    def virtual_swipe(self):
        """Forces a call to the ingress logic function for the current student."""
        current_nip = self.nips[self.current_nip_index]
        student_data = self.data[current_nip]
        uuid = str(student_data['uuid'])
        
        # Get the action from the AccessControlWidget's mode
        action = 1 if self.access_control_widget.mode.get() == 'entry' else 0
        
        # Call the ingress logic function directly
        response = ingress_logic(uuid, action, self.access_control_widget.df_ingress, self.access_control_widget.df_student_data)
        
        # Update the UI of the AccessControlWidget
        self.access_control_widget.update_ui(response['result'], response['message'], response['student_data'], uuid)
        
        # After a virtual swipe, the student's status might have changed, so we update the display
        self.update_access_control_status_from_uuid(uuid)
        
        # Reload the ingress data to make sure it's up-to-date for future operations
        self.access_control_widget.df_ingress = self.access_control_widget.load_data(self.access_control_widget.ingress_file)

    def prev_nip(self, event=None):
        if self.current_nip_index > 0:
            self.current_nip_index -= 1
            self.update_combobox_and_display()

    def next_nip(self, event=None):
        if self.current_nip_index < len(self.nips) - 1:
            self.current_nip_index += 1
            self.update_combobox_and_display()

    def update_combobox_and_display(self):
        if self.nips:
            new_nip = self.nips[self.current_nip_index]
            self.nip_selector.set(new_nip)
            self.update_display(new_nip)

# --- NTAG215Observer Modification ---
# We need to modify the observer to reference the main app for updating the combobox
# and other display elements.
class IDCardViewerNTAG215Observer(NTAG215Observer):
    def __init__(self, app_instance):
        # We need to pass the app_instance to the superclass constructor
        super().__init__(app_instance)

    def update(self, observable, actions):
        (addedcards, _) = actions
        for card in addedcards:
            print(f"Card detected, ATR: {toHexString(card.atr)}")
            try:
                connection = card.createConnection()
                connection.connect()
                print("Connected to card")
                
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
                    # Update the main app's selected student based on the UUID
                    self.app.on_card_read_and_select(uuid_from_tag)
                else:
                    self.app.access_control_widget.status_label.config(text="ERROR: Could not decode tag.")
                    self.app.access_control_widget.status_label.config(foreground="red")
                    print("ERROR: Could not decode NDEF message.")

            except Exception as e:
                print(f"An error occurred: {e}")
                self.app.access_control_widget.status_label.config(text="ERROR: Could not read tag.")
                self.app.access_control_widget.status_label.config(foreground="red")

def on_card_read_and_select(self, uuid: str):
    """Callback to handle a successful card read and select the student."""
    # First, handle the access control logic
    action = 1 if self.access_control_widget.mode.get() == 'entry' else 0
    response = ingress_logic(uuid, action, self.access_control_widget.df_ingress, self.access_control_widget.df_student_data)
    
    # Update the access control widget's UI
    self.access_control_widget.update_ui(response['result'], response['message'], response['student_data'], uuid)
    
    # Reload the ingress data to make sure it's up-to-date
    self.access_control_widget.df_ingress = self.access_control_widget.load_data(self.access_control_widget.ingress_file)

    # Now, find the NIP for the given UUID and update the UI
    student_data_df = self.access_control_widget.df_student_data
    matched_student = student_data_df[student_data_df['uuid'] == uuid]
    if not matched_student.empty:
        nip_from_uuid = matched_student.iloc[0]['NIP Unizar']
        if nip_from_uuid in self.nips:
            # Update the combobox and display
            self.current_nip_index = self.nips.index(nip_from_uuid)
            self.update_combobox_and_display()
        else:
            print(f"Warning: NIP {nip_from_uuid} found but not in loaded data.")

# We need a new class that inherits from AccessControlWidget to override the __init__
class ModifiedAccessControlWidget(AccessControlWidget):
    # Add a new parameter for the app_instance
    def __init__(self, parent, app_instance, ingress_file, student_data_file):
        # Call the parent's constructor first, which will create the original observer
        super().__init__(parent, ingress_file, student_data_file)
        
        # Now, set the app_instance attribute on this widget instance
        self.app_instance = app_instance
        
        # Stop the original monitor and replace the observer
        self.cardmonitor.deleteObserver(self.cardobserver)
        
        # Now create the new observer linked to the main app
        self.cardobserver = IDCardViewerNTAG215Observer(self.app_instance)
        self.cardmonitor.addObserver(self.cardobserver)

# Add the new method to the main app class
IDCardViewerApp.on_card_read_and_select = on_card_read_and_select

if __name__ == "__main__":
    if not os.path.exists('database.xlsx'):
        print("Creating mock database.xlsx for demonstration...")
        mock_data_students = {
            'NIP Unizar': [123456, 789012, 112233],
            'uuid': ['76d452ab-89ca-4d0a-a2d1-2ffa9ab61117', 'another-uuid-for-testing', 'some-other-uuid'],
            'Nombre': ['John', 'Jane', 'Michael'],
            'Apellidos': ['Doe', 'Smith', 'Jordan'],
            'Estudios Matriculados': ['Computer Science', 'Physics', 'Chemistry'],
            'Fotografia': ['path/to/photo1.jpg', 'path/to/photo2.jpg', 'path/to/photo3.jpg']
        }
        df_students = pd.DataFrame(mock_data_students)
        df_students.to_excel('database.xlsx', index=False)

    excel_file = 'database.xlsx'
    nip_data, nips = load_data(excel_file)
    
    root = tk.Tk()
    app = IDCardViewerApp(root, nip_data, nips, excel_file)
    
    def on_closing():
        app.access_control_widget.destroy_monitor()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.mainloop()
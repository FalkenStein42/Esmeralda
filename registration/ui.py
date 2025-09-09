import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import qrcode
from pathlib import Path
import os
import subprocess
from typing import get_type_hints, get_args
from dataclasses import fields
import inspect # Re-adding inspect as it can still be useful for other introspection tasks
import pandas as pd
from typing import Dict, Any, List, Literal
from registration.cardgenerator.cardgenerator import generate_card, CardOptions

def load_data(file_path: str) -> (Dict[Any, Dict[str, Any]], List[Any]):
    """
    Loads data from an Excel file and returns a dictionary mapping NIPs to data
    and a sorted list of NIPs.
    """
    df = pd.read_excel(file_path)
    # Create a mapping for easy lookup
    nip_to_data = {row['NIP Unizar']: row for index, row in df.iterrows()}
    return nip_to_data, sorted(list(nip_to_data.keys()))
# Import all necessary components from your project's modules

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

# Main application class
class IDCardViewerApp:
    def __init__(self, master, data, nips, excel_file):
        self.master = master
        self.master.title("ID Card Viewer")
        self.data = data
        self.nips = nips
        self.excel_file = excel_file
        self.current_nip_index = 0
        
        # Initialize an instance of CardOptions
        self.card_options = CardOptions()
        
        # Create a dictionary to hold Tkinter variables for dynamic options
        self.option_vars = {}

        # Create GUI elements
        self.create_widgets()

        # Bind arrow keys for navigation
        self.master.bind('<Left>', self.prev_nip)
        self.master.bind('<Right>', self.next_nip)

        # Initially display the first student
        self.update_combobox_and_display()

    def create_widgets(self):
        # Dropdown for NIPs
        self.nip_selector = ttk.Combobox(self.master, values=self.nips, state="normal")
        self.nip_selector.pack(pady=10)
        
        # Main content frame for QR, PDF, and the new menu
        main_content_frame = tk.Frame(self.master)
        main_content_frame.pack()

        # Frame for QR and PDF display
        display_frame = tk.Frame(main_content_frame)
        display_frame.pack(side=tk.LEFT, padx=10)

        self.qr_label = tk.Label(display_frame)
        self.qr_label.pack(side=tk.LEFT, padx=10)

        self.pdf_label = tk.Label(display_frame)
        self.pdf_label.pack(side=tk.LEFT, padx=10)

        # New frame for the right-side menu
        right_menu_frame = tk.Frame(main_content_frame)
        right_menu_frame.pack(side=tk.RIGHT, padx=10, fill=tk.Y)
        
        # Section 1: Locked Text Boxes for Student Info
        info_frame = ttk.LabelFrame(right_menu_frame, text="Student Info")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.info_text = tk.Text(info_frame, height=15, width=40, state="disabled")
        self.info_text.pack(padx=5, pady=5)

        # Separator
        ttk.Separator(right_menu_frame, orient='horizontal').pack(fill='x', pady=5)

        # Section 2: Dynamic Card Options
        options_frame = ttk.LabelFrame(right_menu_frame, text="Card Options")
        options_frame.pack(fill=tk.BOTH, pady=5)
        
        # Dynamically create radio buttons based on CardOptions dataclass
        type_hints = get_type_hints(CardOptions)
        for field in fields(CardOptions):
            field_name = field.name
            field_type_hints = type_hints.get(field_name)
            
            # Check if the field is a Literal type
            if hasattr(field_type_hints, '__origin__') and field_type_hints.__origin__ is Literal:
                # Get the literal values
                options = get_args(field_type_hints)
                
                # Create a Tkinter StringVar to hold the selected value
                option_var = tk.StringVar(value=getattr(self.card_options, field_name))
                self.option_vars[field_name] = option_var
                
                # Create a label for the option
                ttk.Label(options_frame, text=f"{field_name.capitalize()}:").pack(padx=5, pady=2, anchor='w')
                
                # Create a frame for the radio buttons to organize them
                radio_button_frame = tk.Frame(options_frame)
                radio_button_frame.pack(pady=2)

                # Create a radio button for each option
                for option in options:
                    radio_button = ttk.Radiobutton(
                        radio_button_frame, 
                        text=option, 
                        variable=option_var, 
                        value=option,
                        command=lambda name=field_name, value=option: self.update_card_options(name, value)
                    )
                    radio_button.pack(side='left', padx=2)

        # Separator
        ttk.Separator(right_menu_frame, orient='horizontal').pack(fill='x', pady=5)

        # Section 3: Buttons
        button_frame = ttk.LabelFrame(right_menu_frame, text="Actions")
        button_frame.pack(fill=tk.BOTH, pady=5)

        ttk.Button(button_frame, text="Generate", command=self.generate_card_and_display).pack(fill='x', pady=2)
        ttk.Button(button_frame, text="Reload Card", command=self.reload_card).pack(fill='x', pady=2)
        ttk.Button(button_frame, text="Reload Database", command=self.reload_database).pack(fill='x', pady=2)
        ttk.Button(button_frame, text="Open Card", command=self.open_card).pack(fill='x', pady=2)
        ttk.Button(button_frame, text="Print Card", command=self.print_card).pack(fill='x', pady=2)

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
            except (ValueError, KeyError) as e:
                print(f"Error: Could not find data for NIP '{selected_nip}'. Details: {e}")

    def update_display(self, nip):
        student_data = self.data[nip]
        uuid = str(student_data['uuid'])
        pdf_path = Path("output_cards") / f"{nip}.pdf"

        # Update Info Textbox
        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        for key, value in student_data.items():
            self.info_text.insert(tk.END, f"{key}: {value}\n")
        self.info_text.config(state="disabled")
        
        # Update QR Code
        qr_image = show_qr(uuid)
        qr_photo = ImageTk.PhotoImage(qr_image)
        self.qr_label.configure(image=qr_photo)
        self.qr_label.image = qr_photo  # Keep a reference

        # Check if PDF exists
        if not pdf_path.exists():
            # Show the default template if the card doesn't exist
            template_path = Path("output_cards") / "template.pdf"
            if template_path.exists():
                pdf_image = show_pdf_preview(str(template_path))
            else:
                # Handle case where template also doesn't exist
                pdf_image = None
                print(f"Template file {template_path} not found.")
        else:
            # Show the generated card if it exists
            pdf_image = show_pdf_preview(str(pdf_path))
        
        # Update PDF label if an image was loaded
        if pdf_image:
            pdf_photo = ImageTk.PhotoImage(pdf_image)
            self.pdf_label.configure(image=pdf_photo)
            self.pdf_label.image = pdf_photo
        else:
            # Clear the display and show a message if image loading failed
            self.pdf_label.configure(image='', text="Could not load PDF preview.")

    def generate_card_and_display(self):
        nip = self.nips[self.current_nip_index]
        row = self.data[nip]
        pdf_path = Path("output_cards") / f"{nip}.pdf"

        # Show a loading screen
        loading_label = tk.Label(self.master, text="Generating ID card...", font=("Arial", 16))
        loading_label.pack(pady=10)
        self.master.update_idletasks()

        # Generate the card, passing the card_options dataclass
        generate_card(
            str(pdf_path),
            row['Fotografia'],
            row['uuid'],
            str(row['Nombre']),
            str(row['Apellidos']),
            str(row['NIP Unizar']),
            str(row['Estudios Matriculados']),
            self.card_options # Pass the CardOptions instance
        )

        # Remove loading message and update display with the new card
        loading_label.pack_forget()
        self.update_display(nip)

    def reload_card(self):
        nip = self.nips[self.current_nip_index]
        self.update_display(nip)

    def reload_database(self):
        # Save the currently selected NIP
        current_nip = self.nip_selector.get()
        
        # Reload data using the instance variable
        self.data, self.nips = load_data(self.excel_file)
        
        # Update the combobox values
        self.nip_selector['values'] = self.nips
        
        # Try to find the index of the old NIP in the new data
        try:
            current_nip_int = int(current_nip)
            self.current_nip_index = self.nips.index(current_nip_int)
        except (ValueError, KeyError):
            # If the old NIP is not found, default to the first one
            self.current_nip_index = 0
            
        self.update_combobox_and_display()

    def open_card(self):
        nip = self.nips[self.current_nip_index]
        pdf_path = Path("output_cards") / f"{nip}.pdf"
        if pdf_path.exists():
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(str(pdf_path))
                elif os.name == 'posix': # Linux
                    subprocess.run(['xdg-open', str(pdf_path)])
                else:
                    print("Unsupported OS")
            except Exception as e:
                print(f"Error opening file: {e}")
        else:
            print("Card not generated yet.")

    def print_card(self):
        nip = self.nips[self.current_nip_index]
        pdf_path = Path("output_cards") / f"{nip}.pdf"
        if pdf_path.exists():
            try:
                if os.name == 'nt':  # Windows
                    subprocess.run(['cmd', '/c', 'start', '/b', 'print', str(pdf_path)], check=True)
                elif os.name == 'posix': # Linux
                    subprocess.run(['lp', str(pdf_path)], check=True)
                else:
                    print("Unsupported OS")
            except Exception as e:
                print(f"Error printing file: {e}")
        else:
            print("Card not generated yet.")

    def prev_nip(self, event=None):
        if self.current_nip_index > 0:
            self.current_nip_index -= 1
            self.update_combobox_and_display()

    def next_nip(self, event=None):
        if self.current_nip_index < len(self.nips) - 1:
            self.current_nip_index += 1
            self.update_combobox_and_display()

    def update_combobox_and_display(self):
        new_nip = self.nips[self.current_nip_index]
        self.nip_selector.set(new_nip)
        self.update_display(new_nip)

# Example usage
if __name__ == "__main__":
    excel_file = 'database.xlsx'
    nip_data, nips = load_data(excel_file)
    
    root = tk.Tk()
    app = IDCardViewerApp(root, nip_data, nips, excel_file)
    root.mainloop()
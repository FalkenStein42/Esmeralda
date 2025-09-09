import cv2
import qrcode
import numpy as np

def show_qr_codes(data_list):
    """
    Generates and displays QR codes for a given list of strings.

    The QR code for each string is displayed in a new window.
    Press 'Enter' to move to the next QR code.
    Press 'q' or 'Escape' to exit at any time.

    Args:
        data_list (list): A list of strings to be converted into QR codes.
    """
    if not data_list:
        print("The input list is empty.")
        return

    print("--- QR Code Viewer ---")
    print("Press 'Enter' to view the next QR code.")
    print("Press 'q' or 'Escape' to quit.")
    print("-" * 25)

    for i, data in enumerate(data_list):
        print(f"Generating QR code for: '{data}'")

        # Create a QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # Add data to the QR code instance
        qr.add_data(data)
        qr.make(fit=True)

        # Create the QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert the Pillow image to a NumPy array for OpenCV
        img_np = np.array(img.convert('RGB'))
        # OpenCV expects BGR color format
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # Create a resizable window
        window_name = f"QR Code {i + 1} of {len(data_list)}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        # Display the image
        cv2.imshow(window_name, img_bgr)

        # Wait for a key press
        key = cv2.waitKey(0)

        # Check for user input to exit the loop
        if key == 27 or key == ord('q'):  # 27 is the ASCII code for Escape
            print("\nExiting viewer.")
            break
        elif key != 13: # 13 is the ASCII code for Enter
            # If any other key is pressed, still proceed to the next QR code
            print("Key pressed was not 'Enter'. Proceeding to next QR code.")
        
        # Close the current window before the next iteration
        cv2.destroyAllWindows()

    # Final cleanup
    cv2.destroyAllWindows()
    print("\nAll QR codes have been shown.")

if __name__ == "__main__":
    # Example usage with a list of strings
    from uuid import uuid4
    my_data = [
        uuid4()
        for i in range(0,4)
    ]
    show_qr_codes(my_data)

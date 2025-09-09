from pickletools import bytes8
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toHexString
from smartcard.CardConnection import CardConnection
import ndef
import struct
import io

def ndef_decode(hex_string):
    """
    Decodes an NDEF message from a hexadecimal string and returns a human-readable
    string representation of the records.

    This function first converts the hexadecimal string into a byte stream and then
    iterates through the NDEF records. It is designed to handle very large payloads
    by processing them in chunks, preventing memory issues.

    Args:
        hex_string (str): A string containing the hexadecimal representation of the
                          NDEF message bytes.

    Returns:
        str: A multi-line string with details about each decoded NDEF record,
             including its type, ID, and payload size.

    Raises:
        ndef.message.NdefError: If the NDEF message is malformed.
        ValueError: If the input hex string is invalid.
    """
    try:
        # Convert the hex string to a bytes object
        message_bytes = bytes.fromhex(hex_string)
        # Create a stream from the bytes
        stream = io.BytesIO(message_bytes)
    except ValueError as e:
        raise ValueError(f"Invalid hexadecimal string: {e}")

    output = []

    try:
        # Check for NFC Forum Tag TLV structure (Type 0x03 = NDEF message)
        tag_tlv_type = stream.read(1)
        if tag_tlv_type != b'\x03':
            raise ndef.message.NdefError("NDEF message does not start with a valid TLV type (0x03)")
        
        # Read the NDEF message length from the TLV
        ndef_message_length_byte = stream.read(1)
        if not ndef_message_length_byte:
            raise ndef.message.NdefError("Could not read NDEF message length")
        
        ndef_message_length = struct.unpack('>B', ndef_message_length_byte)[0]
        # We can use this length to verify we've read the full message, but
        # the internal NDEF record structure will guide us.

        # We process the stream until the end marker is found.
        while True:
            # Read the first byte which contains the flags
            header = stream.read(1)
            if not header:
                break
            
            flags = struct.unpack('>B', header)[0]
            
            # Extract flags
            mb = (flags >> 7) & 1  # Message Begin
            me = (flags >> 6) & 1  # Message End
            cf = (flags >> 5) & 1  # Chunk Flag
            sr = (flags >> 4) & 1  # Short Record
            il = (flags >> 3) & 1  # ID Length

            # Get the type length (1 byte)
            type_length = struct.unpack('>B', stream.read(1))[0]

            # Get the payload length
            if sr:
                # Short record, payload length is 1 byte
                payload_length = struct.unpack('>B', stream.read(1))[0]
            else:
                # Full record, payload length is 4 bytes
                payload_length = struct.unpack('>I', stream.read(4))[0]

            # Get the ID length if the IL flag is set
            id_length = 0
            if il:
                id_length = struct.unpack('>B', stream.read(1))[0]

            # Read the record type and ID as raw bytes
            record_type = stream.read(type_length)
            record_id = stream.read(id_length)
            
            # Read the entire payload into a variable. For very large payloads,
            # this part might still be memory intensive, but the alternative is to
            # process the payload without keeping it. For this return type,
            # we must process it all.
            payload_data = stream.read(payload_length)
            
            # Check for the NDEF message terminator byte
            terminator = stream.read(1)
            if terminator != b'\xfe':
                raise ndef.message.NdefError("Malformed NDEF message: missing terminator byte (0xFE)")
            
            # Now, try to decode the payload based on the record type
            decoded_payload_text = ""
            if record_type == b'T':
                # NDEF Text Record format:
                # [status byte] [language code] [text payload]
                status_byte = payload_data[0]
                language_code_length = status_byte & 0x3F  # Lower 6 bits for lang code length
                
                # Check for UTF-8 or UTF-16 encoding
                is_utf16 = (status_byte >> 7) & 1
                
                # Extract language code and text
                language_code = payload_data[1:1 + language_code_length].decode('ascii')
                text_bytes = payload_data[1 + language_code_length:]
                
                # Decode the text
                encoding = 'utf-16be' if is_utf16 else 'utf-8'
                decoded_payload_text = text_bytes.decode(encoding)

            output.append(f"Record Found:")
            output.append(f"  Type: {record_type.decode('ascii')}")
            output.append(f"  ID: {record_id.hex()}")
            output.append(f"  Payload Size: {len(payload_data)} bytes")
            if decoded_payload_text:
                output.append(f"  Decoded Text: {decoded_payload_text}")

            # If the Message End flag is set, this is the last record in the message
            if me:
                break
            
    except struct.error as e:
        raise ndef.message.NdefError(f"Malformed NDEF message: {e}")
        
    return "\n".join(output)

def read_ndef_message(connection: CardConnection) -> bool:
    """Reads the NDEF message from the NFC tag and compares it to the expected message."""
    # Start reading from the expected starting page of NDEF message
    read_command = [0xFF, 0xB0, 0x00, 4, 0x04]
    message = b''
    try:
        while True:  # Loop to read all parts of the NDEF message
            response, sw1, sw2 = connection.transmit(read_command)
            if sw1 == 0x90 and sw2 == 0x00:
                message += bytes(response[:4])  # Append only the NDEF data
                # print(f"Read data from page {read_command[3]}: {bytes(response[:4]).hex()}")
                if 0xFE in response:  # Look for end byte of NDEF message within the response
                    break
                read_command[3] += 1  # Move to the next page
            else:
                print(f"Failed to read at page {
                      read_command[3]}: SW1={sw1:02X}, SW2={sw2:02X}")
                return False

        print("Read NDEF message:", message.hex())
        print("Decoded NDEF message:", ndef_decode(message.hex()))
    except Exception as e:
        print(f"Error during reading: {e}")
        return False



def create_ndef_record(url: str) -> bytes:
    """Encodes a given URI into a complete NDEF message using ndeflib.

    Args:
        url (str): The URI to be encoded into an NDEF message.

    Returns:
        bytes: The complete NDEF message as bytes, ready to be written to an NFC tag.
    """

    uri_record = ndef.UriRecord(url)

    # Encode the NDEF message
    encoded_message = b''.join(ndef.message_encoder([uri_record]))

    # Calculate total length of the NDEF message (excluding start byte and terminator)
    message_length = len(encoded_message)

    # Create the initial part of the message with start byte, length, encoded message, and terminator
    initial_message = b'\x03' + \
        message_length.to_bytes(1, 'big') + encoded_message + b'\xFE'

    # Calculate padding to align to the nearest block size (assuming 4 bytes per block)
    padding_length = -len(initial_message) % 4
    complete_message = initial_message + (b'\x00' * padding_length)
    return complete_message


class NTAG215Observer(CardObserver):
    """Observer class for NFC card detection and processing."""

    def update(self, observable, actions):
        global cards_processed
        (addedcards, _) = actions
        for card in addedcards:
            print(f"Card detected, ATR: {toHexString(card.atr)}")
            try:
                connection = card.createConnection()
                connection.connect()
                print("Connected to card")


                if read_ndef_message(connection):
                    print('beep')  # On success
                else:
                    pass  # On failure

                cards_processed += 1
                print(f"Total cards processed: {cards_processed}")

            except Exception as e:
                print(f"An error occurred: {e}")


def main():
    print("Starting NFC card processing...")
    cardmonitor = CardMonitor()
    cardobserver = NTAG215Observer()
    cardmonitor.addObserver(cardobserver)

    try:
        input("Press Enter to stop...\n")
    finally:
        cardmonitor.deleteObserver(cardobserver)
        print("Stopped NFC card processing. Total cards processed:", cards_processed)


if __name__ == "__main__":
    cards_processed = 0
    main()
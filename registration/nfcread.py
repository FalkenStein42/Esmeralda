#!/usr/bin/env python3
"""
NFC Tag Reader Script with UUID reading functionality.

This script extends the provided nfctest.py to include a function that
prompts for an identifier, reads a UUID from a text record on an NFC tag,
and returns a dictionary mapping the identifier to the UUID.

Assumes a tag formatted with a single NDEF Text Record containing a UUID4.
"""

from smartcard.System import readers
from smartcard.util import toHexString, toBytes
import time
import uuid

class NFCTagReader:
    def __init__(self):
        self.readers = readers()
        self.connection = None
        
    def connect_to_tag(self):
        """Wait for and connect to an NFC tag"""
        print("Waiting for NFC tag...")
        
        while True:
            for reader in self.readers:
                try:
                    connection = reader.createConnection()
                    connection.connect()
                    
                    # Check if tag is present
                    atr = connection.getATR()
                    if atr:
                        print(f"Connected to tag via: {reader}")
                        print(f"ATR: {toHexString(atr)}")
                        self.connection = connection
                        return True
                        
                except Exception as e:
                    continue
                    
            time.sleep(1)
            
        return False
    
    def disconnect_from_tag(self):
        """Disconnect from the NFC tag."""
        if self.connection:
            try:
                self.connection.disconnect()
                print("\nDisconnected from tag")
            except Exception as e:
                print(f"Error disconnecting: {e}")

    def read_uuid_from_tag(self):
        """
        Reads a UUID4 from an NDEF Text Record on the NFC tag.
        
        This method is a more robust implementation that attempts to
        correctly parse the NDEF (NFC Data Exchange Format) message structure.
        It reads the tag's memory blocks, looks for the NDEF message and
        record headers, and then extracts the text payload.

        Returns:
            str: The UUID string if found and valid, otherwise None.
        """
        try:
            # Common starting block for NDEF data on MIFARE Ultralight tags is block 4
            read_command = [0xFF, 0xB0, 0x00, 0x04, 16] # Read 16 bytes from block 4
            data, sw1, sw2 = self.connection.transmit(read_command)
            
            if sw1 != 0x90 or sw2 != 0x00:
                print(f"Error reading NDEF header: {sw1:02X}{sw2:02X}")
                return None

            # Check for NDEF message header (0x03) and length byte
            if data[0] != 0x03:
                print("No NDEF message header (0x03) found.")
                return None
            
            # The length of the NDEF message is the second byte
            ndef_message_length = data[1]
            if ndef_message_length == 0xFF:
                # 3-byte length not supported by this simple script
                print("Multi-byte NDEF length not supported.")
                return None
            
            print(f"Found NDEF message with length: {ndef_message_length} bytes.")

            # Read the entire NDEF message by looping through blocks
            full_data = data[2:16] # Start with the data from the first read
            
            # Calculate remaining bytes to read
            bytes_to_read = ndef_message_length - len(full_data)
            current_block = 5 # Start reading from the next block
            
            while bytes_to_read > 0:
                # Read 16 bytes at a time
                read_size = 16
                if bytes_to_read < 16:
                    read_size = bytes_to_read

                read_command = [0xFF, 0xB0, 0x00, current_block, read_size]
                block_data, sw1, sw2 = self.connection.transmit(read_command)
                
                if sw1 != 0x90 or sw2 != 0x00:
                    print(f"Error reading block {current_block}: {sw1:02X}{sw2:02X}")
                    return None
                
                full_data.extend(block_data)
                bytes_to_read -= len(block_data)
                current_block += 1
            
            print(f"Length of full_data list: {len(full_data)}")
            print(f"Full NDEF record raw data (hex): {toHexString(full_data)}")

            # --- New Logic: Iterate through multiple records ---
            current_index = 0
            while current_index < len(full_data):
                record_data = full_data[current_index:]
                
                if not record_data:
                    break

                # Parse NDEF Record Header
                flags_byte = record_data[0]
                type_len = record_data[1]
                
                # Check for 4-byte payload length
                if flags_byte & 0x10 == 0: # SR (Short Record) is not set
                    # 4-byte payload length
                    payload_len = (record_data[2] << 24) | (record_data[3] << 16) | (record_data[4] << 8) | record_data[5]
                    header_len = 1 + 1 + 4 + type_len
                else:
                    # 1-byte payload length
                    payload_len = record_data[2]
                    header_len = 1 + 1 + 1 + type_len

                record_type = record_data[header_len - type_len : header_len]
                
                # Check if it's a Text Record (type is 'T' or 0x54)
                if record_type == toBytes('T'):
                    # The text payload starts after the header
                    raw_payload = record_data[header_len : header_len + payload_len]
                    
                    print("\n--- Parsing NDEF Text Record ---")
                    print(f"Raw payload bytes (hex): {toHexString(raw_payload)}")
                    
                    if not raw_payload:
                        print("Payload is empty.")
                        return None
                    
                    # Extract language code and text from the payload
                    status_byte = raw_payload[0]
                    language_code_length = status_byte & 0x3F
                    
                    uuid_bytes = raw_payload[1 + language_code_length:]
                    
                    try:
                        uuid_string = bytes(uuid_bytes).decode('utf-8')
                        print(f"Decoded text payload: '{uuid_string}'")

                        # Validate the UUID
                        try:
                            val = uuid.UUID(uuid_string, version=4)
                            print(f"\nFound valid UUID: {uuid_string}")
                            return uuid_string
                        except ValueError:
                            print(f"Found text, but it's not a valid UUID: '{uuid_string}'")
                            
                    except UnicodeDecodeError:
                        print("Failed to decode text payload.")
                
                # Move to the next record
                current_index += header_len + payload_len

            # If the loop finishes without finding a UUID
            print("No NDEF Text Record with a valid UUID was found.")
            return None

        except Exception as e:
            print(f"Error reading UUID from tag: {str(e)}")
            return None
        
def read_and_match_uuid():
    """
    Main function to read an identifier, connect to an NFC tag, and read a UUID.
    
    Prompts the user for a number, reads the UUID from a tag, and returns a
    dictionary with the identifier as the key and the UUID as the value.
    
    Returns:
        dict: A dictionary with the format {identifier: uuid} or an error message.
    """
    try:
        identifier = input("Please enter an identifier number: ")
        
        reader = NFCTagReader()
        if not reader.connect_to_tag():
            return {"error": "Failed to connect to NFC tag"}
        
        read_uuid = reader.read_uuid_from_tag()
        
        if read_uuid:
            result_dict = {identifier: read_uuid}
            print("\n" + "="*40)
            print("SUCCESS: UUID READ AND MATCHED")
            print("="*40)
            print(f"Identifier: {identifier}")
            print(f"UUID:       {read_uuid}")
            return result_dict
        else:
            print("\nFailed to read a valid UUID from the NFC tag.")
            return {"error": "Failed to read UUID"}
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}
    finally:
        # Ensure the connection is closed even if an error occurs
        if 'reader' in locals():
            reader.disconnect_from_tag()

if __name__ == "__main__":
    result = read_and_match_uuid()
    print("\nFunction return value:")
    print(result)

import imaplib
import email
import os
from email.policy import default
import fitz  # PyMuPDF
from dotenv import load_dotenv
from pymongo import MongoClient
import re


def fetch_emails_from_inventory_folder(email_address, password):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(email_address, password)
    mail.select('"[Gmail]/All Mail"')  # Adjust as needed for your "Inventory" folder

    result, data = mail.search(None, 'UNSEEN')  # Or use 'ALL' for all emails
    emails = []
    if result == 'OK':
        for num in data[0].split():
            result, email_data = mail.fetch(num, '(RFC822)')
            if result == 'OK':
                emails.append(email_data[0][1])

    mail.logout()
    return emails


def extract_pdf_attachments(raw_email):
    email_message = email.message_from_bytes(raw_email, policy=default)
    attachments = []

    for part in email_message.walk():
        if part.get_content_maintype() == 'application' and part.get_content_subtype() == 'pdf':
            filename = part.get_filename()
            if filename:
                content = part.get_payload(decode=True)
                attachments.append((filename, content))

    return attachments


def parse_inventory_pdf(pdf_bytes):
    inventory_data = {'items': []}
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text")

    lines = text.split('\n')
    item_pattern = re.compile(r'^(\d+) - (\w[\w\s.-]+)')
    # Adjusted to consider the next line after item name for "Case" or "Each"
    quantity_pattern = re.compile(r'^\s*(Case|Each)\s+(\d+)')

    current_item = {}
    skip_next_line = False  # Flag to skip processing for quantity lines

    for i, line in enumerate(lines):
        if skip_next_line:
            skip_next_line = False
            continue

        item_match = item_pattern.match(line)
        if item_match:
            # Finalize and save the previous item
            if current_item:
                inventory_data['items'].append(current_item)
                current_item = {}

            # Initialize new item
            current_item = {
                'ItemNumber': int(item_match.group(1)),
                'ItemName': item_match.group(2),
                'Cases': None,
                'Eaches': None
            }

            # Check if next line contains "Case" or "Each" quantity
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                quantity_match = quantity_pattern.match(next_line)
                if quantity_match:
                    quantity_type, quantity = quantity_match.groups()
                    if quantity_type == "Case":
                        current_item['Cases'] = quantity
                    elif quantity_type == "Each":
                        current_item.clear()
                    skip_next_line = True  # Skip the next line as it has been processed

    # Add the last item if it exists
    if current_item.get('ItemNumber'):  # Corrected from 'Item number' to 'ItemNumber'
        inventory_data['items'].append(current_item)

    return inventory_data


# Sample usage with the provided PDF content as bytes
# pdf_bytes = ... # Load your PDF bytes here
# inventory_data = parse_inventory_pdf(pdf_bytes)


def save_inventory_to_mongodb(inventory_data, client):
    db = client['mydatabase']
    collection = db['inventory']

    if inventory_data and inventory_data['items']:  # Ensure there are items to save
        result = collection.insert_one(inventory_data)
        print(f"Inventory data inserted with record id: {result.inserted_id}")
    else:
        print("No inventory items to save.")




def process_inventory_emails(email_address, password, client):
    emails = fetch_emails_from_inventory_folder(email_address, password)

    for raw_email in emails:
        attachments = extract_pdf_attachments(raw_email)
        # Inside process_inventory_emails, when calling parse_inventory_pdf
        for filename, content in attachments:
            inventory_data = parse_inventory_pdf(content)  # content is already in bytes
            if inventory_data:
                save_inventory_to_mongodb(inventory_data, client)


def identify_and_upload_oos_items(client):
    try:
        db = client['mydatabase']

        # Collections
        inventory_collection = db['inventory']
        items_collection = db['items']
        oos_items_collection = db['oos_items']  # Collection for out-of-stock items

        # Fetch the latest inventory
        latest_inventory = inventory_collection.find_one(sort=[("_id", -1)])
        if not latest_inventory:
            print("No inventory found")
            return

        # Extract item numbers from the latest inventory
        inventory_item_numbers = {item['ItemNumber'] for item in latest_inventory['items']}

        # Fetch all items that are considered active or relevant from items collection
        all_items = list(items_collection.find({}, {'ItemNumber': 1, 'ItemDescription': 1, 'Grand Total': 1}))

        # Delete all existing documents in oos_items_collection before uploading new ones
        oos_items_collection.delete_many({})

        # Identify OOS items
        oos_items = []
        for item in all_items:
            if item['ItemNumber'] not in inventory_item_numbers:
                # Adding only relevant fields to OOS items list
                item_number = int(float(item['ItemNumber']))  # Convert to float first, then to int to handle .0
                oos_item = {
                    'ItemNumber': str(item_number),  # Convert integer back to string
                    'ItemDescription': item.get('ItemDescription', ''),
                }
                oos_items.append(oos_item)

        # Upload OOS items to MongoDB, if any
        if oos_items:
            result = oos_items_collection.insert_many(oos_items)
            print(f"Uploaded {len(result.inserted_ids)} OOS items to MongoDB.")
        else:
            print("No OOS items to upload.")

    except Exception as e:
        print(f"An error occurred: {e}")


def generate_and_save_inventory_stats(client):
    try:
        db = client['mydatabase']

        inventory_collection = db['inventory']
        oos_items_collection = db['oos_items']
        inventory_stats_collection = db['inventory_stats']

        # Fetch the latest inventory
        latest_inventory = inventory_collection.find_one(sort=[("_id", -1)])
        if not latest_inventory:
            print("No inventory found")
            return

        # Calculate total inventory (sum of all cases)
        total_inventory = sum(
            int(item.get('Cases', 0)) for item in latest_inventory['items'] if item.get('Cases', 0).isdigit())

        # Calculate the number of out-of-stock items
        num_oos_items = oos_items_collection.count_documents({})

        # Prepare the statistics document
        stats_document = {
            'total_inventory': total_inventory,
            'num_oos_items': num_oos_items,
        }

        # Save the statistics to MongoDB
        result = inventory_stats_collection.insert_one(stats_document)
        print(f"Inventory statistics saved with record id: {result.inserted_id}")

    except Exception as e:
        print(f"An error occurred: {e}")


def inventory_main():
    load_dotenv()  # This method will load variables from a .env file

    email_address = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')
    db_uri = os.getenv('DB_URI')
    client = MongoClient(db_uri)

    process_inventory_emails(email_address, password, client)
    identify_and_upload_oos_items(client)
    generate_and_save_inventory_stats(client)
    client.close()

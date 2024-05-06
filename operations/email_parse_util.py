from dotenv import load_dotenv
from pymongo import MongoClient
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from datetime import datetime
import imaplib
import email
import re
from email.policy import default
import fitz  # PyMuPDF
import os

email_address = os.getenv("email_address")
password = os.getenv("password")
uri = os.getenv("uri")


def is_inventory_email(raw_email):
    """
    Checks if the email is an inventory email based on the attachment filenames.

    Args:
        raw_email (bytes): The raw email content.

    Returns:
        bool: True if the email is an inventory email, False otherwise.
    """
    # Parse the raw email content
    email_message = BytesParser(policy=policy.default).parsebytes(raw_email)

    # Check all parts of the email
    for part in email_message.iter_attachments():
        # Try to get the filename of the attachment
        filename = part.get_filename()
        if filename:
            # Check if the filename matches the inventory email pattern
            if re.match(r"901\.901_InventoryStatus_\d{8}_\d{6}\.pdf", filename):
                return True

    return False


def is_order_email(raw_email):
    """
    Determines if an email subject line indicates an order email.

    Args:
        raw_email (bytes): The raw email content in bytes.

    Returns:
        bool: True if the subject line matches the order email pattern, False otherwise.
    """
    # Parse the raw email content to get the email object
    email_message = BytesParser(policy=policy.default).parsebytes(raw_email)

    # Extract the subject from the email object
    subject_header = email_message['Subject']
    subject = str(email.header.make_header(email.header.decode_header(subject_header)))

    # Define the substring to look for in the subject line for order emails
    order_subject_substring = "concord peet's route replenishment submission"

    # Check if the subject line (in lowercase) contains the specified order subject substring (also in lowercase)
    return order_subject_substring.lower() in subject.lower()



def insert_order_into_mongodb(extracted_data, client, db_name='mydatabase', orders_collection='orders'):
    """
    Inserts the order details into a MongoDB collection.

    :param extracted_data: The data to be inserted, including the order details.
    :param client: MongoDB client instance.
    :param db_name: The name of the database.
    :param orders_collection: The name of the collection for orders.
    """
    # Check if the necessary data is available
    if not extracted_data['items']:
        print("Missing items in order details.")
        return

    # Prepare the document to be inserted
    try:
        pick_up_date = datetime.today()
    except ValueError as e:
        print(f"Error parsing pick_up_date: {e}")
        pick_up_date = None

    order_document = {
        'route_name': extracted_data.get('route_name'),
        'route': extracted_data.get('route'),
        'pick_up_date': pick_up_date,
        'pick_up_time': extracted_data.get('pick_up_time'),
        'total_cases': extracted_data.get('total_cases'),
        'items': extracted_data['items'],  # Assuming items is a list of dictionaries
        'status': "Pending",
    }

    # Select the database and collection
    db = client[db_name]
    orders_col = db[orders_collection]

    # Insert the document into the orders collection
    result = orders_col.insert_one(order_document)
    print(f"Order data inserted with record id: {result.inserted_id}")

    # Generate transfer_ID (e.g., using the last 4 characters of the MongoDB _id)
    transfer_id = str(result.inserted_id)[-4:]

    # Update the document with the transfer_ID
    orders_col.update_one({'_id': result.inserted_id}, {'$set': {'transfer_id': transfer_id}})

    print(f"Order updated with transfer_id: {transfer_id}")


def insert_inventory_to_mongodb(inventory_data):
    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['mydatabase']
    collection = db['inventory']
    isstats = db['inventory_stats']

    # Check if there is inventory data to save
    if inventory_data and 'items' in inventory_data:
        # Insert inventory data
        inventory_result = collection.insert_one(inventory_data)
        print(f"Inventory data inserted with record id: {inventory_result.inserted_id}")

        # Calculate statistics, e.g., total number of items
        total_items = sum(item['quantity'] for item in inventory_data['items'] if 'quantity' in item)

        # Create a stats dictionary
        stats_data = {
            'total_items': total_items,
            'record_date': datetime.now()  # Storing the time when the stats were recorded
        }

        # Insert stats data
        stats_result = isstats.insert_one(stats_data)
        print(f"Inventory stats inserted with record id: {stats_result.inserted_id}")

    else:
        print("No inventory items to save.")

    client.close()


def parse_inventory_pdf(pdf_bytes):
    inventory_data = {'items': []}
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text")
    doc.close()

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


def identify_and_upload_oos_items():
    try:
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        inventory_collection = db['inventory']
        items_collection = db['items']
        oos_items_collection = db['oos_items']

        # Fetch the latest inventory
        latest_inventory = inventory_collection.find_one(sort=[("_id", -1)])
        if not latest_inventory:
            print("No inventory found")
            return

        # Extract item numbers from the latest inventory and convert them to integers if they are strings
        inventory_item_numbers = {int(item['ItemNumber']) for item in latest_inventory['items']}

        # Fetch all items that are considered active or relevant from the items collection
        all_items = list(items_collection.find({}, {'ItemNumber': 1, 'ItemDescription': 1, 'Grand Total': 1}))
        # Delete all existing documents in oos_items_collection before uploading new ones
        oos_items_collection.delete_many({})

        # Identify OOS items
        oos_items = []
        for item in all_items:

            item_number = int(item['ItemNumber'])
            grand_total = item.get('Grand Total', 0)
            if item_number not in inventory_item_numbers:

                oos_item = {
                    'ItemNumber': item_number,
                    'ItemDescription': item.get('ItemDescription', '')
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



def process_inventory_email(raw_email, client):
    attachments = extract_pdf_attachments(raw_email)
    for filename, content in attachments:
        inventory_data = parse_inventory_pdf(content)
        if inventory_data:
            insert_inventory_to_mongodb(inventory_data)
            identify_and_upload_oos_items()


def parse_email_content(email_content):
    # Parse the email content
    msg = BytesParser(policy=policy.default).parsebytes(email_content)

    # Prepare extracted data dictionary
    extracted_data = {
        'route_name': None,
        'route_number': None,
        'pick_up_date': None,
        'total_cases': None,
        'items': []
    }

    reorder_items(extracted_data.items())
    # Function to process each part of the email
    def process_part(part):
        content_type = part.get_content_type()
        charset = part.get_content_charset() or 'utf-8'  # Default to UTF-8 if charset is not specified
        if content_type == "text/plain" or content_type == "text/html":
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(charset)
            except Exception as e:
                print(f"Error decoding payload: {e}")
        return ''

    # Handle multipart messages
    if msg.is_multipart():
        email_str = ''
        for part in msg.walk():
            part_content = process_part(part)
            if part_content:  # Ensure that the part contains text content
                email_str += part_content
    else:
        email_str = process_part(msg)

    # Regular expressions to find route name and number
    route_name_match = re.search(r"Route Name:\s*(.*)", email_str)
    if route_name_match:
        extracted_data['route_name'] = route_name_match.group(1).strip()

    route_number_match = re.search(r"Route Number:\s*(RTC\d+)", email_str)
    if route_number_match:
        extracted_data['route_number'] = route_number_match.group(1).strip()

    pick_up_date_match = re.search(r"Pick up Date:\s*(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} (?:AM|PM))", email_str)
    if pick_up_date_match:
        date_str = pick_up_date_match.group(1)
        try:
            extracted_data['pick_up_date'] = datetime.strptime(date_str, '%m/%d/%Y %I:%M %p')
        except ValueError as e:
            print(f"Error parsing pick-up date: {date_str} - {e}")
            extracted_data['pick_up_date'] = datetime.now()
    else:
        extracted_data['pick_up_date'] = datetime.now()

    # Further processing for HTML part (if necessary)
    if 'text/html' in email_str:
        extract_table_from_html(email_str, extracted_data)

    return extracted_data



    # Function to extract details from text content
def extract_table_from_html(html_body, extracted_data):
    soup = BeautifulSoup(html_body, 'html.parser')
    tables = soup.find_all('table')  # Assuming the relevant items are in one of the tables
    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Assuming the first row contains header and skipping it
            cols = row.find_all('td')
            if len(cols) >= 3:  # Checking if there are at least three columns
                item_number = cols[0].get_text(strip=True)
                item_description = cols[1].get_text(strip=True)
                quantity = cols[2].get_text(strip=True)

                # Check for a valid quantity; it must be a digit
                if item_number and item_description and quantity.isdigit():
                    item_dict = {
                        'ItemNumber': item_number,
                        'ItemDescription': item_description,
                        'Quantity': int(quantity)
                    }
                    extracted_data['items'].append(item_dict)



    # Ensuring the dictionary is returned if used independently from the main parse function
    return extracted_data


def fetch_item_ordering(client, db_name='mydatabase', collection_name='items'):
    db = client[db_name]
    collection = db[collection_name]
    items_ordering = {}
    try:
        cursor = collection.find({})
        for item in cursor:
            item_number = str(item.get('ItemNumber'))
            order = item.get('Orderby', float('inf'))  # Use a large number for items without an ordering index
            items_ordering[item_number] = order
    except Exception as e:
        print(f"Failed to fetch item ordering: {e}")
    return items_ordering


def reorder_items(items, items_ordering):
    # Sort items based on the order provided in items_ordering
    items.sort(key=lambda x: items_ordering.get(x['ItemNumber'], float('inf')))
    return items


def process_order_email(raw_email, client):
    parsed_data = parse_email_content(raw_email)
    if parsed_data:
        insert_order_into_mongodb(parsed_data, client)


def extract_pdf_attachments_and_body(raw_email):
    email_message = email.message_from_bytes(raw_email, policy=default)
    attachments = []
    body_text = ""

    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                body_text = part.get_payload(decode=True).decode()  # Decode byte to str
            elif part.get_content_maintype() == 'application' and part.get_content_subtype() == 'pdf':
                filename = part.get_filename()
                if filename:
                    content = part.get_payload(decode=True)
                    attachments.append((filename, content))
    else:  # Not a multipart
        body_text = email_message.get_payload(decode=True).decode()

    return attachments, body_text

from email.header import decode_header, make_header




def fetch_unread_emails(email_address, password):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(email_address, password)
    mail.select('inbox')

    result, data = mail.search(None, 'UNSEEN')
    if result != 'OK':
        print("Failed to retrieve unread emails.")
        return []

    email_ids = data[0].split()
    emails = []

    for e_id in email_ids:
        result, email_data = mail.fetch(e_id, '(RFC822)')
        if result == 'OK':
            emails.append(email_data[0][1])

    mail.close()
    mail.logout()
    return emails


def classify_and_process_emails(emails, client):
    # Loop through each email
    for raw_email in emails:
        if is_inventory_email(raw_email):
            process_inventory_email(raw_email, client)
            print("IS")
        elif is_order_email(raw_email):
            process_order_email(raw_email, client)
            print("Order")
        else:
            print("Unknown email type.")

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve environment variables
    email_address = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')
    db_uri = os.getenv('DB_URI')

    # Connect to MongoDB using the URI from environment variables
    client = MongoClient(db_uri)

    # Assume fetch_unread_emails and classify_and_process_emails are defined elsewhere
    emails = fetch_unread_emails(email_address, password)
    classify_and_process_emails(emails, client)

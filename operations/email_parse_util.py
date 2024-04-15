import email as email_lib
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


def is_transfer_email(raw_email):
    """
    Checks if the email is a transfer email based on the attachment filenames.

    Args:
        raw_email (bytes): The raw email content.

    Returns:
        bool: True if the email is a transfer email, False otherwise.
    """
    # Parse the raw email content
    email_message = BytesParser(policy=policy.default).parsebytes(raw_email)

    # Check all parts of the email for attachments
    for part in email_message.iter_attachments():
        # Try to get the filename of the attachment
        filename = part.get_filename()
        if filename:
            # Check if the filename matches the transfer email pattern
            if filename.startswith("901.901_TruckTransferOut_"):
                return True

    return False


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

    if inventory_data and inventory_data['items']:  # Ensure there are items to save
        result = collection.insert_one(inventory_data)
        print(f"Inventory data inserted with record id: {result.inserted_id}")
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
            if item['ItemNumber'] not in inventory_item_numbers and item.get('Grand Total', 0) < 0:
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


def process_inventory_email(raw_email, client):
    attachments = extract_pdf_attachments(raw_email)
    for filename, content in attachments:
        inventory_data = parse_inventory_pdf(content)
        if inventory_data:
            insert_inventory_to_mongodb(inventory_data)
            identify_and_upload_oos_items()


def parse_email_content(email_content):
    msg = BytesParser(policy=policy.default).parsebytes(email_content)

    # Initial structure for extracted data
    extracted_data = {
        'email_id': msg.get('Message-ID'),  # Extract email ID
        'route_name': None,
        'route': None,
        'pick_up_date': None,
        'pick_up_time': None,
        'total_cases': None,
        'items': [],
        'additional_items_needed': None,
    }

    # Function to extract text content and handle forwarded emails
    def handle_forwarded_emails(text_content):
        forwarded_patterns = [
            "Forwarded message", "Begin forwarded message", "^From:", "^Sent:",
            "^To:", "Original Message", "^\-\- Forwarded message \-\-$"
        ]
        for pattern in forwarded_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                # Find the start of the original message and return the substring
                start = re.search(pattern, text_content, re.IGNORECASE).start()
                return text_content[start:]
        return text_content

    # Function to extract details from text content
    def extract_order_details(html_body):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_body, 'html.parser')
        text = soup.get_text(separator=' ')  # Use space as separator to prevent concatenation of words

        details_patterns = {
            'route_name': r"Route Name:\s*([^\n]+)",
            'route': r"Route Number:\s*([^\n]+)",
            'pick_up_date': r"Pick up Date:\s*([^\n]+)",
            'pick_up_time': r"Pick up Time:\s*([^\n]+)",
            'total_cases': r"Total Cases:\s*(\d+)",
            # Assuming 'Additional Items Needed' might not always be followed by identifiable content
            'additional_items_needed': r"Additional Items Needed:\s*([^\n]*)",
        }

        for key, pattern in details_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted_data[key] = match.group(1).strip()

        # Parse 'pick_up_date' specifically if present
        if extracted_data['pick_up_date']:
            try:
                extracted_data['pick_up_date'] = datetime.strptime(extracted_data['pick_up_date'], "%m/%d/%Y").date()
            except ValueError as e:
                print(f"Error parsing pick_up_date: {e}")
                extracted_data['pick_up_date'] = None

    # Function to parse HTML and extract table data
    def extract_table_from_html(html_body):
        soup = BeautifulSoup(html_body, 'html.parser')
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skipping the first row as it's assumed to be headers
                cols = row.find_all('td')
                if len(cols) >= 4:  # Ensuring there are at least 4 columns to match your structure
                    # Constructing a dictionary with explicit keys based on column positions
                    item_dict = {
                        'ItemNumber': cols[1].text.strip(),  # Assuming cols[1] is ItemNumber
                        'ItemDescription': cols[2].text.strip(),  # Assuming cols[2] is ItemDescription
                        'Quantity': cols[3].text.strip(),  # Assuming cols[3] is Quantity
                    }
                    extracted_data['items'].append(item_dict)

    # Extract content and apply parsing logic
    if msg.is_multipart():
        for part in msg.walk():
            part_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset('utf-8')
            if part_type == "text/plain":
                text_content = payload.decode(charset)
                text_content = handle_forwarded_emails(text_content)
                extract_order_details(text_content)
            elif part_type == "text/html":
                html_content = payload.decode(charset)
                extract_table_from_html(html_content)
                html_text_content = BeautifulSoup(html_content, 'html.parser').get_text()
                extract_order_details(html_text_content)
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset('utf-8')
        if content_type == "text/plain":
            text_content = payload.decode(charset)
            text_content = handle_forwarded_emails(text_content)
            extract_order_details(text_content)
        elif content_type == "text/html":
            html_content = payload.decode(charset)
            extract_table_from_html(html_content)
            html_text_content = BeautifulSoup(html_content, 'html.parser').get_text()
            extract_order_details(html_text_content)

    return extracted_data


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


# Extract 4-digit code from email body
from email import message_from_bytes
from email.header import decode_header, make_header


def extract_transfer_id_from_subject(raw_email_bytes):
    # Parse the raw email bytes into a MIME message object
    msg = message_from_bytes(raw_email_bytes)

    # Access the subject or other headers directly
    subject = str(make_header(decode_header(msg['subject'])))

    # Adjusted regular expression to match alphanumeric characters
    # This pattern assumes that the ID does not start with a digit.
    # Adjust the pattern as needed based on the expected format of your IDs.
    match = re.search(r'\b[A-Za-z0-9]+\b', subject)
    if match:
        return match.group(0)  # Return the first occurrence of alphanumeric pattern
    else:
        return None  # No ID found



# Parse PDF for transfer information

def parse_transfer_pdf(pdf_content):
    transfer_data = {
        'transfer_id': None,
        'route_number': None,
        'date': None,
        'user': None,
        'destination_route': None,
        'items': [],
        'primary_total': 0,
        'secondary_total': 0
    }

    doc = fitz.open("pdf", pdf_content)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    lines = text.split('\n')

    # Extracting date, route, user, and destination route
    transfer_data['date'] = lines[0].split('Printed on:')[1].split()[0]
    route_parts = lines[0].split('Route:')[1].strip().split(' - ')
    transfer_data['route_number'] = route_parts[1] if len(route_parts) > 1 else route_parts[0]

    transfer_data['user'] = lines[1].split('User:')[1].strip()

    for line in lines:
        if "Destination Route:" in line:
            transfer_data['destination_route'] = line.split("Destination Route:")[1].strip()
            break

    item_lines_started = False
    for line in lines:
        if "Destination Route" in line or "Item # Description UOM Transfer" in line:
            continue

        if "Total Quantity Primary" in line:
            try:
                # The \s+ accounts for one or more whitespace characters
                transfer_data['primary_total'] = int(re.search(r"Total Quantity Primary\s+(\d+)", line).group(1))
            except (ValueError, AttributeError):
                print("Could not parse primary total from line:", line)

        if "Total Quantity Secondary" in line:
            try:
                # Similarly, for secondary total
                transfer_data['secondary_total'] = int(re.search(r"Total Quantity Secondary\s+(\d+)", line).group(1))
            except (ValueError, AttributeError):
                print("Could not parse secondary total from line:", line)
            break  # Assuming no more relevant data after "Total Quantity Secondary"

        parts = line.split()
        if not item_lines_started:
            if parts[0] == "Item" and parts[-1] == "Transfer":
                item_lines_started = True
                continue

        if item_lines_started and len(parts) >= 3:
            if "Sales" in line or "Rep." in line or "Authorization" in line or line.startswith("Total Quantity"):
                continue

            # Ensure we do not process the lines for totals as items
            if parts[0].startswith("Total"):
                continue

            item_number = parts[0]
            description = " ".join(parts[1:-2])  # Ensure accurate parsing of description
            transfer_quantity = parts[-1]  # Ensure accurate capture of transfer quantity
            item_data = {
                'ItemNumber': item_number,
                'ItemDescription': description,
                'Quantity': transfer_quantity
            }
            transfer_data['items'].append(item_data)

    return transfer_data


    # Save to MongoDB


def insert_transfer_to_mongodb(transfer_data, client):
    db = client['mydatabase']
    collection = db['transfers']

    if transfer_data and 'transfer_id' in transfer_data and transfer_data['items']:
        # Create a filter for the transfer ID
        filter = {'transfer_id': transfer_data['transfer_id']}
        # Update the document with the new transfer data, or insert it if it doesn't exist
        result = collection.update_one(filter, {'$set': transfer_data}, upsert=True)

        # Check if the operation resulted in an update or insert (upsert)
        if result.upserted_id:
            print(f"Transfer data inserted with record id: {result.upserted_id}")
        else:
            print(f"Transfer data updated for transfer_id: {transfer_data['transfer_id']}")
    else:
        print("Invalid transfer data. Make sure it contains 'transfer_id' and 'items'.")

    # client.close()


def process_transfer_email(raw_email, client):
    attachments, body_text = extract_pdf_attachments_and_body(raw_email)
    transfer_id = extract_transfer_id_from_subject(raw_email)  # Now extracting from subject

    for filename, content in attachments:
        transfer_data = parse_transfer_pdf(content)
        if transfer_data and transfer_id:
            transfer_data['transfer_id'] = transfer_id  # Include the transfer ID in your transfer data
            insert_transfer_to_mongodb(transfer_data, client)


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
        elif is_transfer_email(raw_email):
            process_transfer_email(raw_email, client)
            print("TR")
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

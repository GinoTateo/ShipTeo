import os
import email as email_lib
from pymongo import MongoClient
import imaplib
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
import re
from datetime import datetime



def fetch_last_email_content(email_address, password):
    """
    Connects to a Gmail account and fetches the content of the last email in the inbox.

    :param email_address: Your Gmail email address.
    :param password: Your Gmail password or app-specific password.
    :return: Raw email content of the last email.
    """
    try:
        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_address, password)
        mail.select('inbox')

        # Search for all emails in the inbox
        status, email_ids = mail.search(None, 'ALL')
        if status != 'OK':
            print("No emails found!")
            return None

        # Fetch the last email ID
        last_email_id = email_ids[0].split()[-1]
        status, email_data = mail.fetch(last_email_id, '(RFC822)')
        if status != 'OK':
            print("Failed to fetch the email.")
            return None

        raw_email = email_data[0][1]

        # Close the connection and logout
        mail.close()
        mail.logout()

        return raw_email, last_email_id.decode()
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# Example usage
# email_content = fetch_last_email_content('your_email@gmail.com', 'your_password')


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


# Example usage
# raw_email_content = fetch_last_email_content('your_email@gmail.com', 'your_password')
# parsed_data = parse_email(raw_email_content)

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

    if not extracted_data.get('pick_up_date'):
        try:
            pick_up_date = datetime.today()
        except ValueError as e:
            print(f"Error parsing pick_up_date: {e}")
            pick_up_date = None
    else:
        pick_up_date = extracted_data.get('pick_up_date')

    total_cases = sum(item.get('Quantity', 0) for item in extracted_data.get('items', []))

    order_document = {
        'route_name': extracted_data.get('route_name'),
        'route': extracted_data.get('route_number'),
        'pick_up_date': pick_up_date,
        'pick_up_time': extracted_data.get('pick_up_time'),
        'total_cases': total_cases,
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


# Example usage
# parsed_data = parse_email(raw_email_content)
# insert_order_into_mongodb(parsed_data)
def get_last_parsed_email_id(client, db_name='mydatabase', status_collection='status'):
    db = client[db_name]
    collection = db[status_collection]
    status_document = collection.find_one({'variable': 'last_parsed'})
    last_parsed_email_id = status_document.get('value') if status_document else None
    return last_parsed_email_id


def get_latest_email_id(email_address, password):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(email_address, password)
    mail.select('inbox')
    status, email_ids = mail.search(None, 'ALL')
    if status != 'OK':
        print("No emails found!")
        return None
    last_email_id = email_ids[0].split()[-1].decode()
    mail.close()
    mail.logout()
    return last_email_id


def fetch_unread_emails(email_address, password):
    """
    Fetches unread emails from the Gmail account.
    """
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(email_address, password)
    mail.select('inbox')

    # Search for unread emails
    result, data = mail.search(None, 'UNSEEN')
    if result != 'OK':
        print("Failed to retrieve unread emails.")
        return []

    if data is None:
        print("All orders parsed")

    email_ids = data[0].split()
    emails = []

    for e_id in email_ids:
        result, email_data = mail.fetch(e_id, '(RFC822)')
        if result == 'OK':
            emails.append(email_data[0][1])

    mail.close()
    mail.logout()
    return emails


def check_and_parse_new_emails(email_address, email_password, client, db_name='mydatabase', orders_collection='orders'):
    """
    Fetches unread emails, parses them, and inserts order details into MongoDB.
    """
    unread_emails = fetch_unread_emails(email_address, email_password)

    for raw_email in unread_emails:
        email_message = email_lib.message_from_bytes(raw_email)
        subject = str(email_lib.header.make_header(email_lib.header.decode_header(email_message['Subject'])))

        # Updated condition to check the subject line
        if 'Route Order for' in subject:
            parsed_data = parse_email_content(raw_email)
            if parsed_data is not None:
                insert_order_into_mongodb(parsed_data, client, db_name, orders_collection)


def parse_and_reorder_email(email_content, client):
    # Parsing the email content
    extracted_data = parse_email_content(email_content)

    # Fetch the ordering for items
    items_ordering = fetch_item_ordering(client)

    # Reorder items based on fetched order
    if 'items' in extracted_data and extracted_data['items']:
        extracted_data['items'] = reorder_items(extracted_data['items'], items_ordering)

    return extracted_data


# Example usage
# client = MongoClient('mongodb://localhost:27017/')  # or your MongoDB connection details
# check_and_parse_new_emails('your_email@gmail.com', 'your_password', client)

def order_main():


    email = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')
    uri = os.getenv('DB_URI')

    client = MongoClient(uri)

    check_and_parse_new_emails(email, password, client, 'mydatabase', 'orders')


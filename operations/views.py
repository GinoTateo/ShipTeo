import json
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from reportlab.pdfgen import canvas
import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import JsonResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from pymongo import MongoClient
from reportlab.lib.pagesizes import letter

from account.decorators import user_is_warehouse_manager, user_is_warehouse_worker, user_is_rsr
from operations.Approval_Backend import approval_main
from operations.Inventory_Backend import inventory_main
from operations.Order_Backend import order_main
from django.core.paginator import Paginator

# Constants

load_dotenv()  # This method will load variables from a .env file

MONGO_URI = os.environ.setdefault('DB_URI', 'DB_URI')

routes = {
    "RTC0003",
    "RTC00013",
    "RTC00018",
    "RTC00019",
    "RTC00089",
    "RTC000377",
    "RTC000379",
    "RTC000649",
    "RTC000700",
    "RTC000719",
    "RTC0004",
    "RTC000127",
    "RTC000433",
    "RTC000647",
    "RTC000720",
    "RTC000730",
    "RTC000731",
    "RTC000765",
    "RTC000783",
    "RTC000764",
    "RTC0002",
}

ship_to_routes = {
    "RTC0003",
    "RTC00013",
    "RTC00018",
    "RTC00019",
    "RTC00089",
    "RTC000377",
    "RTC000379",
    "RTC000649",
    "RTC000700",
    "RTC000719",
    }

class MongoConnection:
    _client = None

    @staticmethod
    def get_client():
        if MongoConnection._client is None:
            MongoConnection._client = MongoClient(MONGO_URI)
            logging.info("MongoDB client initialized")
        return MongoConnection._client

    @staticmethod
    def close_client():
        if MongoConnection._client is not None:
            MongoConnection._client.close()
            MongoConnection._client = None
            logging.info("MongoDB client closed")


@login_required
@user_is_warehouse_worker
def warehouse_dashboard(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    inventory_stats = db['inventory_stats'].find_one(sort=[("_id", -1)]) or {}
    total_out_of_stocks = inventory_stats.get('num_oos_items', 0)
    inventory_status = inventory_stats.get('total_inventory', 0)
    pending_orders_count = db['orders'].count_documents({"status": "Pending"})

    return render(request, 'warehouse/warehouse_dashboard.html', {
        'total_out_of_stocks': total_out_of_stocks,
        'inventory_status': inventory_status,
        'pending_orders': pending_orders_count
    })


def build_order_query(filters):
    query = {}
    if filters['date']:
        start_of_day = datetime.fromisoformat(filters['date'])
        end_of_day = start_of_day + timedelta(days=1)
        query['pick_up_date'] = {"$gte": start_of_day, "$lt": end_of_day}
    if filters['status']:
        query['status'] = filters['status']
    if filters['route']:
        query['route'] = filters['route']
    return query


@login_required
@user_is_warehouse_worker
def edit_order(request, order_id):
    if request.method != 'POST':
        return HttpResponse("Invalid request method", status=405)

    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['orders']
    result = collection.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': "Preparing"}}
    )
    if result.matched_count == 0:
        return HttpResponse("Order not found", status=404)

    return redirect('ops:edit_order', order_id=order_id)


@user_is_warehouse_worker
def complete_order(request, order_id):
    try:
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        collection = db['orders']

        # Retrieve the order to get the start time
        order = collection.find_one({'_id': ObjectId(order_id)})

        completion_time = datetime.now()

        if not order:
            print("No order found with the specified ID.")
            client.close()
            return HttpResponse("Order not found", status=404)

        start_time = order.get('start_time')

        # Calculate the duration if start_time exists
        if start_time:
            duration = completion_time - start_time
            duration_in_seconds = duration.total_seconds()
        else:
            duration_in_seconds = 0
            # Optionally convert to minutes or hours as needed

        # Update the order's status to "Complete" and completion time
        result = collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': "Complete", 'completion_time': completion_time,
                      'duration_seconds': duration_in_seconds}}
        )

        # Check if the order was successfully updated
        if result.matched_count == 0:
            # No order was found with the provided ID
            print("No order found with the specified ID.")
            client.close()
            return HttpResponse("Order not found", status=404)

        # Retrieve the updated order for rendering
        order = collection.find_one({'_id': ObjectId(order_id)})
    except Exception as e:
        print(f"An error occurred: {e}")
        client.close()
        return HttpResponse("Error connecting to database", status=500)

    client.close()
    return JsonResponse({'success': True})


def calculate_duration(start_time, end_time):
    if not start_time:
        return 0
    return (end_time - start_time).total_seconds()


@user_is_warehouse_worker
def prepare_order(request, order_id):
    if request.method != 'POST':
        return HttpResponse("Invalid request method", status=405)

    client = MongoConnection.get_client()
    collection = client['mydatabase']['orders']
    builder_name = request.POST.get('builder_name', 'Default Builder')
    start_time = datetime.now()

    result = collection.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': "Preparing", 'builder_name': builder_name, 'start_time': start_time}}
    )

    if result.matched_count == 0:
        return HttpResponse("Order not found", status=404)

    # Redirect to a PDF generation view or another relevant view
    return redirect('../pdf', order_id=order_id)


# Here
@login_required
@user_is_warehouse_worker
def orders_view(request):
    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['mydatabase']
    collection = db['orders']

    # Getting filter parameters from the request
    date = request.GET.get('date')
    status = request.GET.get('status')
    route = request.GET.get('route')
    page_number = request.GET.get('page', 1)  # Getting the page number, default is 1


    # Building the query based on the filters
    query = {}
    if date:
        start_of_day = datetime.fromisoformat(date)
        end_of_day = start_of_day + timedelta(days=1)
        query['pick_up_date'] = {"$gte": start_of_day, "$lt": end_of_day}
    if status:
        query['status'] = status
    if route:
        query['route'] = route

    # Sort orders by date descending to get the newest orders first
    orders = list(collection.find().sort('$natural', -1))

    for order in orders:
        order['order_id'] = str(order['_id'])

    # Apply pagination
    paginator = Paginator(orders, 15)  # Show 15 orders per page
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/order_view.html', {'page_obj': page_obj, 'routes': routes})


@login_required
@user_is_warehouse_worker
def order_detail_view(request, order_id):
    edit_mode = 'edit' in request.GET and request.GET['edit'] == 'true'

    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['orders']
    items_collection = db['mapped_items']

    order = collection.find_one({'_id': ObjectId(order_id)})
    if not order:
        raise Http404("Order not found")

    # Extract item numbers and fetch related data
    order_item_numbers = [item['ItemNumber'] for item in order.get('items', [])]
    available_items = list(items_collection.find({'ItemNumber': {'$nin': order_item_numbers}}))

    if request.method == 'POST' and edit_mode:
        # Assuming each item in the form is prefixed with 'item_', followed by the item's index or ID
        # and the field names are appended with '_description', '_quantity', and '_inStock'
        process_order_edits(request, order, collection)
        # Redirect to avoid resubmitting the form on refresh
        return HttpResponseRedirect(reverse('ops:detail_order_view', args=[order_id]))

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'available_items': available_items,
    })


def process_order_edits(request, order, collection):
    for key, value in request.POST.items():
        if key.startswith('items_') and key.endswith('_quantity'):
            item_id = key.split('_')[1]
            new_quantity = request.POST.get(f'items_{item_id}_quantity')
            in_stock = request.POST.get(f'items_{item_id}_inStock') == 'true'

            for item in order.get('items', []):
                if str(item.get('ItemNumber')) == item_id:
                    item['Quantity'] = int(new_quantity)
                    item['InStock'] = in_stock
                    break

    collection.update_one({'_id': ObjectId(order['id'])}, {'$set': {'items': order['items']}})


def fetch_item_ordering(client, db_name='mydatabase', collection_name='items'):
    db = client[db_name]
    collection = db[collection_name]
    items_ordering = {}
    try:
        cursor = collection.find({})
        for item in cursor:
            item_number = str(item.get('ItemNumber'))
            order = int(item.get('Orderby', float('inf')))  # Convert to int, use float('inf') as default
            items_ordering[item_number] = order
    except Exception as e:
        print(f"Failed to fetch item ordering: {e}")
    return items_ordering


def reorder_items(items, items_ordering):
    items.sort(key=lambda x: items_ordering.get(x['ItemNumber'], float('inf')))
    return items


@login_required
@user_is_warehouse_worker
def generate_order_pdf(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['orders']
    oos_items_collection = db['oos_items']
    mapped_items_collection = db['mapped_items']

    # Fetch OOS items
    oos_items_cursor = oos_items_collection.find({})
    oos_items = [doc["ItemNumber"] for doc in oos_items_cursor]

    # Initialize dictionaries
    item_to_location = {}
    item_to_type = {}

    # Fetch location and type mappings from the 'mapped_items' collection in one go
    try:
        for doc in mapped_items_collection.find({}):
            try:
                # Ensure ItemNumber is an integer
                item_number = int(doc['ItemNumber'])
            except (ValueError, KeyError, TypeError):
                print(f"Error converting or finding ItemNumber in document: {doc}")
                continue

            item_to_location[item_number] = doc.get("Location", "N/A")
            item_to_type[item_number] = doc.get("Type", "N/A")  # Assuming 'Type' is the correct field name
    except Exception as e:
        print(f"An error occurred: {e}")


    order = collection.find_one({'_id': ObjectId(order_id)})

    # Fetch item ordering from the 'items' collection
    items_ordering = fetch_item_ordering(client, 'mydatabase', 'items')

    # Reorder the items in the order based on the 'Orderby' field
    ordered_items = reorder_items(order.get('items', []), items_ordering)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="order_{order_id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Initialize totals
    total_quantity = 0
    adjusted_total_quantity = 0

    for item in ordered_items:
        item_number = item.get('ItemNumber', '')
        try:
            quantity = int(item.get('Quantity', 0))
            total_quantity += quantity  # Add to total quantity
            if int(item_number) not in oos_items:
                adjusted_total_quantity += quantity  # Add to adjusted total if not OOS

        except ValueError:
            # Log error or handle the case where the quantity is not an integer
            print(f"Warning: Invalid quantity '{item.get('Quantity')}' for item number {item_number}")

    p.setFont("Helvetica-Bold", 12)
    formatted_date = order.get('pick_up_date').strftime('%B %d, %Y')
    p.drawString(30, height - 30, f"Date: {formatted_date}")

    # Set font to Helvetica-Bold for headers
    tid = order.get("transfer_id")
    p.setFont("Helvetica-Bold", 12)
    route_number = order.get('route', 'N/A')
    route_type = "Ship-to" if route_number in ship_to_routes else "Pick-up"
    p.drawString(30, height - 50, f"Route Number: {route_number} ({route_type}) ")
    p.setFont("Helvetica", 12)

    # Move total quantity and related information to the top right
    p.drawString(width - 300, height - 50, f"Total Quantity Ordered: {total_quantity}")
    p.drawString(width - 300, height - 70, f"Total After OOS Adjustments: {adjusted_total_quantity}")
    p.drawString(width - 300, height - 90, "Physical Count:")
    p.rect(width - 180, height - 92, 50, 15)  # Adjustment input box

    # Starting position adjustment for item list
    y_position = height - 120

    p.setFont("Helvetica-Bold", 12)
    # Draw column headers, including a new column for 'Location'
    p.drawString(30, y_position, "Item Number")
    p.drawString(150, y_position, "Description")
    p.drawString(340, y_position, "Location")
    # Adjust existing columns to make room for the new 'Location' column
    p.drawString(475, y_position, "Quantity")  # New location column
    p.drawString(530, y_position, "Status")
    p.drawString(630, y_position, "Check")  # Checkboxes moved to the far right

    # Revert to normal font for item details
    p.setFont("Helvetica", 12)

    # Adjust y_position for first item row
    y_position -= 20

    for item in ordered_items:
        quantity = item.get('Quantity', 0)

        # Skip items with no quantity or quantity set to 0
        if not quantity:
            continue

        # Draw a line to separate this item from the next
        p.line(30, y_position - 2, 580, y_position - 2)  # Adjust line length as needed

        item_number = item.get('ItemNumber', 'Unknown')

        description = item.get('ItemDescription', 'N/A')
        stock_status = "IS" if int(item_number) not in oos_items else "OOS"

        # Drawing item details (keep this part unchanged)
        p.drawString(30, y_position, str(item_number))
        p.drawString(150, y_position, description)
        p.drawString(475, y_position, str(quantity))

        # If the item is out of stock, cross out the quantity
        if stock_status == "OOS":
            # Calculate width of the quantity text for precise line drawing
            quantity_text_width = p.stringWidth(str(quantity), "Helvetica", 12)
            # Draw a line through the quantity text
            p.line(475, y_position + 4, 480 + quantity_text_width, y_position + 4)

        # Draw the location next to each item
        item_location = item_to_location.get(int(item_number), "N/A")
        p.drawString(360, y_position, item_location)
        p.rect(340, y_position - 2, 12, 12, stroke=1, fill=0)  # Checkbox

        # Draw the placeholder box for adjustment quantity, stock status, and checkbox
        p.rect(495, y_position - 2, 25, 15)  # Placeholder box for adjustment quantity
        p.drawString(530, y_position, stock_status)  # Include stock status
        p.rect(630, y_position - 2, 12, 12, stroke=1, fill=0)  # Checkbox

        # Move to the next line
        y_position -= 20

        # Check if we need to start a new page
        if y_position < 50:
            p.showPage()
            y_position = height - 50


    p.setTitle(route_number)
    p.showPage()
    p.save()
    return response


@login_required
def inventory_view(request):
    try:
        client = MongoConnection.get_client()
        db = client['mydatabase']
        # Fetch the latest inventory
        latest_inventory = db['inventory'].find_one(sort=[("_id", -1)])
        inventory_items = latest_inventory.get('items', []) if latest_inventory else []
        # Fetch Out-of-Stock items directly
        oos_items = list(db['oos_items'].find({}, {'ItemNumber': 1, 'ItemDescription': 1}))
    except Exception as e:
        return HttpResponse(f"Error connecting to database: {str(e)}", status=500)

    return render(request, 'inventory/inventory_list.html', {
        'inventory_items': inventory_items,
        'OOS_items': oos_items,
    })


def get_item_description(item_number, items_list):
    # Attempt to find an item description from a list of items
    for item in items_list:
        if item['ItemNumber'] == item_number:
            return item.get('ItemDescription', 'N/A')
    return 'Description Unavailable'


@login_required
def verify_order(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    orders_collection = db['orders']
    transfers_collection = db['transfers']
    oos_items_collection = db['oos_items']
    # Fetching OOS item numbers
    oos_item_numbers = {doc['ItemNumber'] for doc in oos_items_collection.find({}, {'ItemNumber': 1})}
    # Fetch the order and corresponding transfer
    order = orders_collection.find_one({'_id': ObjectId(order_id)})
    matching_transfer = transfers_collection.find_one(
        {"transfer_id": {"$regex": ".*" + str(order['_id'])[-4:] + "$"}})
    if not order or not matching_transfer:
        return render(request, 'error_page.html', {'error': "Transfer not found in database."})
    # Preparing data for the template
    items_with_variances, adjustments = calculate_variances(order, matching_transfer, oos_item_numbers)

    return render(request, 'orders/order_verification.html', {
        'order': order,
        'matching_transfer': matching_transfer,
        'order_items': items_with_variances,
        'adjustments': adjustments,
    })


def calculate_variances(order, matching_transfer, oos_item_numbers):
    order_item_dict = {item['ItemNumber']: item for item in order.get('items', [])}
    transfer_item_dict = {item['ItemNumber']: item for item in matching_transfer.get('items', [])}
    items_with_variances = []
    adjustments = 0
    # Calculating variances and adjustments
    for item_number, order_item in order_item_dict.items():
        order_quantity = int(order_item['Quantity'])
        transfer_item = transfer_item_dict.get(item_number)
        if transfer_item:
            transfer_quantity = int(transfer_item['Quantity'])
            variance = transfer_quantity - order_quantity
            adjustments += variance
            items_with_variances.append({
                'ItemNumber': item_number,
                'ItemDescription': order_item.get('ItemDescription', 'N/A'),
                'OrderQuantity': order_quantity,
                'TransferQuantity': transfer_quantity,
                'Variance': variance,
                'IsOOS': item_number in oos_item_numbers,
            })
            del transfer_item_dict[item_number]
        else:
            items_with_variances.append({
                'ItemNumber': item_number,
                'ItemDescription': order_item.get('ItemDescription', 'N/A'),
                'OrderQuantity': order_quantity,
                'TransferQuantity': 0,
                'Variance': -order_quantity,
                'IsOOS': item_number in oos_item_numbers,
            })
    # Include transferred but not ordered items
    for item_number, transfer_item in transfer_item_dict.items():
        transfer_quantity = int(transfer_item['Quantity'])
        item_description = get_item_description(item_number,
                                                order.get('items', []) + matching_transfer.get('items', []))
        adjustments += transfer_quantity
        items_with_variances.append({
            'ItemNumber': item_number,
            'ItemDescription': item_description,
            'OrderQuantity': 0,
            'TransferQuantity': transfer_quantity,
            'Variance': transfer_quantity,
            'IsOOS': False,
        })
    return items_with_variances, adjustments


@require_http_methods(["GET", "POST"])
def place_order_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order = {
                'date': data.get('date'),
                'route': data.get('route'),
                'orders': data.get('orders', []),  # Ensure default is a list if not provided
                'status': data.get('status', 'Received'),
                'transfer_id': data.get('transfer_id')
            }

            client = MongoConnection.get_client()
            db = client['mydatabase']
            order_id = db['orders'].insert_one(order).inserted_id

            return JsonResponse({'message': 'Order placed successfully', 'order_id': str(order_id)}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return render(request, 'orders/place_order.html')


@login_required
def list_items_view(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    items_cursor = db['items'].find({})
    items_by_type = {}

    for item in items_cursor:
        item_type = item.get('Item_Type', 'Other')
        processed_item = {k.replace(' ', '_'): v for k, v in item.items()}

        if item_type not in items_by_type:
            items_by_type[item_type] = []
        items_by_type[item_type].append(processed_item)

    return render(request, 'warehouse/list_items.html', {'items_by_type': items_by_type})


@user_is_warehouse_worker
@require_http_methods(["GET", "POST"])
def review_order_view(request):
    if request.method == 'POST':
        items = []
        for key, value in request.POST.items():
            if key.startswith('item_number_'):
                try:
                    _, type_index, item_index = key.split('_')
                    item_number = value
                    item_description_key = f'item_description_{type_index}_{item_index}'
                    quantity_key = f'quantity_{type_index}_{item_index}'

                    item_description = request.POST.get(item_description_key, 'Description Unavailable')
                    quantity = int(request.POST.get(quantity_key, 0))

                    transformed_item = {
                        'Item_Number': item_number,
                        'Item_Description': item_description,
                        'Quantity': quantity
                    }
                    items.append(transformed_item)
                except Exception as e:
                    print(f"Error processing item details: {e}")
                    return HttpResponse("There was an error processing your request. Please check your data.",
                                        status=400)

        # Store the review items in the session after validation
        request.session['order_review'] = items

        # Redirect to avoid resubmission on page refresh
        return redirect('review_order')  # Assuming there's a URL name 'review_order' configured

    # If GET request or no items to review, redirect to the item listing page
    return redirect('list_items')


@login_required
@require_POST
def submit_order(request):
    order_items = request.session.pop('order_review', None)
    if not order_items:
        return JsonResponse({'error': 'Session expired or order details missing.'}, status=400)

    try:
        client = MongoConnection.get_client()
        db = client['mydatabase']
        orders_collection = db['orders2']

        order = {
            'orders': order_items,
            'status': 'Received',
            # Additional fields like 'date' and 'customer_id' can be included here
        }
        result = orders_collection.insert_one(order)
        order_id = result.inserted_id

    except Exception as e:
        # If there's an error in saving, re-add items to the session
        request.session['order_review'] = order_items
        return JsonResponse({'error': f'Failed to place order: {str(e)}'}, status=500)

    return JsonResponse({'message': 'Order submitted successfully', 'order_id': str(order_id)}, status=201)


def inventory_with_6week_avg(request):
    try:
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        inventory_collection = db['inventory']
        items_collection = db['items']

        # Fetch the latest inventory snapshot
        latest_inventory = inventory_collection.find().sort("_id", -1).limit(1).next()
        inventory_items = latest_inventory['items']

        items_with_avg = []
        for inventory_item in inventory_items:
            item_num = inventory_item.get('ItemNumber')
            item_data = items_collection.find_one({'ItemNumber': item_num})
            if item_data:
                avg_value = item_data.get('AVG', 0)

                # Check if AVG is NaN or not a valid number and handle it
                try:
                    avg = round(float(avg_value) if avg_value is not str else 0, 1)
                except ValueError:
                    avg = 0

                try:
                    current_cases = int(inventory_item.get('Cases', 0))
                except ValueError:
                    current_cases = 0

                # Calculate weeks of supply based on the six_week_avg; prevent division by zero
                try:
                    weeks_of_supply = current_cases / -avg if avg is not str else 'N/A'
                except:
                    weeks_of_supply = 0

                wos = round(abs(weeks_of_supply), 1)

                items_with_avg.append({
                    'ItemName': item_data.get('ItemDescription'),
                    'ItemNumber': item_num,
                    'Cases': current_cases,
                    'avg': avg,
                    'WeeksOfSupply': wos
                })

    except Exception as e:
        print(f"An error occurred: {e}")
        return HttpResponse("Error connecting to database", status=500)

        # Render the weeks of supply in the template
    return render(request, 'inventory/inventory_with_avg.html', {'items_with_avg': items_with_avg})


def inventory_visualization_view(request):
    selected_week = request.GET.get('week', 'Week 1')  # Default to 'Week 1' if not specified
    client = MongoConnection.get_client()
    db = client['mydatabase']
    items_collection = db['items']

    items_data = list(items_collection.find())

    # Initialize DataFrame columns
    data = {'Item Number': [], 'Item Description': [], 'Transferred Items': []}

    # Populate DataFrame with data for the selected week
    for item in items_data:
        week_value = item.get(selected_week, 0) if selected_week in item else 0
        data['Item Number'].append(item['ItemNumber'])
        data['Item Description'].append(item['ItemDescription'])
        data['Transferred Items'].append(abs(week_value))  # Use absolute value for transferred items

    df = pd.DataFrame(data)

    # Create visualization with Plotly
    fig = px.bar(df, x='Item Description', y='Transferred Items',
                 title=f'Transfers for {selected_week}')
    plot_div = fig.to_html(full_html=False)

    # client.close()

    return render(request, 'inventory/inventory_plot.html', {'plot_div': plot_div, 'selected_week': selected_week})


def weekly_trend_view(request, item_type):
    selected_week = request.GET.get('week', 'Week 1')  # Default to 'Week 1' if not specified
    client = MongoConnection.get_client()
    db = client['mydatabase']
    items_collection = db['items']

    items_data = list(items_collection.find())

    # Initialize DataFrame columns
    data = {'ItemNumber': [], 'Item Description': [], 'Transferred Items': []}

    # Populate DataFrame with data for the selected week
    for item in items_data:
        week_value = item.get(selected_week, 0) if selected_week in item else 0
        data['ItemNumber'].append(item['ItemNumber'])
        data['ItemDescription'].append(item['ItemDescription'])
        data['Transferred Items'].append(abs(week_value))  # Use absolute value for transferred items

    df = pd.DataFrame(data)

    # Filter DataFrame by selected item type
    df_filtered = df[df['Item Type'] == item_type]

    # Assuming you have weekly data columns like 'Week 1', 'Week 2', etc., in your items_data
    weeks = [f'Week {i}' for i in range(1, 53)]  # Example for 52 weeks
    weekly_transfers = {week: df_filtered[week].sum() for week in weeks if week in df_filtered}

    # Convert to DataFrame for plotting
    df_weekly = pd.DataFrame(list(weekly_transfers.items()), columns=['Week', 'Transferred Items'])

    # Create visualization
    fig = px.line(df_weekly, x='Week', y='Transferred Items',
                  title=f'Weekly Trend of Transferred Items for {item_type}')
    plot_div = fig.to_html(full_html=False)

    # Close MongoDB connection and return the plot
    # client.close()
    return render(request, 'inventory/inventory_plot.html', {'plot_div': plot_div, 'item_type': item_type})


def comparison_across_weeks_view(request):
    selected_week = request.GET.get('week', 'Week 1')  # Default to 'Week 1' if not specified
    client = MongoConnection.get_client()
    db = client['mydatabase']
    items_collection = db['items']

    items_data = list(items_collection.find())

    # Initialize DataFrame columns
    data = {'Item Number': [], 'Item Type': [], 'Item Description': [], 'Transferred Items': []}

    # Populate DataFrame with data for the selected week
    for item in items_data:
        week_value = item.get(selected_week, 0) if selected_week in item else 0
        data['Item Number'].append(item['Item Number'])
        data['Item Type'].append(item['Item Type'])
        data['Item Description'].append(item['Item Description'])
        data['Transferred Items'].append(abs(week_value))  # Use absolute value for transferred items

    df = pd.DataFrame(data)

    # You need to pivot your data to have weeks as columns and item types as rows with transferred items as values
    # This example assumes you have manipulated your DataFrame 'df' accordingly

    # Pivoting DataFrame for Plotly
    df_pivot = df.pivot_table(index='Week', columns='Item Type', values='Transferred Items',
                              aggfunc='sum').reset_index()

    # Create visualization
    fig = px.line(df_pivot, x='Week', y=df_pivot.columns[1:], title='Comparison of Item Types Across Weeks',
                  markers=True)
    plot_div = fig.to_html(full_html=False)

    # Close MongoDB connection and return the plot
    # client.close()
    return render(request, 'inventory/inventory_plot.html', {'plot_div': plot_div})


@user_is_warehouse_worker
def update_order(request, order_id):
    if request.method == 'POST':
        client = MongoConnection.get_client()
        db = client['mydatabase']
        collection = db['orders']

        # Processing posted items data
        items_data = [key for key in request.POST if key.startswith('items_')]
        for item_key in items_data:
            _, index, field = item_key.split('_')
            index = int(index)  # Convert to integer to use as list index
            new_value = request.POST[item_key]

            # For fields that need to be converted into specific types, add checks and conversions here
            if field == 'Quantity':
                new_value = int(new_value)  # Assuming Quantity should be an integer

            # MongoDB update operation
            update_result = collection.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {f'items.{index}.{field}': new_value}}
            )

            if update_result.matched_count == 0:
                # Handle case where no matching document was found
                # client.close()
                return HttpResponse("Order not found.", status=404)

        # client.close()
        # Redirect to the order detail page or another appropriate page after the update
        return redirect('ops:detail_order_view', order_id=order_id)
    else:
        # Handle GET request or other methods if necessary
        return HttpResponse("Method not allowed", status=405)


@require_POST
@csrf_exempt
def add_items(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']

    # Parse the request body to JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON format: {str(e)}'}, status=400)

    selected_items_with_quantities = data.get('selected_items', [])

    if not selected_items_with_quantities:
        return JsonResponse({'error': 'No items provided'}, status=400)

    # Fetch and prepare items to be added
    items_to_add = []
    for item in selected_items_with_quantities:
        item_number = item.get('itemNumber')
        quantity = item.get('quantity')
        description = item.get('description')  # This is coming from the frontend.

        # Ensure all required fields are present
        if item_number and quantity and description:
            # Construct the item object according to the correct schema.
            item_to_add = {
                "ItemNumber": item_number,
                "ItemDescription": description,  # Ensure this matches your DB schema.
                "Quantity": int(quantity)
            }
            items_to_add.append(item_to_add)

    if not items_to_add:
        return JsonResponse({'error': 'No valid items to add'}, status=404)

    # Update the order document by appending the items with quantities
    update_result = db['orders'].update_one(
        {"_id": ObjectId(order_id)},
        {"$push": {"items": {"$each": items_to_add}}}
    )

    if update_result.modified_count == 0:
        return JsonResponse({'error': 'Order not found or no new items added'}, status=404)

    return JsonResponse({'success': True, 'message': 'Items successfully added to the order'})


@require_POST
@csrf_exempt
def delete_item(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']

    # Parse the request body to JSON
    try:
        data = json.loads(request.body)
        item_number = data.get('itemNumber')
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON format: {str(e)}'}, status=400)

    if not item_number:
        return JsonResponse({'error': 'Item number is required'}, status=400)

    # Update the order document by removing the item
    update_result = db['orders'].update_one(
        {"_id": ObjectId(order_id)},
        {"$pull": {"items": {"ItemNumber": item_number}}}
    )

    if update_result.modified_count == 0:
        return JsonResponse({'error': 'Order not found or item not found'}, status=404)

    return JsonResponse({'success': True, 'message': 'Item successfully deleted from the order'})


@csrf_exempt
def trigger_process_order(request):
    response_data = order_main()
    return JsonResponse(response_data, safe=False)


@csrf_exempt
def trigger_process_inventory(request):
    response_data = inventory_main()
    return JsonResponse(response_data, safe=False)


@user_is_warehouse_worker
def update_builder(request, order_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    try:
        client = MongoConnection.get_client()
        db = client['mydatabase']
        collection = db['orders']

        try:
            data = json.loads(request.body)
            builder_name = data.get('builder_name')
            start_time = datetime.now()

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Missing builder_name' + e}, status=400)

        # Perform the update
        result = collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': "Preparing", 'builder_name': builder_name, 'start_time': start_time}}
        )

        if result.modified_count == 1:
            return JsonResponse({'status': 'success', 'message': 'Builder updated successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Order not found or no update needed'}, status=404)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def fetch_suggested_order(route_number):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db.suggested_order

    suggested_order = collection.find_one({
        'route': route_number,
    })

    return suggested_order


@login_required  # Ensure the user is logged in
def create_order(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db.items

    if request.method == 'GET':
        # Fetch items from MongoDB
        items_cursor = collection.find()
        items_by_type = {}
        for item in items_cursor:
            item_type = item.get('ItemType')
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)

        # Determine the user's route number if logged in
        user_route_number = request.user.route_number if request.user.is_authenticated else None

        # Fetch suggested order for the user's route number
        suggested_order = fetch_suggested_order(user_route_number) if user_route_number else None

        # Passing items grouped by type to the template
        context = {
            'items_by_type': items_by_type,
            'routes': routes if not user_route_number else None,
            'user_route_number': user_route_number,
            'suggested_order': suggested_order,
        }
        return render(request, 'orders/create_order.html', context)

    elif request.method == 'POST':
        # Use user route number if logged in, otherwise get from form
        route_number = request.user.route_number if request.user.is_authenticated else request.POST.get('routeNumber')

        # Process item quantities and descriptions
        order_items = []
        for key, value in request.POST.items():
            if key.startswith('quantity_') and value.isdigit() and int(value) > 0:
                ItemNumber = key.split('_')[1]
                Quantity = int(value)
                ItemDescription = request.POST.get(f'description_{ItemNumber}')
                order_items.append({'ItemNumber': ItemNumber, 'ItemDescription': ItemDescription, 'Quantity': Quantity})

        # Build order details dictionary
        order_details = {
            'route_name': route_number,
            'route': route_number,
            'pick_up_date': datetime.today(),  # Changed to store datetime object
            'pick_up_time': '11:00 AM',
            'total_cases': sum(item['Quantity'] for item in order_items),
            'items': order_items,
            'status': 'Pending',
            'transfer_id': '0000',
            'Type': "ShipTeo"
        }

        # Save the order in MongoDB
        db.orders.insert_one(order_details)
        return render(request, 'orders/order_confirmation.html', {'order': order_details})


@login_required
@user_is_warehouse_manager
def delete_order(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['orders']

    print(order_id)

    # Ensure the request method is POST to handle deletions
    if request.method == 'POST':
        order = collection.delete_one({'_id': ObjectId(order_id)})
        if order.deleted_count > 0:
            print(f"Order {order_id} deleted successfully.")
        else:
            print(f"Order {order_id} not found.")
        return HttpResponseRedirect(reverse('ops:order_view'))
    else:
        return HttpResponseRedirect(reverse('order_detail_view', args=[order_id]))


@login_required
@user_is_rsr
def rsr_orders_view(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['approvals']

    # Retrieve the route number from the logged-in user
    user_route_number = request.user.route_number

    # Getting filter parameters from the request
    date = request.GET.get('date')
    status = request.GET.get('status')
    route = request.GET.get('route', user_route_number)  # Default to user's route number if not provided
    page_number = request.GET.get('page', 1)  # Getting the page number, default is 1

    # Building the query based on the filters
    query = {"route": route}  # Start with the user's route number
    if date:
        start_of_day = datetime.fromisoformat(date)
        end_of_day = start_of_day + timedelta(days=1)
        query['pick_up_date'] = {"$gte": start_of_day, "$lt": end_of_day}
    if status:
        query['status'] = status

    # Sort orders by date descending to get the newest orders first
    orders = list(collection.find(query).sort('$natural', -1))

    for order in orders:
        order['order_id'] = str(order['_id'])

    # Apply pagination
    paginator = Paginator(orders, 15)  # Show 15 orders per page
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/rsr_order_view.html', {'page_obj': page_obj})


@login_required
@user_is_rsr
def rsr_order_detail_view(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['approvals']
    items_collection = db['mapped_items']

    order = collection.find_one({'_id': ObjectId(order_id)})
    if not order:
        raise Http404("Order not found")

    # Extract item numbers and fetch related data
    order_item_numbers = [item['ItemNumber'] for item in order.get('items', [])]
    items = list(items_collection.find({'ItemNumber': {'$nin': order_item_numbers}}))
    print(items)

    return render(request, 'orders/rsr_order_detail.html', {
        'order': order,
        'items': items,
    })


@login_required
@require_POST
def confirm_order_items(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['approvals']

    if not order_id:
        return render(request, "error_templates/forbidden.html", {'message': "Missing order ID."}, status=403)

    order = collection.find_one({'_id': ObjectId(order_id)})
    if order is None:
        return render(request, "error_templates/forbidden.html", {'message': "Order not found."}, status=403)

    if request.user.is_rsr():
        user_route_number = request.user.route_number
        if str(user_route_number) != str(order.get('route')):
            return render(request, "error_templates/forbidden.html",
                          {'message': "You do not have permission to confirm this order."}, status=403)
    elif not request.user.is_warehouse_worker():
        return render(request, "error_templates/forbidden.html",
                      {'message': "You do not have permission to confirm this order."}, status=403)

    # Process the form data to get confirmed items
    confirmed_items = request.POST.getlist('confirmed_items')

    # Debugging: Print the confirmed items to check their format
    print("Confirmed Items:", confirmed_items)

    # Fetch existing items from the order
    existing_items = order.get('items', [])

    # Update only the confirmed items in the existing items array
    for item_str in confirmed_items:
        try:
            # Replace single quotes with double quotes and False with false to make it valid JSON
            item_str = item_str.replace("'", '"').replace("False", "false")
            confirmed_item = json.loads(item_str)
        except json.JSONDecodeError as e:
            print(f"JSON decode error for item: {item_str} - {str(e)}")
            # Handle the error or skip this item
            continue

        for existing_item in existing_items:
            if existing_item['ItemNumber'] == confirmed_item['ItemNumber']:
                if request.user.is_rsr():
                    existing_item['RSR_Conf'] = True
                elif request.user.is_warehouse_worker():
                    existing_item['WHA_Conf'] = True

    # Debugging: Print the items array before updating the order
    print("Items to be updated:", existing_items)

    if request.user.is_rsr():
        status = "RSR Confirmed"
    elif request.user.is_warehouse_worker():
        if order.get("route") in ship_to_routes:
            status = "WHA Approved: Ready to Ship"
        else:
            status = "WHA Approved: Ready for Pick-up"

    # Update the order with the confirmed items and set status
    result = collection.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'items': existing_items, 'status': status}}
    )

    # Debugging: Check the result of the update operation
    print("Update result:", result.modified_count)

    # Redirect based on the user's role
    if request.user.is_rsr():
        return redirect('ops:rsr_orders_view')
    elif request.user.is_warehouse_worker():
        return redirect('ops:warehouse_approval_view')
    else:
        return render(request, "error_templates/forbidden.html",
                      {'message': "You do not have permission to confirm this order."}, status=403)

@csrf_exempt
def trigger_process_approval(request):
    response_data = approval_main()
    return JsonResponse(response_data, safe=False)


@login_required
@user_is_warehouse_worker
def order_picker(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    orders_collection = db['orders']
    items_collection = db['items']

    # Fetch the order by its ID
    order = orders_collection.find_one({'_id': ObjectId(order_id)})
    if not order:
        raise Http404("Order not found")

    # Extract item numbers as integers, checking if ItemNumber is in the item dict
    item_numbers = [int(item['ItemNumber']) for item in order.get('items', []) if 'ItemNumber' in item]
    print("Item numbers extracted for query:", item_numbers)

    # Fetch and process items
    items_data = items_collection.find({'ItemNumber': {'$in': item_numbers}})
    items_list = list(items_data)  # Make a list once
    item_details = {item['ItemNumber']: item for item in items_list}
    print("Item details dictionary:", item_details)

    order_items_data = []
    for item in order.get('items', []):
        item_num = int(item['ItemNumber'])  # Convert to int, ensuring consistent key usage
        item_info = item_details.get(item_num, {})  # Access using integer keys
        location = item_info.get('ItemLocation', 'Location not found')

        print(f"Processing item number: {item_num} - Found location: {location}")  # Debug output

        order_item = {
            'ItemNumber': item_num,
            'Description': item.get('ItemDescription', 'No description'),
            'Quantity': item.get('Quantity', 0),
            'Location': location
        }
        order_items_data.append(order_item)


    order_items_json = json.dumps(order_items_data)

    return render(request, 'orders/picker/base_picker.html', {
        'order_items': order_items_json
    })


@login_required
@user_is_warehouse_worker
def warehouse_approval_view(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['approvals']

    # Sort orders by date descending to get the newest orders first
    approvals = list(collection.find().sort('$natural', -1))
    page_number = request.GET.get('page', 1)  # Getting the page number, default is 1


    for order in approvals:
        order['order_id'] = str(order['_id'])

    # Apply pagination
    paginator = Paginator(approvals, 15)  # Show 15 orders per page
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/rsr_order_view.html', {'page_obj': page_obj})

@login_required
@user_is_warehouse_worker
def warehouse_approval_detail_view(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['approvals']
    items_collection = db['mapped_items']

    order = collection.find_one({'_id': ObjectId(order_id)})
    if not order:
        raise Http404("Order not found")

    # Extract item numbers and fetch related data
    order_item_numbers = [item['ItemNumber'] for item in order.get('items', [])]
    items = list(items_collection.find({'ItemNumber': {'$nin': order_item_numbers}}))


    return render(request, 'orders/rsr_order_detail.html', {
        'order': order,
        'available_items': items,
    })


@login_required
@user_is_warehouse_worker
def generate_approval_pdf(request, order_id):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db['approvals']
    oos_items_collection = db['oos_items']
    mapped_items_collection = db['mapped_items']


    order = collection.find_one({'_id': ObjectId(order_id)})

    # Fetch item ordering from the 'items' collection
    items_ordering = fetch_item_ordering(client, 'mydatabase', 'items')

    # Reorder the items in the order based on the 'Orderby' field
    ordered_items = reorder_items(order.get('items', []), items_ordering)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="order_{order_id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Initialize totals
    total_quantity = 0
    adjusted_total_quantity = 0

    for item in ordered_items:
        item_number = item.get('ItemNumber', '')
        try:
            quantity = int(item.get('Quantity', 0))
            total_quantity += quantity  # Add to total quantity

        except ValueError:
            # Log error or handle the case where the quantity is not an integer
            print(f"Warning: Invalid quantity '{item.get('Quantity')}' for item number {item_number}")

    p.setFont("Helvetica-Bold", 12)
    formatted_date = order.get('pick_up_date').strftime('%B %d, %Y')
    p.drawString(30, height - 30, f"Approval: {formatted_date}")


    p.setFont("Helvetica-Bold", 12)
    route_number = order.get('route', 'N/A')
    route_type = "Ship-to" if route_number in ship_to_routes else "Pick-up"
    p.drawString(30, height - 50, f"Route Number: {route_number} ({route_type}) ")
    p.setFont("Helvetica", 12)

    # Move total quantity and related information to the top right
    p.drawString(width - 300, height - 50, f"Total Quantity Ordered: {total_quantity}")


    # Starting position adjustment for item list
    y_position = height - 100

    p.setFont("Helvetica-Bold", 12)
    # Draw column headers, including a new column for 'Location'
    p.drawString(30, y_position, "Item Number")
    p.drawString(150, y_position, "Description")
    p.drawString(300, y_position, "Quantity")  # New location column
    p.drawString(375, y_position, "WHA")
    p.drawString(450, y_position, "RSR")


    # Revert to normal font for item details
    p.setFont("Helvetica", 12)

    # Adjust y_position for first item row
    y_position -= 20

    for item in ordered_items:
        quantity = item.get('Quantity', 0)

        # Skip items with no quantity or quantity set to 0
        if not quantity:
            continue

        # Draw a line to separate this item from the next
        p.line(30, y_position - 2, 580, y_position - 2)  # Adjust line length as needed

        item_number = item.get('ItemNumber', 'Unknown')
        description = item.get('ItemDescription', 'N/A')

        # Drawing item details (keep this part unchanged)
        p.drawString(30, y_position, str(item_number))
        p.drawString(150, y_position, description)
        p.drawString(315, y_position, str(quantity))


        # Draw the placeholder box for adjustment quantity, stock status, and checkbox
        p.rect(380, y_position - 2, 20, 15)
        p.rect(450, y_position - 2, 20, 15)

        # Move to the next line
        y_position -= 20

        # Check if we need to start a new page
        if y_position < 50:
            p.showPage()
            y_position = height - 50

    p.setTitle(route_number)
    p.showPage()
    p.save()
    return response


@login_required
@user_is_warehouse_worker
def physical_inventory_view(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    inventory_collection = db['inventory']

    # Fetch the most recent inventory document
    most_recent_inventory = inventory_collection.find_one(sort=[("timestamp", -1)])

    # Fetch item ordering from the 'items' collection
    items_ordering = fetch_item_ordering(client, 'mydatabase', 'items')

    # Reorder the items in the order based on the 'Orderby' field
    ordered_items = reorder_items(most_recent_inventory.get('items', []), items_ordering)

    if request.method == 'POST':
        if most_recent_inventory:
            items = ordered_items
            for key, value in request.POST.items():
                if key.startswith('quantity_'):
                    item_number = key.split('_')[1]
                    try:
                        physical_quantity = int(value)
                    except ValueError as e:
                        print(f"Invalid quantity value '{value}' for item_number '{item_number}': {e}")
                        continue  # Skip invalid quantities

                    # Find the specific item in the items array
                    for item in items:
                        if item['ItemNumber'] == item_number:
                            item['Physical'] = physical_quantity
                            break

            # Update the inventory document with the modified items array
            result = inventory_collection.update_one(
                {'_id': most_recent_inventory['_id']},
                {'$set': {'items': items}}
            )

            # Debug: Print the result of the update operation
            print(f"Update result for inventory_id '{most_recent_inventory['_id']}': {result.modified_count} document(s) updated.")

        return redirect('ops:inventory_comparison')  # Redirect to the same page after submission

    return render(request, 'inventory/physical_inventory.html', {
        'inventory_items': most_recent_inventory
    })


@login_required
@user_is_warehouse_worker
def builder_report_view(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    orders_collection = db['orders']

    # Determine the time range based on user selection
    time_range = request.GET.get('time_range', 'all')
    now = datetime.now()

    if time_range == 'day':
        start_date = now - timedelta(days=1)
    elif time_range == 'week':
        start_date = now - timedelta(weeks=1)
    elif time_range == 'month':
        start_date = now - timedelta(days=30)
    elif time_range == 'year':
        start_date = now - timedelta(days=365)
    else:
        start_date = None

    match_stage = {}
    if start_date:
        match_stage = {
            '$match': {
                'pick_up_date': {'$gte': start_date}
            }
        }

    # Aggregate the total cases by builder_name
    pipeline = [
        match_stage,
        {
            '$group': {
                '_id': '$builder_name',
                'total_cases': {'$sum': {'$toInt': '$total_cases'}},
                'orders_count': {'$sum': 1}
            }
        },
        {
            '$sort': {'total_cases': -1}
        }
    ]

    # Remove the match stage if it's empty (i.e., for 'all' time range)
    if not match_stage:
        pipeline.pop(0)

    builder_stats = list(orders_collection.aggregate(pipeline))

    # Calculate total cases across all builders
    total_cases = sum(stat['total_cases'] for stat in builder_stats)

    # Preprocess data to rename keys and calculate percentages
    processed_stats = []
    for stat in builder_stats:
        processed_stats.append({
            'builder_name': stat['_id'],
            'total_cases': stat['total_cases'],
            'orders_count': stat['orders_count'],
            'case_percentage': (stat['total_cases'] / total_cases) * 100 if total_cases > 0 else 0
        })

    return render(request, 'orders/builder_dashboard.html', {
        'builder_stats': processed_stats,
        'time_range': time_range,
    })


@login_required
@user_is_warehouse_worker
def inventory_comparison_view(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    inventory_collection = db['inventory']

    # Fetch the most recent inventory document
    most_recent_inventory = inventory_collection.find_one(sort=[("timestamp", -1)])

    # Process items to ensure Cases and Physical are integers
    items = most_recent_inventory.get('items', [])
    for item in items:
        item['Cases'] = int(item.get('Cases', 0))
        item['Physical'] = int(item.get('Physical', 0))

    # Calculate totals
    total_cases = sum(item['Cases'] for item in items)
    total_physical = sum(item['Physical'] for item in items)

    return render(request, 'inventory/inventory_comparison.html', {
        'inventory_items': items,
        'total_cases': total_cases,
        'total_physical': total_physical,
    })
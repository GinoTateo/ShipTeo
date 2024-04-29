import json
import logging
import os
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse, Http404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from pymongo import MongoClient
from reportlab.lib.pagesizes import letter
from operations.email_parse_util import main
from django.core.paginator import Paginator

# Constants
MONGO_URI = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"


# MONGO_URI = os.environ.setdefault('DB_URI', 'DB_URI')

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


# @login_required
# def orders_view(request):
#     filters = {
#         'date': request.GET.get('date'),
#         'status': request.GET.get('status'),
#         'route': request.GET.get('route')
#     }
#
#     client = MongoConnection.get_client()
#     db = client['mydatabase']
#     query = build_order_query(filters)
#     orders = list(db['orders'].find(query))
#
#     return render(request, 'orders/order_view.html', {'orders': orders})
#

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


# Further functions to be optimized similarly

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

    routes = {
        "RTC000003",
        "RTC000013",
        "RTC000018",
        "RTC00019",
        "RTC000089",
        "RTC000377",
        "RTC000379",
        "RTC000649",
        "RTC000700",
        "RTC000719",
        "RTC000004",
        "RTC000127",
        "RTC000433",
        "RTC000647",
        "RTC000720",
        "RTC000730",
        "RTC000731",
        "RTC000765",
        "RTC000783",
        "RTC000764",
        "RTC000002",
    }


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
    orders = list(collection.find(query).sort("pick_up_date", -1))

    for order in orders:
        order['order_id'] = str(order['_id'])

    # Apply pagination
    paginator = Paginator(orders, 15)  # Show 15 orders per page
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/order_view.html', {'page_obj': page_obj, 'routes': routes})


@login_required
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


@login_required
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
    for doc in mapped_items_collection.find({}):
        item_number = doc["ItemNumber"]
        item_to_location[item_number] = doc.get("Location", "N/A")
        item_to_type[item_number] = doc.get("Type", "N/A")  # Assuming 'Type' is the correct field name

    ship_to_routes = [
        "RTC000003", "RTC00013", "RTC000018", "RTC000019", "RTC000089",
        "RTC000377", "RTC000379", "RTC000649", "RTC000700", "RTC000719"
    ]

    order = collection.find_one({'_id': ObjectId(order_id)})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="order_{order_id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Initialize totals
    total_quantity = 0
    adjusted_total_quantity = 0

    # Calculate totals
    for item in order.get('items', []):
        try:
            quantity = int(item.get('Quantity', 0))
        except:
            quantity = 0;
        total_quantity += quantity
        if item.get('ItemNumber', '') not in oos_items:
            adjusted_total_quantity += quantity

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

    builder_name = order.get("builder_name")
    p.drawString(30, height - 70, f"Transfer ID: {tid} ")
    p.drawString(30, height - 90, f"Builder: {builder_name} ")

    # Move total quantity and related information to the top right
    p.drawString(width - 300, height - 50, f"Total Quantity Ordered: {total_quantity}")
    p.drawString(width - 300, height - 70, f"Total After OOS Adjustments: {adjusted_total_quantity}")
    p.drawString(width - 300, height - 90, "Build Adjustments:")
    p.rect(width - 180, height - 92, 50, 15)  # Adjustment input box
    p.drawString(width - 300, height - 110, "Build Count:")
    p.rect(width - 180, height - 112, 50, 15)  # Build count box
    p.drawString(width - 300, height - 130, "Scan Count:")
    p.rect(width - 180, height - 132, 50, 15)  # Scan count box

    # Starting position adjustment for item list
    y_position = height - 170

    p.setFont("Helvetica-Bold", 12)
    # Draw column headers, including a new column for 'Location'
    p.drawString(30, y_position, "Item Number")
    p.drawString(150, y_position, "Description")
    p.drawString(340, y_position, "Quantity")
    # Adjust existing columns to make room for the new 'Location' column
    p.drawString(420, y_position, "Type")  # New location column
    p.drawString(470, y_position, "Location")  # New location column
    p.drawString(530, y_position, "Stock Status")
    p.drawString(630, y_position, "Check")  # Checkboxes moved to the far right

    # Revert to normal font for item details
    p.setFont("Helvetica", 12)

    # Adjust y_position for first item row
    y_position -= 20

    for item in order.get('items', []):

        # Draw a line to separate this item from the next
        p.line(30, y_position - 2, 580, y_position - 2)  # Adjust line length as needed

        item_number = item.get('ItemNumber', 'Unknown')
        description = item.get('ItemDescription', 'N/A')
        quantity = item.get('Quantity', 0)
        stock_status = "IS" if item_number not in oos_items else "OOS"

        # Drawing item details (keep this part unchanged)
        p.drawString(30, y_position, str(item_number))
        p.drawString(150, y_position, description)
        p.drawString(350, y_position, str(quantity))

        # If the item is out of stock, cross out the quantity
        if stock_status == "OOS":
            # Calculate width of the quantity text for precise line drawing
            quantity_text_width = p.stringWidth(str(quantity), "Helvetica", 12)
            # Draw a line through the quantity text
            p.line(350, y_position + 4, 350 + quantity_text_width, y_position + 4)

        item_type = item_to_type.get(item_number, "N/A")  # Fetch the type
        p.drawString(420, y_position, item_type)

        # Draw the location next to each item
        item_location = item_to_location.get(item_number, "N/A")
        p.drawString(485, y_position, item_location)

        # Draw the placeholder box for adjustment quantity, stock status, and checkbox
        p.rect(370, y_position - 2, 30, 15)  # Placeholder box for adjustment quantity
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
            item_name = inventory_item.get('ItemName')
            item_data = items_collection.find_one({'ItemDescription': item_name})
            if item_data:
                # Calculate the 6-week average sales or usage
                six_week_avg = round(abs(item_data.get('AVG', 0)), 1)

                # Calculate current inventory cases
                current_cases = round(int(inventory_item.get('Cases', 0)), 1)

                # Calculate weeks of supply based on the six_week_avg; prevent division by zero
                weeks_of_supply = current_cases / -(six_week_avg) if six_week_avg else 'N/A'

                wos = round(abs(weeks_of_supply), 1)

                items_with_avg.append({
                    'ItemName': item_name,
                    'ItemNumber': int(item_data.get('ItemNumber')),
                    'Cases': current_cases,
                    'SixWeekAvg': six_week_avg,
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

    # Fetch and prepare items to be added
    items_to_add = []
    for item in selected_items_with_quantities:
        item_number = item.get('itemNumber')
        quantity = item.get('quantity')
        description = item.get('description')  # This is coming from the frontend.

        # Construct the item object according to the correct schema.
        item_to_add = {
            "ItemNumber": item_number,
            "ItemDescription": description,  # Ensure this matches your DB schema.
            "Quantity": int(quantity)
        }

        items_to_add.append(item_to_add)

    # Update the order document by appending the items with quantities
    update_result = db['orders'].update_one(
        {"_id": ObjectId(order_id)},
        {"$push": {"items": {"$each": items_to_add}}}
    )

    if not items_to_add:
        return JsonResponse({'error': 'No valid items found with the provided ItemNumbers'}, status=404)

    # Update the order document by appending the items with quantities
    update_result = db['orders'].update_one(
        {"_id": ObjectId(order_id)},
        {"$push": {"items": {"$each": items_to_add}}}
    )

    if update_result.modified_count == 0:
        return JsonResponse({'error': 'Order not found or no new items added'}, status=404)

    return JsonResponse({'success': True, 'message': 'Items successfully added to the order'})


@csrf_exempt
def trigger_process_order(request):
    response_data = main()
    return JsonResponse(response_data, safe=False)


def update_builder(request, order_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    try:
        client = MongoConnection.get_client()
        db = client['mydatabase']
        collection = db['orders']
        builder_name = request.POST.get('builder_name')

        if not builder_name:
            return JsonResponse({'status': 'error', 'message': 'Missing builder_name'}, status=400)

        # Perform the update
        result = collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': "Preparing", 'builder_name': builder_name}}
        )

        if result.modified_count == 1:
            return JsonResponse({'status': 'success', 'message': 'Builder updated successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Order not found or no update needed'}, status=404)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def create_order(request):
    client = MongoConnection.get_client()
    db = client['mydatabase']
    collection = db.mapped_items

    if request.method == 'GET':

        routes = {
            "RTC000003",
            "RTC000013",
            "RTC000018",
            "RTC00019",
            "RTC000089",
            "RTC000377",
            "RTC000379",
            "RTC000649",
            "RTC000700",
            "RTC000719",
            "RTC000004",
            "RTC000127",
            "RTC000433",
            "RTC000647",
            "RTC000720",
            "RTC000730",
            "RTC000731",
            "RTC000765",
            "RTC000783",
            "RTC000764",
            "RTC000002",
        }

        # Fetch items from MongoDB
        items_cursor = collection.find()
        items_by_type = {}
        for item in items_cursor:
            item_type = item.get('Type')
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)

        # Passing items grouped by type to the template
        return render(request, 'orders/create_order.html', {'items_by_type': items_by_type, 'routes': routes})

    elif request.method == 'POST':
        route_number = request.POST.get('routeNumber')
        # Process item quantities and descriptions
        order_items = []

        for key, value in request.POST.items():
            if key.startswith('quantity_') and value.isdigit() and int(value) > 0:
                item_number = key.split('_')[1]
                quantity = int(value)
                description = request.POST.get('description_' + item_number)
                order_items.append({'ItemNumber': item_number, 'ItemDescription': description, 'Quantity': quantity})

        # Build order details dictionary
        order_details = {
            'route_name': route_number,
            'route': route_number,
            'pick_up_date': datetime.today(),  # Changed to store datetime object
            'pick_up_time': '11:00 AM',
            'total_cases': sum(item['Quantity'] for item in order_items),
            'items': order_items,
            'status': 'Pending',
            'transfer_id': '0000'
        }

        # Save the order in MongoDB
        db.orders.insert_one(order_details)
        return render(request, 'orders/order_confirmation.html', {'order': order_details})


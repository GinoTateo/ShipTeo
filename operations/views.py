import json
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import DetailView, ListView
from pymongo import MongoClient
from reportlab.lib.pagesizes import letter
import rsr.models
from account.models import Account
from operations.email_parse_util import main
from operations.filters import ItemFilter
from operations.models import Item, Order, OrderItem, Warehouse, OutOfStockItem


# Assuming this function is correctly getting MongoDB client and fetching data
def get_mongodb_client():
    # Return a MongoClient instance connected to your database
    pass


class ProductView(DetailView):
    model = Item
    template_name = "order_page.html"


@login_required
def OrderSummaryView(request):
    # current_user = request.user
    # user = get_object_or_404(User, username=current_user)
    user = Account.objects.get(username=request.user)
    order = Order.objects.filter(user=user)
    context = {
        'object': order
    }

    return render(request, 'order_summary.html', context)


@login_required
def OrderSummaryViewWithID(request, order_id):
    # current_user = request.user
    # user = get_object_or_404(User, username=current_user)
    order = Order.objects.filter(id=order_id)
    context = {
        'object': order
    }

    return render(request, 'order_summary.html', context)


@login_required
def add_to_cart(request, pk, quantity):
    item = get_object_or_404(Item, pk=pk)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs[0]

        if order.items.filter(item__pk=item.pk).exists():
            order_item.quantity += quantity
            order_item.save()
            messages.info(request, "Added quantity Item")
            return redirect("order-form")
        else:
            order.items.add(order_item)
            order_item.quantity += quantity - 1
            order_item.save()
            messages.info(request, "Item added to your cart")
            return redirect("order-form")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        order_item.quantity += quantity - 1
        order_item.save()
        messages.info(request, "Item added to your cart")
        return redirect("order-form")


@login_required
def add_item_order(request, *args, **kwargs):
    user_id = request.user.id

    user = Account.objects.get(id=user_id)
    payload = {}

    item_id = request.POST.get("item_id")
    quantity_str = request.POST.get("quantity")
    try:
        quantity = int(quantity_str)
    except ValueError:
        quantity = quantity_str

    item = Item.objects.get(pk=item_id)
    if item:
        order_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False
        )
        order = Order.objects.filter(user=request.user, ordered=False)
        if order.exists():
            order = order[0]

            if order.items.filter(item__pk=item.pk).exists():
                order_item.quantity += quantity
                order_item.save()
                payload['response'] = "Item added to your cart"
            else:
                order.items.add(order_item)
                order_item.quantity += quantity - 1
                order_item.save()
                payload['response'] = "Item added to your cart"
        else:
            ordered_date = timezone.now()
            order = Order.objects.create(user=request.user, ordered_date=ordered_date)
            order.item.add(item)
            order_item.quantity += quantity - 1
            order_item.save()
            payload['response'] = "Item added to your cart"
    else:
        payload['response'] = "Could not find request"
    return redirect("ops:order-form")


@login_required
def remove_from_cart(request, pk):
    item = get_object_or_404(Item, pk=pk)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__pk=item.pk).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order_item.delete()
            messages.info(request, "Item \"" + order_item.item.item_name + "\" remove from order")
            return redirect("order-summary")
        else:
            messages.info(request, "This Item is not in your order")
            return redirect("product", pk=pk)
    else:
        # add message doesnt have order
        messages.info(request, "You do not have an Order")
        return redirect("product", pk=pk)


@login_required
def reduce_quantity_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__pk=item.pk).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order_item.delete()
            messages.info(request, "Item quantity was updated")
            return redirect("order-summary")
        else:
            messages.info(request, "This Item not in your cart")
            return redirect("order-summary")
    else:
        # add message doesnt have order
        messages.info(request, "You do not have an Order")
        return redirect("order-summary")


class orderForm(ListView):
    model = Item
    template_name = "order_form2.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = ItemFilter(self.request.GET, queryset=self.get_queryset())
        return context


@login_required
def ItemData(request, item_id):
    item = Item.objects.get(id=item_id)

    return render(request, "item_data.html", {'item': item})


# def WarehouseDateItemView(request, warehouse_id):
#     warehouse = Warehouse.objects.get(id=warehouse_id)
#     inventory = Inventory.objects.filter(warehouse=warehouse).latest('date')
#     inv_items = inventory.items.all()
#     items = Item.objects.filter(Q(item_type='G') | Q(item_type='W'))
#
#     return render(request, "warehouse_dates.html", {'items': inv_items, 'warehouse': warehouse})


# @login_required
# def WarehouseDateItemForm(request, item_id):
#     item = Item.objects.get(id=item_id)
#     items = Item.objects.filter(Q(item_type='G') | Q(item_type='W'))
#     last_item = items.last()
#     form = WarehouseForm()
#     if item.pk is last_item.pk:
#         return render(request, "warehouse_dates.html", {'items': items})
#     return render(request, "item_date_form.html", {'item': item, 'form': form})


# @login_required
# def WarehouseDateItemInput(request, item_id, inventory_id):
#     inventory = Inventory.objects.get(id=inventory_id)
#     if request.method == 'POST':
#         # create a form instance and populate it with data from the request:
#         form = WarehouseForm(request.POST)
#         # check whether it's valid:
#         if form.is_valid():
#             date = form.cleaned_data['Date']
#             amount = form.cleaned_data['Amount']
#
#             item = Item.objects.get(id=item_id)
#
#             add_item, created = InventoryItem.objects.get_or_create(
#                 item=item,
#                 total_quantity=amount,
#                 item_date=date,
#             )
#
#             inventory.items.add(add_item)
#             inventory.save()
#
#             items = Item.objects.filter(Q(item_type='G') | Q(item_type='W'))
#             last_item = items.last()
#             item = Item.objects.get(id=item_id + 1)
#             if item.pk is last_item.pk:
#                 return render(request, "warehouse_dates.html", {'items': items})
#             return render(request, "item_date_form.html", {'form': form, 'item': item, 'inventory': inventory})
#
#     # if a GET (or any other method) we'll create a blank form
#     else:
#         form = WarehouseForm()
#
#     return render(request, 'item_date_form.html', {'form': form, 'inventory': inventory})


# @login_required
# def WarehouseDateForm(request, warehouse_id):
#     items = Item.objects.all()
#
#     warehouse = Warehouse.objects.get(id=warehouse_id)
#     inventory = Inventory.objects.filter(warehouse=warehouse).latest('date')
#     inv_items = inventory.items.all()
#
#     for item in inv_items:
#         item.item_date = None
#         item.save()
#
#     item = items.first()
#     form = WarehouseForm()
#
#     return render(request, 'item_date_form.html', {'form': form, 'item': item, 'inventory': inventory})


@login_required
# def WarehouseDateFormSkip(request, item_id, inventory_id):
#     inventory = Inventory.objects.get(id=inventory_id)
#     item = Item.objects.get(id=item_id + 1)
#     form = WarehouseForm()
#
#     items = Item.objects.filter(Q(item_type='G') | Q(item_type='W'))
#     last_item = items.last()
#
#     if item.pk is last_item.pk:
#         return render(request, "warehouse_dates.html", {'items': items, 'inventory': inventory})
#
#     return render(request, "item_date_form.html", {'form': form, 'item': item, 'inventory': inventory})

def WarehouseList(request):
    warehouses = Warehouse.objects.all()

    return render(request, 'warehouse_list.html', {'warehouses': warehouses})


@login_required
def warehouse_dashboard(request, warehouse_id):
    # Assuming you have a Django model Warehouse
    try:
        warehouse = Warehouse.objects.get(id=warehouse_id)
    except Warehouse.DoesNotExist:
        raise Http404("Warehouse not found")

    routes = warehouse.routes.all()

    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['mydatabase']

    # Fetch inventory stats
    inventory_stats = db['inventory_stats'].find_one(sort=[("_id", -1)])  # Get the most recent stats document
    if not inventory_stats:
        # Handle the case where no stats are found, maybe set default values or return an error
        print("No inventory stats found")
        inventory_status = 0
        total_out_of_stocks = 0
    else:
        # Assuming the inventory_stats document contains 'total_inventory' and 'num_oos_items' fields
        inventory_status = inventory_stats.get('total_inventory', 0)
        total_out_of_stocks = inventory_stats.get('num_oos_items', 0)

    # Calculate the number of pending orders
    pending_orders_count = db['orders'].count_documents({"status": "Pending"})

    client.close()

    return render(request, 'warehouse_dashboard.html', {
        'warehouse': warehouse,
        'routes': routes,
        'total_out_of_stocks': total_out_of_stocks,
        'inventory_status': inventory_status,
        'pending_orders': pending_orders_count
    })


import io
from django.http import FileResponse
from reportlab.pdfgen import canvas


def PalletPages(request, route_id):
    if request.method == 'POST':
        RT = rsr.models.Route.objects.get(id=route_id)
        RTnum = RT.number

        if request.method == 'POST':
            # Instanciate the form with posted data

            pages = int(request.POST.get('pallets'))
            # Create a file-like buffer to receive PDF data.
            buffer = io.BytesIO()

            # Create the PDF object, using the buffer as its "file."
            p = canvas.Canvas(buffer)
            p.setTitle(f"RT{RTnum}_pallet_pages")
            # Draw things on the PDF. Here's where the PDF generation happens.
            # See the ReportLab documentation for the full list of functionality.
            for page in range(pages):
                p.setFont("Helvetica", 100)
                p.drawString(150, 750, "RT " + RTnum.__str__(), )
                p.drawString(150, 150, f'{page + 1} of {pages}')
                p.showPage()
            # Close the PDF object cleanly, and we're done.

            p.save()

            # FileResponse sets the Content-Disposition header so that browsers
            # present the option to save the file.
            buffer.seek(0)
            return FileResponse(buffer, as_attachment=True, filename=f'RT{RTnum}_pallet_pages.pdf')
        else:  # The form is invalid return a json response
            return JsonResponse({"Error": "Form is invalid"}, status=400)
    else:
        return render(request, 'warehouse_print.html')
    # return render(request, 'pallet-pages.html', {'RTnum': RTnum, 'pages': pages})


def PrintPalletPages(request, warehouse_id):
    warehouse = Warehouse.objects.get(id=warehouse_id)
    routes = warehouse.routes.all()
    return render(request, 'warehouse_print.html', {'warehouse': warehouse, 'routes': routes})


@login_required
def WarehousePhysicalInventory(request, item_id):
    return render(request, 'item_date_form.html')


@login_required
def WarehouseManagerDetail(request, warehouse_id):
    warehouse = Warehouse.objects.get(id=warehouse_id)
    routes = warehouse.routes.all()
    user = request.user
    orders = Order.objects.all()

    return render(request, 'warehouse_manager_detail.html',
                  {'warehouse': warehouse, 'routes': routes, 'user': user, 'orders': orders})


@login_required
def WarehouseManagerOrderStatusUpdate(request, order_id):
    order = Order.objects.get(id=order_id)

    if request.method == 'POST':
        # Access form input data
        order_status = request.POST.get('orderStatus')
        quantity = request.POST.get('quantity')
        order.status = order_status
        order.save()

    return WarehouseManagerOrderStatusDetail(request, order_id)


@login_required
def WarehouseManagerOrderStatusView(request):
    orders = Order.objects.all()

    return render(request, 'OrderStatusView.html', {'orders': orders})


@login_required
def WarehouseManagerOrderStatusDetail(request, order_id):
    order = Order.objects.get(id=order_id)

    return render(request, 'OrderStatusDetail.html', {'order': order})


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

    routes = {
        "RTC000003",
        "RTC000013",
        "RTC000018",
        "RTC000019",
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

    orders = list(collection.find(query))

    # Renaming '_id' field to 'order_id' for each order
    for order in orders:
        order['order_id'] = str(order['_id'])  # Convert ObjectId to string
        del order['_id']

    orders.reverse()

    # You can now pass these orders to your template or process them further
    return render(request, 'orders/order_view.html', {'orders': orders, 'routes': routes})


@login_required
def edit_order(request, order_id):
    try:
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        collection = db['orders']

        # Update the order's status to "preparing"
        result = collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': "Preparing"}}
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
    return redirect("ops:edit_order", order_id)



def prepare_order(request, order_id):
    try:
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        collection = db['orders']

        if request.method == 'POST':
            # Assuming builder_name is sent via POST request
            builder_name = request.POST.get('builder_name')

            start_time = datetime.now()

            # Update the order's builder and status
            result = collection.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'status': "Preparing", 'builder_name': builder_name, 'start_time': start_time}}
            )

            if result.matched_count == 0:
                print("No order found with the specified ID.")
                client.close()
                return HttpResponse("Order not found", status=404)

            # Redirect to PDF or detail view after updating
            client.close()
            return redirect('../pdf', order_id=order_id)


    except Exception as e:
        print(f"An error occurred: {e}")
        client.close()
        return HttpResponse("Error connecting to database", status=500)


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


@login_required
def order_detail_view(request, order_id):
    # Directly create a MongoDB client instance
    edit_mode = 'edit' in request.GET and request.GET['edit'] == 'true'

    try:
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        collection = db['orders']
        items_collection = db['mapped_items']
        # Fetch the order document
        order = collection.find_one({'_id': ObjectId(order_id)})

        # Extract item numbers from the order items
        order_item_numbers = [item['ItemNumber'] for item in order.get('items', [])]

        # Fetch available items that are not in the order
        available_items = list(items_collection.find({'ItemNumber': {'$nin': order_item_numbers}}))


    except Exception as e:
        print(f"An error occurred: {e}")
        return HttpResponse("Error connecting to database", status=500)

    # Fetch Out of Stock (OOS) items
    OOS_items = OutOfStockItem.objects.all().values_list('item_number', flat=True)

    if request.method == 'POST' and edit_mode:
        # Assuming each item in the form is prefixed with 'item_', followed by the item's index or ID
        # and the field names are appended with '_description', '_quantity', and '_inStock'
        for key, value in request.POST.items():
            if key.startswith('items_') and key.endswith('_quantity'):
                # Extract the item ID/index from the key
                item_id = key.split('_')[1]
                # Update the quantity for the item
                new_quantity = request.POST.get(f'items_{item_id}_quantity')
                in_stock = request.POST.get(f'items_{item_id}_inStock') == 'true'

                # Find the item in the 'order' document and update its quantity and inStock status
                # Assuming 'items' is a list of items within the 'order' document
                for item in order.get('items', []):
                    if str(item.get('ItemNumber')) == item_id:
                        item['Quantity'] = int(new_quantity)
                        item['InStock'] = in_stock
                        break

        # Save the updated order back to MongoDB
        collection.update_one({'_id': ObjectId(order_id)}, {'$set': {'items': order['items']}})

        # Redirect to avoid resubmitting the form on refresh
        return HttpResponseRedirect(reverse('ops:detail_order_view', args=[order_id]))

    client.close()
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'OOS_items': OOS_items,
        'available_items': available_items,
    })


@login_required
def generate_order_pdf(request, order_id):
    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
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
    client.close()

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


def inventory_view(request, warehouse_id):
    try:
        # MongoDB connection
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']

        # Fetch the latest inventory
        inventory_collection = db['inventory']
        latest_inventory = inventory_collection.find_one(sort=[("_id", -1)])

        inventory_items = latest_inventory['items'] if latest_inventory else []

        # Fetch Out-of-Stock items directly from oos_items collection
        oos_items_collection = db['oos_items']
        OOS_items = list(oos_items_collection.find({}, {'ItemNumber': 1, 'ItemDescription': 1}))

    except Exception as e:
        print(f"An error occurred: {e}")
        return HttpResponse("Error connecting to database", status=500)

    # Render the inventory list template, passing both inventory items and OOS items
    return render(request, 'inventory/inventory_list.html', {
        'inventory_items': inventory_items,
        'OOS_items': OOS_items,
    })


def get_item_description(item_number, items_list):
    # Attempt to find an item description from a list of items
    for item in items_list:
        if item['ItemNumber'] == item_number:
            return item.get('ItemDescription', 'N/A')
    return 'Description Unavailable'


def verify_order(request, order_id):
    try:
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        orders_collection = db['orders']
        transfers_collection = db['transfers']
        oos_items_collection = db['oos_items']

        # Fetching OOS item numbers
        oos_items_docs = list(oos_items_collection.find({}, {'ItemNumber': 1}))
        oos_item_numbers = {doc['ItemNumber'] for doc in oos_items_docs}

        # Fetch the order and corresponding transfer
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        matching_transfer = transfers_collection.find_one(
            {"transfer_id": {"$regex": ".*" + str(order['_id'])[-4:] + "$"}})

        if not order or not matching_transfer:
            return render(request, 'error_page.html', {'error': "Transfer not found in database."})

        order_items = order.get('items', [])
        transfer_items = matching_transfer.get('items', [])

        # Create dictionaries for efficient lookups
        order_item_dict = {item['ItemNumber']: item for item in order_items}
        transfer_item_dict = {item['ItemNumber']: item for item in transfer_items}

        # Preparing data for the template
        items_with_variances = []

        # Adustments
        adjustments = 0;

        # Checking items that were both ordered and transferred, including quantity variances
        for item_number, order_item in order_item_dict.items():
            order_quantity = int(order_item['Quantity'])
            transfer_item = transfer_item_dict.get(item_number)
            if transfer_item:
                transfer_quantity = int(transfer_item['Quantity'])
                variance = transfer_quantity - order_quantity
                adjustments = variance + adjustments
                is_oos = item_number in oos_item_numbers
                items_with_variances.append({
                    'ItemNumber': item_number,
                    'ItemDescription': order_item.get('ItemDescription', 'N/A'),
                    'OrderQuantity': order_quantity,
                    'TransferQuantity': transfer_quantity,
                    'Variance': variance,
                    'IsOOS': is_oos,
                })
                # Remove item from transfer_item_dict to mark it as processed
                del transfer_item_dict[item_number]
            else:
                # Ordered but not transferred
                items_with_variances.append({
                    'ItemNumber': item_number,
                    'ItemDescription': order_item.get('ItemDescription', 'N/A'),
                    'OrderQuantity': order_quantity,
                    'TransferQuantity': 0,
                    'Variance': order_quantity,
                    'IsOOS': item_number in oos_item_numbers,
                })

        # Checking items that were transferred but not ordered
        for item_number, transfer_item in transfer_item_dict.items():
            transfer_quantity = int(transfer_item['Quantity'])
            item_description = get_item_description(item_number, order_items + transfer_items)
            adjustments = variance + transfer_quantity
            items_with_variances.append({
                'ItemNumber': item_number,
                'ItemDescription': item_description,
                'OrderQuantity': 0,
                'TransferQuantity': transfer_quantity,
                'Variance': transfer_quantity,
                'IsOOS': False,  # Assuming these cannot be OOS as they were transferred
                'Unordered': True
            })

        return render(request, 'orders/order_verification.html', {
            'order': order,
            'matching_transfer': matching_transfer,
            'order_items': items_with_variances,
            'adjustments': adjustments,
        })
    except Exception as e:
        return render(request, 'error_page.html', {'error': str(e)})


@require_http_methods(["GET", "POST"])
def place_order_view(request):
    if request.method == 'POST':
        try:
            # Assuming JSON data is sent
            data = json.loads(request.body)
            date = data.get('date')
            route = data.get('route')
            orders = data.get('orders')  # This is expected to be a list of items
            status = data.get('status', 'Received')  # Default status
            transfer_id = data.get('transfer_id')

            # MongoDB connection setup
            uri = "your_mongodb_connection_uri"
            client = MongoClient(uri)
            db = client['mydatabase']
            orders_collection = db['orders2']

            # Create and save the entire order
            order = {
                'date': date,
                'route': route,
                'orders': orders,  # Directly saving the array of items
                'status': status,
                'transfer_id': transfer_id,
            }
            order_id = orders_collection.insert_one(order).inserted_id

            client.close()

            # Return a success response with the order ID
            return JsonResponse({'message': 'Order placed successfully', 'order_id': str(order_id)}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # For GET requests, show the form (assuming you have a template for it)
    return render(request, 'orders/place_order.html')


def list_items_view(request, warehouse_id):
    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['mydatabase']
    items_collection = db['items']

    items_cursor = items_collection.find({})
    items_by_type = {}
    for item in items_cursor:
        # Replace spaces in keys
        processed_item = {k.replace(' ', '_'): v for k, v in item.items()}

        item_type = processed_item.get('Item_Type', 'Other')  # Adjusted key
        if item_type not in items_by_type:
            items_by_type[item_type] = []
        items_by_type[item_type].append(processed_item)

    client.close()
    return render(request, 'list_items.html', {'items_by_type': items_by_type})


def review_order_view(request):
    if request.method == 'POST':
        items = []
        for key, value in request.POST.items():
            if key.startswith('item_number_'):
                try:
                    *_, type_index, item_index = key.split('_')
                    item_number = value
                    item_description_key = f'item_description_{type_index}_{item_index}'
                    quantity_key = f'quantity_{type_index}_{item_index}'
                    item_description = request.POST.get(item_description_key, '')
                    quantity = request.POST.get(quantity_key, 0)
                    transformed_items = []
                    for item in items:
                        transformed_item = {
                            'Item_Number': item.get('Item Number'),
                            'Item_Description': item.get('Item Description', 'Default Description'),
                            'Quantity': item.get('Quantity')
                        }
                        transformed_items.append(transformed_item)
                except ValueError as e:
                    print(f"Error processing {key}: {e}")
                    # Handle the error appropriately, e.g., log it, send a user-friendly message, etc.
                    return HttpResponse("There was an error processing your request.", status=400)

        # Assuming you're using Django's session framework to temporarily store the order
        request.session['order_review'] = items

        # Proceed to render the review order template or handle as necessary
        return render(request, 'orders/review_order.html', {'items': items})

    # Redirect or handle get requests differently
    return redirect('list_items')  # Adjust as necessary


# Ensure MongoDB setup and submission logic is correctly implemented
def submit_order(request):
    if request.method == 'POST':
        # Assuming order details are stored in the session during review
        order_items = request.session.get('order_review', [])
        if not order_items:
            return JsonResponse({'error': 'Session expired or order details missing.'}, status=400)

        # MongoDB connection and order submission logic
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        orders_collection = db['orders2']

        # Create and save the order
        order = {
            'orders': order_items,
            'status': 'Received',
            # Add any other necessary order details here
        }
        order_id = orders_collection.insert_one(order).inserted_id

        # Clear the session data for order review
        del request.session['order_review']

        client.close()

        # Redirect to a confirmation page or return a success response
        return JsonResponse({'message': 'Order submitted successfully', 'order_id': str(order_id)}, status=201)

    else:
        return redirect('list_items')


def inventory_with_6week_avg(request, warehouse_id):
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


def inventory_visualization_view(request, warehouse_id):
    selected_week = request.GET.get('week', 'Week 1')  # Default to 'Week 1' if not specified

    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
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

    client.close()

    return render(request, 'inventory/inventory_plot.html', {'plot_div': plot_div, 'selected_week': selected_week})


def weekly_trend_view(request, warehouse_id, item_type):
    selected_week = request.GET.get('week', 'Week 1')  # Default to 'Week 1' if not specified

    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
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
    client.close()
    return render(request, 'inventory/inventory_plot.html', {'plot_div': plot_div, 'item_type': item_type})


def comparison_across_weeks_view(request, warehouse_id):
    selected_week = request.GET.get('week', 'Week 1')  # Default to 'Week 1' if not specified

    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
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
    client.close()
    return render(request, 'inventory/inventory_plot.html', {'plot_div': plot_div})


def update_order(request, order_id):
    if request.method == 'POST':
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
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
                client.close()
                return HttpResponse("Order not found.", status=404)

        client.close()
        # Redirect to the order detail page or another appropriate page after the update
        return redirect('ops:detail_order_view', order_id=order_id)
    else:
        # Handle GET request or other methods if necessary
        return HttpResponse("Method not allowed", status=405)


@require_POST
@csrf_exempt
def add_items(request, order_id):
    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
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
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['mydatabase']
        collection = db['orders']
        builder_name = request.POST.get('builder_name')

        builder_name = request.POST.get('builder_name')

        if not builder_name:
            return JsonResponse({'error': 'Missing builder_name'}, status=400)

        # Perform the update
        result = collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': "Preparing", 'builder_name': builder_name}}
        )

        if result.modified_count == 1:
            return JsonResponse({'status': 'success', 'message': 'Builder updated successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Order not found or builder already set'}, status=404)

    except Exception as e:
        # Log the error here
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def test_redis(request):
    # Test writing to the cache
    cache.set('hello', 'world', timeout=30)
    # Test reading from cache
    if cache.get('hello') == 'world':
        return HttpResponse("Redis is working!")
    else:
        return HttpResponse("Redis is not working.", status=500)
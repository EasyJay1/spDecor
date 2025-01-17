import os
import zipfile
from io import BytesIO
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from allauth.account.views import SignupView
from .forms import CustomSignupForm
from django.contrib.admin.views.decorators import staff_member_required
from .forms import TicketCodeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from .models import Event, Ticket, Category, Booking
from .forms import BookingForm
from .utils import is_payment_required
from django.db import transaction
from django.shortcuts import render
from django.core.mail import send_mail
from .forms import ContactForm
from django.shortcuts import render
from django.core.mail import send_mail
from .forms import ContactForm
from .models import Event, Booking
from django.db.models import Sum
from PIL import Image, ImageDraw, ImageFont

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Event, Category, Booking, Ticket
from .forms import BookingForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from django.conf import settings
from .models import Booking, Event, Category


def save_bookings(request):
    bookings_to_save_data = request.session.get('bookings_to_save', [])
    event_slug = request.session.get('event_slug')

    if not bookings_to_save_data:
        messages.error(request, 'No bookings to save.')
        return

    event = get_object_or_404(Event, slug=event_slug)

    for booking_data in bookings_to_save_data:
        category = get_object_or_404(Category, id=booking_data['category_id'])
        booking = Booking(
            user=request.user,
            event=event,
            category=category,
            number_of_tickets=booking_data['number_of_tickets']
        )
        booking.save()

    request.session.pop('bookings_to_save', None)
    request.session.pop('total_cost', None)
    request.session.pop('event_slug', None)
    messages.success(request, 'Ticket(s) booked successfully!')

@csrf_exempt
def flutterwave_webhook(request):
    if request.method == 'POST':
        # Parse the JSON request body
        webhook_data = json.loads(request.body)

        # Process the webhook data
        event = webhook_data.get('event')
        if event == 'charge.completed':
            data = webhook_data.get('data', {})
            tx_ref = data.get('tx_ref')
            status = data.get('status')
            transaction_id = data.get('id')

            if status == 'successful':
                # Payment is successful, update your booking status accordingly
                payment_verified = verify_payment(transaction_id)
                if payment_verified:
                    save_bookings(tx_ref)
                    return JsonResponse({'status': 'success'}, status=200)
                else:
                    return JsonResponse({'status': 'error', 'message': 'Payment verification failed'}, status=400)

        return JsonResponse({'status': 'error', 'message': 'Unhandled event type'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def verify_payment(transaction_id):
    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()

        if response_data['status'] == 'success' and response_data['data']['status'] == 'successful':
            return True
        else:
            return False
    except requests.RequestException as e:
        print(f"Error verifying payment: {e}")
        return False

def payment_status(request):
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')
    event_slug = request.session.get('event_slug')

    if status == 'successful':
        payment_verified = verify_payment(transaction_id)
        if payment_verified:
            save_bookings(request)
            messages.success(request, 'Booking and payment successful!')
            return redirect('booking_success')
        else:
            messages.error(request, 'Payment verification failed. Please try again.')
            return redirect('book_event', event_slug=event_slug)
    elif status == 'cancelled':
        messages.info(request, 'Payment was cancelled.')
        return redirect('book_event', event_slug=event_slug)
    else:
        messages.error(request, 'Payment failed. Please try again.')
        return redirect('book_event', event_slug=event_slug)

@login_required
def continue_booking(request):
    booking_data = request.session.pop('booking_data', None)
    event_slug = request.session.pop('event_slug', None)
    if not booking_data or not event_slug:
        return redirect('index')
    event = get_object_or_404(Event, slug=event_slug)
    categories = Category.objects.all()
    bookings_to_save = []
    total_cost = Decimal(0)
    all_valid = True
    for category in categories:
        number_of_tickets = booking_data.get(f'number_of_tickets{category.id}', '0')
        if number_of_tickets == '':
            number_of_tickets = '0'
        try:
            number_of_tickets = int(number_of_tickets)
        except ValueError:
            number_of_tickets = 0
        if number_of_tickets < 1:
            continue
        form_data = {
            'category': category.id,
            'number_of_tickets': number_of_tickets
        }
        booking_form = BookingForm(form_data)
        if booking_form.is_valid():
            booking = booking_form.save(commit=False)
            booking.user = request.user
            booking.event = event
            bookings_to_save.append(booking)
            total_cost += Decimal(booking.number_of_tickets) * category.price
        else:
            all_valid = False
            messages.error(request, f'Error in booking for category {category.grade}.')
    if all_valid:
        if is_payment_required(total_cost):
            request.session['bookings_to_save'] = [
                {
                    'category_id': booking.category.id,
                    'number_of_tickets': booking.number_of_tickets
                } for booking in bookings_to_save
            ]
            return render(request, 'blogapp/payment.html', {
                'total_cost': float(total_cost),
                'customer_email': request.user.email,
                'customer_name': request.user.get_full_name,
                'tx_ref': f"txref-{event.id}-{request.user.id}",
            })
        else:
            for booking in bookings_to_save:
                booking.save()
            messages.success(request, 'Booking successful!')
            return redirect('booking_success')
    else:
        messages.error(request, 'Form data is not valid.')
        return redirect('index')

@transaction.atomic
def book_event(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    categories = Category.objects.all()
    total_tickets = Ticket.objects.filter(booking__event=event).count()

    if request.method == 'POST':
        if request.user.is_authenticated:
            bookings_to_save = []
            total_cost = Decimal(0)
            all_valid = True

            for category in categories:
                number_of_tickets = request.POST.get(f'number_of_tickets{category.id}', '0')
                if number_of_tickets == '':
                    number_of_tickets = '0'
                number_of_tickets = int(number_of_tickets)
                if number_of_tickets < 1:
                    continue
                form_data = {
                    'category': category.id,
                    'number_of_tickets': number_of_tickets
                }
                booking_form = BookingForm(form_data)
                if booking_form.is_valid():
                    booking = booking_form.save(commit=False)
                    booking.user = request.user
                    booking.event = event
                    bookings_to_save.append(booking)
                    total_cost += Decimal(booking.number_of_tickets) * category.price
                else:
                    all_valid = False
                    messages.error(request, f'Error in booking for category {category.grade}.')
                    # Optionally break here to stop processing other categories on error

            if all_valid:
                if is_payment_required(total_cost):
                    request.session['bookings_to_save'] = [
                        {
                            'category_id': booking.category.id,
                            'number_of_tickets': booking.number_of_tickets
                        } for booking in bookings_to_save
                    ]
                    request.session['total_cost'] = float(total_cost)
                    request.session['event_slug'] = event_slug
                    return render(request, 'blogapp/payment.html', {
                        'total_cost': float(total_cost),
                        'customer_email': request.user.email,
                        'customer_name': request.user.get_full_name,
                        'tx_ref': f"txref-{event.id}-{request.user.id}",
                    })
                else:
                    for booking in bookings_to_save:
                        booking.save()
                    messages.success(request, 'Booking successful!')
                    return redirect('booking_success')
            else:
                messages.error(request, 'Form data is not valid.')
        else:
            booking_data = request.POST.dict()
            request.session['booking_data'] = booking_data
            request.session['event_slug'] = event_slug
            messages.info(request, 'Please log in to continue booking.')
            return redirect('account_login')
    return render(request, 'blogapp/discover.html', {'event': event, 'categories': categories, 'total_tickets': total_tickets})


@staff_member_required
def deactivate_ticket(request):
    if request.method == 'POST':
        form = TicketCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                ticket = Ticket.objects.get(unique_code=code)
                if not ticket.active_ticket:
                    messages.error(request, f'Ticket already used at {ticket.used_date}.')
                else:
                    ticket.deactivate()
                    messages.success(request, 'Ticket scratched successfully.')
            except Ticket.DoesNotExist:
                messages.error(request, 'Invalid ticket code.')
    else:
        form = TicketCodeForm()
    return render(request, 'blogapp/ticket_scanner.html', {'form': form})

@staff_member_required
def qr_code_scanner(request):
    return render(request, 'blogapp/scanner.html')













class CustomSignupView(SignupView):
    form_class = CustomSignupForm

    def form_valid(self, form):
        response = super().form_valid(form)
        self.send_confirmation_email(form.instance)
        return response

    def send_confirmation_email(self, user):
        from allauth.account.utils import send_email_confirmation
        send_email_confirmation(self.request, user)



@login_required
def download_tickets(request):
    user_tickets = Ticket.objects.filter(booking__user=request.user)

    # Create a zip file in memory
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for ticket in user_tickets:
            if ticket.qr_code:
                # Add the QR code image to the zip file
                filename = f'{ticket.unique_code}.png'
                qr_code_data = ticket.qr_code.read()
                zip_file.writestr(filename, qr_code_data)

    buffer.seek(0)
    # Create the HttpResponse object with the appropriate headers
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=tickets.zip'

    return response

def index(request):
    events = Event.objects.filter(active_event=True)
    for event in events:
        total_tickets = Booking.objects.filter(event=event).aggregate(Sum('number_of_tickets'))['number_of_tickets__sum']
        event.total_tickets_sold = total_tickets if total_tickets is not None else 0

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']

            # Send an email to the site admin
            send_mail(
                'Contact Us Form Submission',
                f'You have a new subscriber: {email}  \n with phone number  {phone} request a chat',
                'jay@technlogic.service',  # Replace with your email
                ['jay@technlogic.service'],  # Replace with your email
            )

            # Send a confirmation email to the sender
            send_mail(
                'Thank You for Your Feedback',
                'Thank you for your feedback. How can we assist you?',
                'jay@technlogic.service',  # Replace with your email
                [email],
            )
            messages.success(request, 'Sent successful!')
            return render(request, 'blogapp/index.html', {'events': events,'form': form, 'success': True})
    else:
        form = ContactForm()

    return render(request, 'blogapp/index.html', {'form': form, 'events': events})

def event_detail(request):
    if request.user.is_authenticated:
        user_bookings = Booking.objects.filter(user=request.user)
        tickets = Ticket.objects.filter(booking__in=user_bookings).order_by('booking__category')
        tickets_by_category = {}
        for ticket in tickets:
            category = ticket.booking.category
            if category not in tickets_by_category:
                tickets_by_category[category] = []
            tickets_by_category[category].append(ticket)
        total_tickets = tickets.count()
    else:
        user_bookings = []
        tickets_by_category = {}
        total_tickets = 0
    context = {
        'user_bookings': user_bookings,
        'tickets_by_category': tickets_by_category,
        'total_tickets': total_tickets,
    }
    return render(request, 'blogapp/detail.html', context)



def privacy(request):
    if request.method == 'POST':
        # Process the form submission here
        # ...
        return render(request, 'blogapp/maintain.html')
    else:
        return render(request, 'blogapp/privacy.html')


def maintain(request):
    if request.method == 'POST':
        # Process the form submission here
        # ...
        return render(request, 'blogapp/maintain.html')
    else:
        return render(request, 'blogapp/maintain.html')


# View to handle PDF download
def download_pdf(request):
    # Path to the PDF file
    pdf_file_path = os.path.join(settings.BASE_DIR, 'media', 'file.pdf')

    # Check if the file exists
    if not os.path.exists(pdf_file_path):
        return HttpResponseNotFound('The requested file does not exist.')

    try:
        # Open the PDF file for reading in binary mode
        with open(pdf_file_path, 'rb') as pdf_file:
            # Read the file content into a variable
            pdf_content = pdf_file.read()

        # Return the PDF file as a FileResponse
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="EASY_JAY_CONTRACT.pdf"'
        return response
    except Exception as e:
        # Handle any exceptions
        return HttpResponse(f"An error occurred: {str(e)}", status=500)




import os
import zipfile
from decimal import Decimal
from io import BytesIO
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.core.mail import send_mail
from django.template.loader import get_template
from xhtml2pdf import pisa
from .forms import BookingForm
from .models import Booking, Category, Event, Ticket
from allauth.account.views import SignupView
from .forms import CustomSignupForm
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib import messages
from .forms import TicketCodeForm
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Ticket

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
    return render(request, 'blogapp/deactivate_ticket.html', {'form': form})

@staff_member_required
def qr_code_scanner(request):
    return render(request, 'scanner.html')

@csrf_exempt  # Use csrf_exempt for testing; consider proper CSRF handling for production
def validate_ticket(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            code = data['code']
            try:
                ticket = Ticket.objects.get(unique_code=code)
                if not ticket.active_ticket:
                    return JsonResponse({'valid': False, 'used': True, 'used_date': ticket.used_date})
                else:
                    ticket.deactivate()
                    return JsonResponse({'valid': True})
            except Ticket.DoesNotExist:
                return JsonResponse({'valid': False, 'used': False})
        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)

class CustomSignupView(SignupView):
    form_class = CustomSignupForm

    def form_valid(self, form):
        response = super().form_valid(form)
        self.send_confirmation_email(form.instance)
        return response

    def send_confirmation_email(self, user):
        from allauth.account.utils import send_email_confirmation
        send_email_confirmation(self.request, user)

def is_payment_required(total_cost):
    return total_cost > 0  # Adjust this condition based on your payment logic
@transaction.atomic
def book_event(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    categories = Category.objects.all()
    total_tickets = Ticket.objects.filter(booking__event=event).count()
    if request.method == 'POST':
        if request.user.is_authenticated:
            all_valid = True
            bookings_to_save = []
            total_cost = Decimal(0)
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

            if all_valid:
                if is_payment_required(total_cost):
                    for booking in bookings_to_save:
                        booking.save()
                    messages.success(request, 'Booking successful!')
                    #messages.error(request, 'Booking Error!')
                    return redirect('index')

                    request.session['bookings_to_save'] = [booking.id for booking in bookings_to_save]
                    request.session['total_cost'] = float(total_cost)
                    request.session['event_slug'] = event_slug
                    return render(request, 'blogapp/payment.html', {
                        'total_cost': float(total_cost),  # Convert to float for template rendering
                        'customer_email': request.user.email,
                        'customer_name': request.user.get_full_name,
                        'tx_ref': f"txref-{event.id}-{request.user.id}",
                    })
                else:
                    for booking in bookings_to_save:
                        booking.save()
                    messages.success(request, 'Booking successful!')
                    #messages.error(request, 'Booking Error!')
                    return redirect('index')
            else:
                messages.error(request, 'Form data is not valid.')
        else:

            return redirect('account_login')
    return render(request, 'blogapp/discover.html', {'event': event, 'categories': categories, 'total_tickets': total_tickets})


def payment_status(request):
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')
    if status == 'successful':
        payment_verified = verify_payment(transaction_id)
        if payment_verified:
            save_bookings(request, tx_ref)
            messages.success(request, 'Booking and payment successful!')
            return redirect('maintain')
        else:
            messages.error(request, 'Payment verification failed. Please try again.')
            return redirect('book_event', event_slug=request.session.get('event_slug'))
    elif status == 'cancelled':
        messages.info(request, 'Payment was cancelled.')
        return redirect('book_event', event_slug=request.session.get('event_slug'))
    else:
        messages.error(request, 'Payment failed. Please try again.')
        return redirect('book_event', event_slug=request.session.get('event_slug'))


def verify_payment(transaction_id):
    return True

def save_bookings(request, tx_ref):
    bookings_to_save_ids = request.session.get('bookings_to_save', [])
    bookings_to_save = Booking.objects.filter(id__in=bookings_to_save_ids)

    for booking in bookings_to_save:
        booking.save()

    request.session.pop('bookings_to_save', None)
    request.session.pop('total_cost', None)
    request.session.pop('event_slug', None)

    messages.success(request, 'Ticket(s) Booked Successfully 🤝🏻')
    return redirect('event_detail')

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
        total_tickets = Booking.objects.filter(event=event).aggregate(Sum('number_of_tickets'))[
            'number_of_tickets__sum']
        event.total_tickets_sold = total_tickets if total_tickets is not None else 0
    return render(request, 'blogapp/index.html', {'events': events})

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

def contact(request):
    if request.method == 'POST':
        # Process the form submission here
        # ...
        return render(request, 'blogapp/maintain.html')
    else:
        return render(request, 'blogapp/contact.html')


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


def mailing_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Send email
        subject = 'New Contact Form Submission'
        email_message = f'Name: {name}\nEmail: {email}\nMessage: {message}'
        sender = 'michaelglory723@gmail.com'  # Replace with your email address
        recipients = ['oscomputers.gwandara@gmail.com']  # Replace with recipient email addresses

        send_mail(subject, email_message, sender, recipients)

        messages.success(request, 'Form submitted successfully!')
        return redirect('login')

    # Render the contact form
    return render(request, 'contact.html')


# View to generate PDF
@login_required(login_url='login')
def generate_pdf(request):
    # Get the template HTML file
    template = get_template('downloads.html')
    context = {
        # Add your context variables here
        'request': request,
    }
    html = template.render(context)

    # Create a PDF object
    pdf = None
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Edna_policy.pdf"'

    # Generate the PDF
    try:
        pisa.CreatePDF(html, dest=response)
        pdf = response
    except Exception as e:
        # Handle exception if PDF generation fails
        return HttpResponse('PDF Generation Error: {}'.format(str(e)))

    return pdf


# Static view for booking success
def booking_success(request):
    return render(request, 'blogapp/welcome.html')

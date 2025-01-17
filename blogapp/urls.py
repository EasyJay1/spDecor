from .views import download_pdf
from django.urls import path
from . import views
from django.urls import path, include
# blogapp/urls.py
from django.urls import path
from .views import CustomSignupView
from .views import deactivate_ticket


urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', CustomSignupView.as_view(), name='account_signup'),
    path('/deactivate-ticket/', deactivate_ticket, name='deactivate_ticket'),
    path('scanner/', views.qr_code_scanner, name='qr_code_scanner'),
    path('continue_booking', views.continue_booking, name='continue_booking'),
    path('payment_status', views.payment_status, name='payment_status'),
    path('webhook/flutterwave/', views.flutterwave_webhook, name='flutterwave_webhook'),

    path('maintain', views.maintain, name='maintain'),

    path('privacy', views.privacy, name='privacy'),
    path('download-pdf/', download_pdf, name='download_pdf'),

    path('book-event/<slug:event_slug>/', views.book_event, name='book_event'),
    path('download-tickets/', views.download_tickets, name='download_tickets'),

    path('event/', views.event_detail, name='event_detail'),  # Assuming you have an event detail view

]

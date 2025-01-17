import random
import string
from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode
from PIL import Image, ImageDraw, ImageFont
from django.contrib.auth.models import AbstractUser, UserManager
from django.db.models import Q
from django.db import models
from django.urls import reverse
from django.utils import timezone
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image, ImageDraw, ImageFont
import qrcode


class UserManager(UserManager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (Q(username__icontains=query) |
                         Q(first_name__icontains=query)|
                         Q(last_name__icontains=query)|
                         Q(email__icontains=query)
                        )
            qs = qs.filter(or_lookup).distinct() # distinct() is often necessary with Q lookups
        return qs

class CustomUser(AbstractUser):
    is_agent = models.BooleanField(default=False)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    objects = UserManager()

    @property
    def get_full_name(self):
        full_name = self.username
        if self.first_name and self.last_name:
            full_name = self.first_name + " " + self.last_name
        return full_name

    def __str__(self):
        return '{} ({})'.format(self.username, self.get_full_name)

    @property
    def get_user_role(self):
        if self.is_superuser:
            return "Admin"
        elif self.is_agent:
            return "agent"


class CookiesConsent(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    consent_given = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

class Category(models.Model):
    grade = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.grade

class Event(models.Model):
    active_event = models.BooleanField(default=True)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    image = models.FileField(upload_to="img", blank=True, null=True)
    description = models.TextField()
    location = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    comments = models.ManyToManyField(settings.AUTH_USER_MODEL, through='Comment', related_name='event_comments')
    unique_views = models.PositiveIntegerField(default=0)  # Field for unique views
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_events', blank=True)
    bookings = models.ManyToManyField(settings.AUTH_USER_MODEL, through='Booking', related_name='booked_events', blank=True)

    def get_absolute_url(self):
        return reverse("detail", kwargs={"slug": self.slug})

    def __str__(self):
        return f'Ticket {self.name} {self.active_event}'

    def save(self, *args, **kwargs):
        # Check if end_date is in the past and update active_event
        if self.end_date <= timezone.now():
            self.active_event = False
        # Ensure that start_date is not greater than end_date
        if self.start_date > self.end_date:
            raise ValueError("The start date cannot be later than the end date.")
        super().save(*args, **kwargs)


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f'Comment by {self.user.username} on {self.event.name}'



class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True,  blank=True)
    number_of_tickets = models.IntegerField(default=0, blank=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.pk:  # Only check capacity on creation
            if self.number_of_tickets > self.event.capacity:
                raise ValueError("Not enough capacity for the event")

            # Reduce event capacity
            self.event.capacity -= self.number_of_tickets
            self.event.save()

        super().save(*args, **kwargs)  # Save the Booking instance first

        if not self.tickets.exists():  # Check if tickets already exist for this booking
            # Create tickets for the booking
            for _ in range(self.number_of_tickets):
                ticket = Ticket.objects.create(booking=self)
    def __str__(self):
        return f'Ticket {self.number_of_tickets}'

    @classmethod
    def total_tickets_bought(cls):
        total_tickets = cls.objects.aggregate(models.Sum('number_of_tickets'))['number_of_tickets__sum']
        return total_tickets if total_tickets is not None else 0


# blogapp/models.py

from django.utils import timezone
import uuid
import random
import string
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.db import models
from django.utils import timezone
from django.core.files.base import ContentFile


def generate_unique_code():
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        if not Ticket.objects.filter(unique_code=code).exists():
            return code


class Ticket(models.Model):
    active_ticket = models.BooleanField(default=True)
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='tickets')
    unique_code = models.CharField(max_length=10, unique=True, default=generate_unique_code)
    used_date = models.DateTimeField(null=True, blank=True)
    qr_code = models.ImageField(upload_to='qr_codes', blank=True)

    def __str__(self):
        return f'Ticket {self.unique_code} for {self.booking.event.name} with {self.booking.category} now ' \
               f'{self.active_ticket} at {self.used_date}.'

    def save(self, *args, **kwargs):
        if not self.qr_code:
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.unique_code)
            qr.make(fit=True)

            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

            # Load a font
            try:
                font = ImageFont.truetype("arial.ttf", 18)
            except IOError:
                font = ImageFont.load_default()

            # Prepare text
            text = f'{self.booking.category}\n{self.unique_code}\n{self.booking.event.name}\n{self.booking.event.start_date}'
            draw = ImageDraw.Draw(qr_img)
            bbox = draw.textbbox((0, 0), text, font=font)
            textwidth = bbox[2] - bbox[0]
            textheight = bbox[3] - bbox[1]

            # Create a new image with extra space for text
            new_height = qr_img.height + textheight + 10  # 10 pixels for padding
            new_img = Image.new("RGB", (qr_img.width, new_height), "white")

            # Paste the QR code image onto the new image
            new_img.paste(qr_img, (0, 0))

            # Draw the text below the QR code
            draw = ImageDraw.Draw(new_img)
            text_x = (new_img.width - textwidth) / 2
            text_y = qr_img.height + 5  # 5 pixels from the bottom of QR code
            draw.text((text_x, text_y), text, font=font, fill="black")

            # Save the image to a BytesIO object
            buffer = BytesIO()
            new_img.save(buffer, format="PNG")
            buffer.seek(0)

            # Save the image to the qr_code field
            filename = f'{self.booking.event.name}_{self.booking.event.start_date}.png'
            self.qr_code.save(filename, ContentFile(buffer.read()), save=False)

        super().save(*args, **kwargs)

    def deactivate(self):
        self.active_ticket = False
        self.used_date = timezone.now()
        self.save()

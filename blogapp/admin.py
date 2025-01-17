from .models import Category, Event, Comment, Ticket, Booking
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'phone_number', 'is_staff', 'is_superuser'),
        }),
    )
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

# Register the CustomUser model with the admin site
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Event)
admin.site.register(Category)
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('active_ticket', 'booking', 'unique_code', 'used_date')  # Fields to display in the list view
    search_fields = ('unique_code', )  # Fields to search by using the search box
admin.site.register(Comment)
admin.site.register(Booking)


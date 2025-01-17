from django.db import transaction
from .models import Event

class EventViewTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if 'viewed_events' not in request.session:
            request.session['viewed_events'] = []

        event_slug = view_kwargs.get('event_slug')  # Ensure to use correct keyword
        if event_slug and view_func.__name__ == 'book_event' and request.method == 'GET':
            # Avoid multiple increments by double-checking session storage
            viewed_events = request.session.get('viewed_events', [])
            if event_slug not in viewed_events:
                event = Event.objects.filter(slug=event_slug).first()
                if event:
                    with transaction.atomic():
                        event.unique_views += 1
                        event.save()
                    viewed_events.append(event_slug)
                    request.session['viewed_events'] = viewed_events
                    request.session.modified = True

        return None

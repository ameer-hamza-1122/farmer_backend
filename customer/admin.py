from django.contrib import admin
from .models import Customer, OneTimePassword, ChatTicket, ChatTicketReply

# Register your models here.

admin.site.register(Customer)
admin.site.register(OneTimePassword)
admin.site.register(ChatTicket)
admin.site.register(ChatTicketReply)


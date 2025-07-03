from django.contrib import admin
from .models import Customer, OneTimePassword, ChatTicket, ChatTicketReply, News, YieldCalculation, Shop, LeafDisease

# Register your models here.

admin.site.register(Customer)
admin.site.register(OneTimePassword)
admin.site.register(ChatTicket)
admin.site.register(ChatTicketReply)
admin.site.register(News)
admin.site.register(Shop)
admin.site.register(YieldCalculation)
admin.site.register(LeafDisease)


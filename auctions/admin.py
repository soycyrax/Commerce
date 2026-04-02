from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Listing, Bid, Comment, Watchlist

admin.site.register(Listing)
admin.site.register(Bid)
admin.site.register(Comment)
admin.site.register(Watchlist)
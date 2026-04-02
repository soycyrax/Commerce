from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("create", views.create_listing, name="create"),
    path("listing/<int:id>/", views.listing_page, name="listing_page"),
    path("watchlist/<int:listing_id>/", views.toggle_watchlist, name="toggle_watchlist"),
    path("bid/<int:listing_id>/", views.place_bid, name="place_bid"),
    path("close/<int:listing_id>/", views.close_auction, name="close_auction"),
    path("comment/<int:listing_id>/", views.add_comment, name="add_comment"),
    path("watchlist/", views.watchlist_page, name="watchlist"),
    path("categories/", views.categories, name="categories"),
path("categories/<str:category_name>/", views.category_listings, name="category_listings")
]

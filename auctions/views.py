from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from .models import User, Listing, Bid



def index(request):
    listings = Listing.objects.filter(is_active=True)

    return render(request, "auctions/index.html", {
        "listings": listings
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")
    

@login_required
def create_listing(request):
    if request.method == "POST":
        title = request.POST["title"]
        description = request.POST["description"]
        starting_bid = request.POST["starting_bid"]
        image_url = request.POST.get("image_url", "")
        category = request.POST.get("category", "")

        listing = Listing.objects.create(
            title=title,
            description=description,
            starting_bid=starting_bid,
            image_url=image_url,
            category=category,
            created_by=request.user
        )

        return redirect("listing_page", listing.id)
    
    return render(request, "auctions/create.html")


def listing_page(request, id):
    listing = get_object_or_404(Listing, id=id)
    bids = listing.bids.all().order_by("-amount")
    highest_bid = bids.first()

    if request.method == "POST":
        bid_amount = float(request.POST["bid_amount"])

        current_price = highest_bid.amount if highest_bid else listing.starting_bid

        if bid_amount > current_price:
            Bid.objects.create(
                listing=listing,
                bidder=request.user,
                amount=bid_amount
            )
            return redirect("listing_page", id=id)
        else:
            return render(request, "auctions/listing.html", {
                "listing": listing,
                "bids": bids,
                "highest_bid": highest_bid,
                "error": "Bid must be higher than current price"
            })

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "bids": bids,
        "highest_bid": highest_bid
    })
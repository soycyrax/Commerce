from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from .models import User, Listing, Bid, Watchlist, Comment

def index(request):
    listings = Listing.objects.filter(is_active=True)

    watchlist_ids = []
    if request.user.is_authenticated:
        watchlist_ids = Watchlist.objects.filter(
            user=request.user
        ).values_list("listing_id", flat=True)

    return render(request, "auctions/index.html", {
        "listings": listings,
        "watchlist_ids": watchlist_ids
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
    # Handle form submission
    if request.method == "POST":

        # Get form data safely
        title = request.POST.get("title")
        description = request.POST.get("description")
        starting_bid = request.POST.get("starting_bid")
        image_url = request.POST.get("image_url", "")
        category = request.POST.get("category", "")

        # Validate required fields
        if not title or not description or not starting_bid:
            return render(request, "auctions/create.html", {
                "error": "All required fields must be filled"
            })

        # Convert starting_bid to float
        try:
            starting_bid = float(starting_bid)
        except ValueError:
            return render(request, "auctions/create.html", {
                "error": "Starting bid must be a number"
            })

        # Create new listing
        listing = Listing.objects.create(
            title=title,
            description=description,
            starting_bid=starting_bid,
            image_url=image_url,
            category=category,
            created_by=request.user
        )

        # Redirect to the listing page
        return redirect("listing_page", id=listing.id)

    # If GET request, show empty form
    return render(request, "auctions/create.html")


def listing_page(request, id):
    # Retrieve the listing or return 404 if not found
    listing = get_object_or_404(Listing, id=id)
    comments = listing.comments.all()

    is_watched = False
    if request.user.is_authenticated:
        is_watched = Watchlist.objects.filter(
        user=request.user,
        listing=listing
        ).exists()

    # Get all bids ordered by highest amount first
    bids = listing.bids.all().order_by("-amount")

    # Get the highest bid (if any)
    highest_bid = bids.first()

    # Handle bid submission
    if request.method == "POST":

        # Ensure user is authenticated before bidding
        if not request.user.is_authenticated:
            return redirect("login")

        # Get bid amount safely
        bid_amount = request.POST.get("bid_amount")

        # Validate input
        if not bid_amount:
            return render(request, "auctions/listing.html", {
                "listing": listing,
                "bids": bids,
                "highest_bid": highest_bid,
                "error": "Please enter a bid amount",
                "comments": comments,
                "is_watched": is_watched
            })

        bid_amount = float(bid_amount)

        # Determine current price
        current_price = highest_bid.amount if highest_bid else listing.starting_bid

        # Check if bid is valid
        if bid_amount > current_price:

            # Create new bid
            Bid.objects.create(
                listing=listing,
                bidder=request.user,
                amount=bid_amount
            )

            # Redirect to refresh page (avoids duplicate submissions)
            return redirect("listing_page", id=id)

        else:
            # Invalid bid → show error
            return render(request, "auctions/listing.html", {
                "listing": listing,
                "bids": bids,
                "highest_bid": highest_bid,
                "error": "Bid must be higher than current price",
                "comments": comments,
                "is_watched": is_watched
            })

    # Default GET request → just display listing
    return render(request, "auctions/listing.html", {
        "listing": listing,
        "bids": bids,
        "highest_bid": highest_bid,
        "comments": comments,
        "is_watched": is_watched
    })


@login_required
def toggle_watchlist(request, listing_id):
    # Ensure the request is POST to prevent unintended actions via URL
    if request.method != "POST":
        return redirect("listing_page", id=listing_id)

    # Retrieve the listing safely (returns 404 if not found)
    listing = get_object_or_404(Listing, id=listing_id)

    # Try to get an existing watchlist entry or create a new one
    watch, created = Watchlist.objects.get_or_create(
        user=request.user,
        listing=listing
    )

    # If the entry already existed, remove it (toggle off)
    if not created:
        watch.delete()

    # Redirect back to the listing page
    return redirect("listing_page", id=listing_id)


@login_required
def place_bid(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)

    # Only allow POST
    if request.method != "POST":
        return redirect("listing_page", id=listing_id)

    bid_amount = float(request.POST["bid_amount"])

    # Get highest bid
    highest_bid = listing.bids.order_by('-amount').first()

    current_price = highest_bid.amount if highest_bid else listing.starting_bid

    # Invalid bid
    if bid_amount <= current_price:
        return render(request, "auctions/listing.html", {
            "listing": listing,
            "highest_bid": highest_bid,
            "error": "Bid must be higher than current price!"
        })

    # Valid bid
    Bid.objects.create(
        bidder=request.user,
        listing=listing,
        amount=bid_amount
    )

    listing.current_price = bid_amount
    listing.save()

    return redirect("listing_page", id=listing_id)


@login_required  # 🔒 Only logged-in users can access this view
def close_auction(request, listing_id):

    # Get the listing object using the given ID
    listing = Listing.objects.get(id=listing_id)

    # Check: Only the owner of the listing can close the auction
    if request.user != listing.created_by:
        # If not owner → redirect back to listing page
        return redirect("listing_page", id=listing_id)

    # Get the highest bid (largest amount first)
    highest_bid = listing.bids.order_by('-amount').first()

    # If at least one bid exists, assign winner
    if highest_bid:
        listing.winner = highest_bid.bidder

    # Mark the listing as inactive (auction closed)
    listing.is_active = False

    # Save changes to database
    listing.save()

    # Redirect back to the listing page
    return redirect("listing_page", id=listing_id)


@login_required  # Only logged-in users can add comments
def add_comment(request, listing_id):

    # Allow only POST requests (prevents misuse via URL)
    if request.method != "POST":
        return redirect("listing_page", id=listing_id)

    # Safely get the listing (returns 404 if not found)
    listing = get_object_or_404(Listing, id=listing_id)

    # Get comment text from form input
    comment_text = request.POST.get("comment")

    # Prevent empty comments
    if not comment_text or comment_text.strip() == "":
        return redirect("listing_page", id=listing_id)

    # Create and save the comment
    Comment.objects.create(
        user=request.user,      # Who commented
        listing=listing,        # Which listing
        content=comment_text    # Comment text
    )

    # Redirect back to listing page
    return redirect("listing_page", id=listing_id)


@login_required
def watchlist_page(request):
    listings = Listing.objects.filter(
        watchlist__user=request.user
    )
    return render(request, "auctions/watchlist.html", {
        "listings": listings
    })


def categories(request):
    # Get unique categories (case-insensitive optional)
    categories = Listing.objects.values_list("category", flat=True).distinct()

    return render(request, "auctions/categories.html", {
        "categories": categories
    })


def category_listings(request, category_name):
    listings = Listing.objects.filter(
        category=category_name,
        is_active=True
    )

    return render(request, "auctions/category_listings.html", {
        "listings": listings,
        "category": category_name
    })
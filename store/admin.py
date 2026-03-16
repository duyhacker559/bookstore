from django.contrib import admin
from store.models import (
    Book, Customer, Staff, Order, OrderItem, Payment, Shipment, Cart, Recommendation,
    Author, Category, BookDetail, BookImage, Inventory, UserProfile, Rating, Comment,
    UserNotification, InboxMessage, InboxReply
)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 1

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ('customer', 'title', 'content', 'is_verified_purchase', 'helpful_count')

class BookAdmin(admin.ModelAdmin):
    inlines = [BookImageInline, CommentInline]
    list_display = ('id', 'title', 'author', 'price', 'stock', 'rating', 'review_count', 'created_at')
    search_fields = ('title', 'author', 'categories_m2m__name')
    list_filter = ('categories_m2m', 'rating', 'created_at')
    filter_horizontal = ('categories_m2m',)

class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ('id', 'customer', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')

class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

class InventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'quantity')
    list_filter = ('quantity',)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'phone')
    search_fields = ('full_name', 'user__username')

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'method_name', 'amount', 'status')
    list_filter = ('status', 'method_name')

class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'method_name', 'fee')
    list_filter = ('status', 'method_name')

class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'book', 'score', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('customer__name', 'book__title')
    readonly_fields = ('created_at', 'updated_at')

class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'book', 'title', 'is_verified_purchase', 'helpful_count', 'created_at')
    list_filter = ('is_verified_purchase', 'created_at', 'helpful_count')
    search_fields = ('customer__name', 'book__title', 'title', 'content')
    readonly_fields = ('created_at', 'updated_at')


class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('customer__name', 'title', 'message')


class InboxMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'book', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer__name', 'subject', 'content', 'staff_note')


class InboxReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'inbox_message', 'sender_type', 'created_at')
    list_filter = ('sender_type', 'created_at')
    search_fields = ('inbox_message__subject', 'content')

admin.site.register(Book, BookAdmin)
admin.site.register(Customer)
admin.site.register(Staff)
admin.site.register(Order, OrderAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Shipment, ShipmentAdmin)
admin.site.register(Cart)
admin.site.register(Recommendation)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(BookDetail)
admin.site.register(BookImage)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Rating, RatingAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
admin.site.register(InboxMessage, InboxMessageAdmin)
admin.site.register(InboxReply, InboxReplyAdmin)

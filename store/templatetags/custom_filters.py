from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def add_stars(value):
    """Convert rating number to stars"""
    try:
        stars = int(float(value))
        return '⭐' * stars + '☆' * (5 - stars)
    except (ValueError, TypeError):
        return '☆☆☆☆☆'

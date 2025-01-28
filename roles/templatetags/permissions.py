from django import template

register = template.Library()

@register.filter
def has_perm(user, perm_name):
    has_permission = user.has_perm(perm_name)
    return has_permission

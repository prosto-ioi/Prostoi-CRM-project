from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User 

class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email', )

    fieldsets = (
        (None, {'fields': ('email', 'password')}), 
        ('Personal info', {'fields': ('first_name', 'last_name', 'avatar')}), 
        ('Premissions', {'fields': ('is_staf', 'is_active', 'is_superuser', 'groups', 'user_premissions')}),
        ('important dates', {'fields': ('last_login', 'date_joined')})
    )

    add_fieldsets = (
        (None, {'classes': ('wide', ),
                'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', ),
                }),
    )

admin.site.register(User, UserAdmin)

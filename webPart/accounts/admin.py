from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AdminProfile, OrdinaryUserProfile


class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    can_delete = False


class OrdinaryUserProfileInline(admin.StackedInline):
    model = OrdinaryUserProfile
    can_delete = False


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_staff', 'date_joined')
    list_filter = ('user_type', 'is_staff', 'is_active')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Тип пользователя', {'fields': ('user_type',)}),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []

        inlines = []
        if obj.user_type == 'admin':
            inlines.append(AdminProfileInline(self.model, self.admin_site))
        else:
            inlines.append(OrdinaryUserProfileInline(self.model, self.admin_site))

        return inlines


admin.site.register(User, UserAdmin)
admin.site.register(AdminProfile)
admin.site.register(OrdinaryUserProfile)
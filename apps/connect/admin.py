from django.contrib import admin
from .models import ConnectStaff, MynumberRequest, ProfileRequest, ConnectInternationalRequest, ConnectClient

admin.site.register(ConnectStaff)
admin.site.register(MynumberRequest)
admin.site.register(ProfileRequest)
admin.site.register(ConnectInternationalRequest)
admin.site.register(ConnectClient)
